import requests
import pandas as pd
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_full_market_data():
    # --- 上市 ---
    twse_res = requests.get("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", verify=False)
    df_twse = pd.DataFrame(twse_res.json())
    df_twse = df_twse.rename(columns={'Code':'股票代碼', 'Name':'名稱', 'TradeVolume':'成交量', 'ClosingPrice':'收盤價', 'Change':'漲跌'})
    df_twse = df_twse[['股票代碼', '名稱', '成交量', '收盤價', '漲跌']]
    df_twse['市場'] = '上市'

    # --- 上櫃 ---
    tpex_res = requests.get("https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes", verify=False)
    df_tpex = pd.DataFrame(tpex_res.json())
    
    # 使用 get 方法安全抓取，避免 KeyError
    tpex_rename_logic = {
        'Date': '日期',
        'SecCode': '股票代碼', 'Code': '股票代碼',
        'CompanyName': '名稱', 'Name': '名稱',
        'Close': '收盤價', 'ClosingPrice': '收盤價',
        'Chg': '漲跌', 'Change': '漲跌',
        'Volume': '成交量', 'TradeVolume': '成交量'
    }
    
    # 只針對存在的欄位改名
    actual_cols = [c for c in df_tpex.columns if c in tpex_rename_logic]
    df_tpex = df_tpex[actual_cols].rename(columns=tpex_rename_logic)
    df_tpex['市場'] = '上櫃'

    # --- 合併 ---
    df_all = pd.concat([df_twse, df_tpex], ignore_index=True)
    
    # 轉數值並算漲幅
    for col in ['收盤價', '漲跌', '成交量']:
        df_all[col] = pd.to_numeric(df_all[col], errors='coerce')
    
    df_all['漲幅(%)'] = (df_all['漲跌'] / (df_all['收盤價'] - df_all['漲跌']) * 100).round(2)
    return df_all.dropna(subset=['收盤價'])

if __name__ == "__main__":
    df = get_full_market_data()
    print(df.sample(10)) # 隨機抽 10 筆看看
    df.to_csv("all_stocks.csv", index=False, encoding="utf-8-sig")