import requests
import pandas as pd
import datetime
import urllib3
import os

# 停用 SSL 安全警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_stock_historical_data(code):
    """
    動態抓取特定個股過去 3 個月的歷史日收盤價與真實成交量
    支援上市（證交所）與上櫃（櫃買中心）股票
    """
    code = str(code).strip().zfill(4)
    print(f"📡 正在動態抓取股票代碼 {code} 過去 3 個月的歷史行情與真實成交量...")
    
    today = datetime.date.today()
    prices_list = []
    dates_list = []
    volumes_list = [] # 💡 新增：真實成交量陣列
    stock_name = "未知股票"
    market_type = "未知"

    # 1. 計算要抓取的月份 (今天往回推 3 個月)
    months_to_fetch = []
    for i in range(2, -1, -1):
        d = today - datetime.timedelta(days=i * 30)
        months_to_fetch.append(d.strftime("%Y%m01"))

    # --- 嘗試 A：去證交所（上市）抓取歷史日資料 ---
    is_listed = False
    try:
        for date_str in months_to_fetch:
            twse_url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date_str}&stockNo={code}"
            res = requests.get(twse_url, verify=False, timeout=10)
            data = res.json()
            
            if data.get('stat') == 'OK' and 'data' in data:
                is_listed = True
                market_type = "上市"
                title_parts = data.get('title', '').split(' ')
                if len(title_parts) >= 3:
                    stock_name = title_parts[2]
                
                for row in data['data']:
                    # row[0]: 日期, row[1]: 成交股數 (真實交易量), row[6]: 收盤價
                    dates_list.append(row[0].strip())
                    volumes_list.append(row[1].strip()) # 💡 擷取真實成交量
                    prices_list.append(row[6].strip())
    except Exception as e:
        print(f"ℹ️ 嘗試上市 API 時發生異常 (可能非上市股票): {e}")

    # --- 嘗試 B：改去櫃買中心（上櫃）抓取歷史日資料 ---
    if not is_listed:
        try:
            for date_str in months_to_fetch:
                dt = datetime.datetime.strptime(date_str, "%Y%m01")
                tw_year = dt.year - 1911
                tpex_date_str = f"{tw_year}/{dt.strftime('%m')}"
                
                tpex_url = f"https://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/stk_quote_result.php?l=zh-tw&d={tpex_date_str}&stk_no={code}"
                res = requests.get(tpex_url, verify=False, timeout=10)
                data = res.json()
                
                if 'aaData' in data and data['aaData']:
                    market_type = "上櫃"
                    stock_name = data.get('stkName', '未知上櫃')
                    for row in data['aaData']:
                        # row[0]: 日期, row[1]: 成交股數 (真實交易量), row[6]: 收盤價
                        dates_list.append(row[0].strip())
                        volumes_list.append(row[1].strip()) # 💡 擷取真實成交量
                        prices_list.append(row[6].strip())
        except Exception as e:
            print(f"❌ 上櫃資料抓取失敗: {e}")

    # --- 2. 資料清洗與 DataFrame 建立 ---
    if not prices_list:
        print(f"❌ 找不到股票代碼 {code} 的任何歷史資料")
        return pd.DataFrame()

    # 建立與 gemini.py 100% 欄位對齊的真實 DataFrame
    df = pd.DataFrame({
        '日期': dates_list,
        '收盤價': prices_list,
        '成交量': volumes_list # 💡 欄位精確命名為 '成交量'
    })
    
    # 補上基本欄位
    df['股票代碼'] = code
    df['名稱'] = stock_name
    df['市場'] = market_type

    return df

if __name__ == "__main__":
    # 測試本地抓取是否正常
    test_df = get_stock_historical_data("2330")
    if not test_df.empty:
        print("\n✨ 本地真實數據測試成功！")
        print(test_df.head(5))