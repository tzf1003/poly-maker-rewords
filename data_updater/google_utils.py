from google.oauth2.service_account import Credentials
import gspread
import os
import pandas as pd
import requests
import re


def get_spreadsheet(read_only=False):
    """
    使用环境变量中的凭证和URL获取主Google电子表格

    参数：
        read_only (bool): 如果为True，在缺少凭证时使用公共CSV导出
    """
    spreadsheet_url = os.getenv("SPREADSHEET_URL")
    if not spreadsheet_url:
        raise ValueError("未设置SPREADSHEET_URL环境变量")

    # 检查凭证
    if not os.path.exists('credentials.json'):
        if read_only:
            return ReadOnlySpreadsheet(spreadsheet_url)
        else:
            raise FileNotFoundError("找不到credentials.json。使用read_only=True进行只读访问。")

    # 正常的认证访问
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_file('credentials.json', scopes=scope)
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
            # 使用公共CSV导出URL
            csv_url = f"https://docs.google.com/spreadsheets/d/{self.sheet_id}/gviz/tq?tqx=out:csv&sheet={self.title}"
            response = requests.get(csv_url, timeout=30)
            response.raise_for_status()

            # 将CSV数据读入DataFrame
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))

            # 转换为字典列表（与gspread相同的格式）
            return df.to_dict('records')

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