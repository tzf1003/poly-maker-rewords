import json
from poly_utils.google_utils import get_spreadsheet
import pandas as pd
import os
from poly_data.network_utils import retry_on_network_error
from poly_data.logger import get_logger

# 创建工具日志记录器
utils_logger = get_logger('utils', console_output=True)

def pretty_print(txt, dic):
    utils_logger.info(f"{txt}\n{json.dumps(dic, indent=4)}")

@retry_on_network_error(max_retries=3, delay=2)
def get_sheet_df(read_only=None):
    """
    获取表格数据，可选只读模式

    参数：
        read_only (bool): 如果为None，则根据凭证可用性自动检测
    """
    all = 'All Markets'
    sel = 'Selected Markets'

    # 如果未指定，则自动检测只读模式
    if read_only is None:
        creds_file = 'credentials.json' if os.path.exists('credentials.json') else '../credentials.json'
        read_only = not os.path.exists(creds_file)
        if read_only:
            utils_logger.info("未找到凭证，使用只读模式")

    try:
        spreadsheet = get_spreadsheet(read_only=read_only)
    except FileNotFoundError:
        utils_logger.warning("未找到凭证，回退到只读模式")
        spreadsheet = get_spreadsheet(read_only=True)

    wk = spreadsheet.worksheet(sel)
    df = pd.DataFrame(wk.get_all_records())
    df = df[df['question'] != ""].reset_index(drop=True)

    wk2 = spreadsheet.worksheet(all)
    df2 = pd.DataFrame(wk2.get_all_records())
    df2 = df2[df2['question'] != ""].reset_index(drop=True)

    result = df.merge(df2, on='question', how='inner')

    wk_p = spreadsheet.worksheet('Hyperparameters')
    records = wk_p.get_all_records()
    hyperparams, current_type = {}, None

    for r in records:
        # 只有在有非空类型值时才更新current_type
        # 处理来自pandas的字符串和NaN值
        type_value = r['type']
        if type_value and str(type_value).strip() and str(type_value) != 'nan':
            current_type = str(type_value).strip()

        # 跳过没有设置current_type的行
        if current_type:
            # 将数值转换为适当的类型
            value = r['value']
            try:
                # 如果是数字，尝试转换为float
                if isinstance(value, str) and value.replace('.', '').replace('-', '').isdigit():
                    value = float(value)
                elif isinstance(value, (int, float)):
                    value = float(value)
            except (ValueError, TypeError):
                pass  # 如果转换失败，保持为字符串

            hyperparams.setdefault(current_type, {})[r['param']] = value

    return result, hyperparams
