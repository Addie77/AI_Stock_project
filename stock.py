import requests
import pandas as pd
import datetime
import urllib3
import os

# 停用 SSL 安全警告 (避免噴紅字)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_stock_historical_data(code):
    """
    抓取特定個股過去 3 個月的歷史日收盤資訊
    支援上市（證交所）與上櫃（櫃買中心）股票
    """
    code = str(code).strip().zfill(4)
    print(f"📡 正在動態抓取股票代碼 {code} 過去 3 個月的歷史行情...")
    
    today = datetime.date.today()
    prices_list = []
    dates_list = []
    stock_name = "未知股票"
    market_type = "未知"

    # 1. 計算要抓取的月份 (今天往回推 3 個月，例如：20260301, 20260401, 20260501)
    months_to_fetch = []
    for i in range(2, -1, -1):
        d = today - datetime.timedelta(days=i * 30)
        months_to_fetch.append(d.strftime("%Y%m01"))

    # --- 嘗試 A：去證交所（上市）抓取資料 ---
    is_listed = False
    try:
        for date_str in months_to_fetch:
            twse_url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date_str}&stockNo={code}"
            # verify=False 解決 SSL 憑證驗證失敗問題
            res = requests.get(twse_url, verify=False, timeout=10)
            data = res.json()
            
            if data.get('stat') == 'OK' and 'data' in data:
                is_listed = True
                market_type = "上市"
                # 從標題擷取股票名稱
                title_parts = data.get('title', '').split(' ')
                if len(title_parts) >= 3:
                    stock_name = title_parts[2]
                
                for row in data['data']:
                    # row[0]: 日期 (例 115/05/02), row[6]: 收盤價
                    dates_list.append(row[0].strip())
                    prices_list.append(row[6].strip())
    except Exception as e:
        print(f"ℹ️ 嘗試上市 API 時發生異常 (可能非上市股票): {e}")

    # --- 嘗試 B：如果上市抓不到，改去櫃買中心（上櫃）抓取資料 ---
    if not is_listed:
        try:
            for date_str in months_to_fetch:
                # 轉換西元年為民國年格式 (櫃買中心 API 格式需求，如 2026/05 -> 115/05)
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
                        # row[0]: 日期, row[6]: 收盤價
                        dates_list.append(row[0].strip())
                        prices_list.append(row[6].strip())
        except Exception as e:
            print(f"❌ 上櫃資料抓取失敗: {e}")

    # --- 2. 資料清洗與 DataFrame 建立 ---
    if not prices_list:
        print(f"❌ 找不到股票代碼 {code} 的任何歷史資料，請確認代碼是否正確。")
        return pd.DataFrame()

    df = pd.DataFrame({
        '日期': dates_list,
        '收盤價': prices_list
    })
    
    # 清除價格中的逗號並轉換為純數字型態
    df['收盤價'] = pd.to_numeric(df['收盤價'].astype(str).str.replace(',', '').replace('--', '0'), errors='coerce')
    df = df.dropna(subset=['收盤價'])
    
    # 補上股票基本資訊欄位，維持與後端相容性
    df['股票代碼'] = code
    df['名稱'] = stock_name
    df['市場'] = market_type

    return df

if __name__ == "__main__":
    # 測試抓取：以 2330 (上市) 或 0050 為例
    test_code = "2330"
    df_result = get_stock_historical_data(test_code)
    
    if not df_result.empty:
        # 存成 all_stocks.csv，讓 gemini.py 可以無縫讀取
        output_path = "all_stocks.csv"
        df_result.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"\n✨ 成功更新【{df_result.iloc[0]['名稱']}】過去 3 個月共 {len(df_result)} 個交易日的數據！")
        print(df_result.head(5))  # 印出前 5 天資料檢查