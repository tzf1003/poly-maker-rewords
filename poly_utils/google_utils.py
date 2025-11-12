from google.oauth2.service_account import Credentials
import gspread
import os
import pandas as pd
import requests
import re
from dotenv import load_dotenv

load_dotenv()

def get_spreadsheet(read_only=False):
    """
    获取Google电子表格，可选只读模式。

    参数：
        read_only (bool): 如果为True，在缺少凭证时使用公共CSV导出

    返回：
        Spreadsheet对象或只读模式的ReadOnlySpreadsheet包装器
    """
    spreadsheet_url = os.getenv("SPREADSHEET_URL")
    if not spreadsheet_url:
        raise ValueError("未设置SPREADSHEET_URL环境变量")

    # 检查凭证
    creds_file = 'credentials.json' if os.path.exists('credentials.json') else '../credentials.json'

    if not os.path.exists(creds_file):
        if read_only:
            return ReadOnlySpreadsheet(spreadsheet_url)
        else:
            raise FileNotFoundError(f"在{creds_file}找不到凭证文件。使用read_only=True进行只读访问。")

    # 正常的认证访问
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_file(creds_file, scopes=scope)
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_url(spreadsheet_url)
    return spreadsheet

class ReadOnlySpreadsheet:
    """使用公共CSV导出的Google Sheets只读包装器"""

    def __init__(self, spreadsheet_url):
        self.spreadsheet_url = spreadsheet_url
        self.sheet_id = self._extract_sheet_id(spreadsheet_url)

    def _extract_sheet_id(self, url):
        """从Google Sheets URL提取表格ID"""
        match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
        if not match:
            raise ValueError("无效的Google Sheets URL")
        return match.group(1)

    def worksheet(self, title):
        """返回只读工作表"""
        return ReadOnlyWorksheet(self.sheet_id, title)

class ReadOnlyWorksheet:
    """通过CSV导出获取数据的只读工作表"""

    def __init__(self, sheet_id, title):
        self.sheet_id = sheet_id
        self.title = title

    def get_all_records(self):
        """将工作表的所有记录作为字典列表获取"""
        try:
            # URL编码表格标题以处理空格和特殊字符
            import urllib.parse
            encoded_title = urllib.parse.quote(self.title)

            # 将已知表格名称映射到可能的GID位置
            # 基于表格顺序: Full Markets, All Markets, Volatility Markets, Selected Markets, Hyperparameters
            sheet_gid_mapping = {
                'Full Markets': 0,
                'All Markets': 1,
                'Volatility Markets': 2,
                'Selected Markets': 3,
                'Hyperparameters': 4
            }

            # 尝试多种URL格式访问表格
            urls_to_try = [
                f"https://docs.google.com/spreadsheets/d/{self.sheet_id}/gviz/tq?tqx=out:csv&sheet={encoded_title}",
                f"https://docs.google.com/spreadsheets/d/{self.sheet_id}/gviz/tq?tqx=out:csv&sheet={self.title}",
            ]

            # 如果我们知道此表格的可能位置，添加基于GID的URL
            if self.title in sheet_gid_mapping:
                gid = sheet_gid_mapping[self.title]
                urls_to_try.append(f"https://docs.google.com/spreadsheets/d/{self.sheet_id}/export?format=csv&gid={gid}")

            # 也尝试一些常见的GID位置作为后备
            for gid in [0, 1, 2, 3, 4]:
                urls_to_try.append(f"https://docs.google.com/spreadsheets/d/{self.sheet_id}/export?format=csv&gid={gid}")

            for csv_url in urls_to_try:
                try:
                    print(f"尝试从以下位置获取表格'{self.title}': {csv_url}")
                    response = requests.get(csv_url, timeout=30)
                    response.raise_for_status()

                    # 确保响应使用 UTF-8 编码
                    response.encoding = 'utf-8'

                    # 将CSV数据读入DataFrame，明确指定 UTF-8 编码
                    from io import StringIO
                    df = pd.read_csv(StringIO(response.text), encoding='utf-8')

                    # 检查是否获得了有意义的数据（不是空的或错误响应）
                    if not df.empty and len(df.columns) > 1:
                        # 对于Hyperparameters表格，验证它是否有预期的列
                        if self.title == 'Hyperparameters':
                            expected_cols = ['type', 'param', 'value']
                            if all(col in df.columns for col in expected_cols):
                                print(f"成功获取{len(df)}条超参数记录")
                                return df.to_dict('records')
                            else:
                                print(f"表格不匹配Hyperparameters格式。列: {list(df.columns)}")
                                continue
                        else:
                            print(f"成功从表格'{self.title}'获取{len(df)}条记录")
                            # 转换为字典列表（与gspread相同的格式）
                            return df.to_dict('records')

                except Exception as url_error:
                    print(f"URL {csv_url}失败: {url_error}")
                    continue

            print(f"表格'{self.title}'的所有URL尝试都失败了")
            return []

        except Exception as e:
            print(f"警告: 无法从表格'{self.title}'获取数据: {e}")
            return []

    def get_all_values(self):
        """将工作表的所有值作为列表的列表获取"""
        try:
            csv_url = f"https://docs.google.com/spreadsheets/d/{self.sheet_id}/gviz/tq?tqx=out:csv&sheet={self.title}"
            response = requests.get(csv_url, timeout=30)
            response.raise_for_status()

            # 读取CSV并作为列表的列表返回
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))

            # 包含标题并转换为列表的列表
            headers = [df.columns.tolist()]
            data = df.values.tolist()
            return headers + data

        except Exception as e:
            print(f"警告: 无法从表格'{self.title}'获取数据: {e}")
            return []


