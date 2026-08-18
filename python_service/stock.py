import requests
import pandas as pd
import datetime
import urllib3
import os

# 停用 SSL 安全警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 💡 輔助函式：判斷是否為一般 4 碼純數字個股 (過濾 ETF、權證與特別股)
def is_pure_stock(code):
    if not code:
        return False
    code_str = str(code).strip()
    return len(code_str) == 4 and code_str.isdigit()

# ============================================================================
# 🔥 熱門股票 API：爬取上市 (TWSE) 與上櫃 (TPEx) 前五名 (成交量 / 股價)
# ============================================================================
def get_trending_stocks():
    """
    動態抓取當日上市與上櫃的成交張數與股價排行 Top 5 (排除 ETF)
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    twse_stocks = []
    tpex_stocks = []

    # -------------------------------------------------------------------------
    # 1. 爬取 上市股票 (TWSE OpenAPI)
    # -------------------------------------------------------------------------
    try:
        twse_url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        res = requests.get(twse_url, headers=headers, verify=False, timeout=10)
        if res.status_code == 200:
            data = res.json()
            for item in data:
                code = str(item.get("Code") or item.get("code") or "").strip()
                name = str(item.get("Name") or item.get("name") or "").strip()

                if is_pure_stock(code):
                    try:
                        # 上市成交量欄位：TradeVolume
                        vol_val = item.get("TradeVolume") or item.get("Volume") or item.get("TradingShares") or "0"
                        vol_raw = str(vol_val).replace(",", "").strip()
                        raw_vol = float(vol_raw) if vol_raw and vol_raw != "--" else 0.0
                        volume = int(raw_vol // 1000) if raw_vol >= 1000 else int(raw_vol)

                        price_val = item.get("ClosingPrice") or item.get("Close") or "0"
                        price_raw = str(price_val).replace(",", "").strip()
                        price = float(price_raw) if price_raw and price_raw != "--" else 0.0

                        twse_stocks.append({
                            "code": code,
                            "name": name,
                            "volume": volume,
                            "price": price
                        })
                    except Exception:
                        continue
    except Exception as e:
        print(f"⚠️ 上市熱門股票抓取失敗: {e}")

    # -------------------------------------------------------------------------
    # 2. 爬取 上櫃股票 (TPEx OpenAPI) - 💡 修正對齊 TradingShares 欄位
    # -------------------------------------------------------------------------
    try:
        tpex_url = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes"
        res = requests.get(tpex_url, headers=headers, verify=False, timeout=10)
        if res.status_code == 200:
            data = res.json()
            for item in data:
                code = str(item.get("SecuritiesCompanyCode") or item.get("Code") or "").strip()
                name = str(item.get("CompanyName") or item.get("Name") or "").strip()

                if is_pure_stock(code):
                    try:
                        # 🎯 核心修正：精確對齊櫃買中心官方欄位 TradingShares (成交股數)
                        vol_val = (
                            item.get("TradingShares") or 
                            item.get("TradeVolume") or 
                            item.get("TradingVolume") or 
                            item.get("Volume") or 
                            "0"
                        )
                        vol_raw = str(vol_val).replace(",", "").strip()
                        raw_vol = float(vol_raw) if vol_raw and vol_raw != "--" else 0.0
                        volume = int(raw_vol // 1000)  # 換算為張數

                        price_val = item.get("Close") or item.get("ClosingPrice") or "0"
                        price_raw = str(price_val).replace(",", "").strip()
                        price = float(price_raw) if price_raw and price_raw != "--" else 0.0

                        tpex_stocks.append({
                            "code": code,
                            "name": name,
                            "volume": volume,
                            "price": price
                        })
                    except Exception:
                        continue
    except Exception as e:
        print(f"⚠️ 上櫃熱門股票抓取失敗: {e}")

    # -------------------------------------------------------------------------
    # 3. 排序並取 Top 5 (成交張數排行依據真實張數降冪排序)
    # -------------------------------------------------------------------------
    twse_valid = [s for s in twse_stocks if s["volume"] > 0]
    twse_top_volume = sorted(twse_valid if twse_valid else twse_stocks, key=lambda x: x["volume"], reverse=True)[:5]
    twse_top_price = sorted(twse_stocks, key=lambda x: x["price"], reverse=True)[:5]

    tpex_valid = [s for s in tpex_stocks if s["volume"] > 0]
    tpex_top_volume = sorted(tpex_valid if tpex_valid else tpex_stocks, key=lambda x: x["volume"], reverse=True)[:5]
    tpex_top_price = sorted(tpex_stocks, key=lambda x: x["price"], reverse=True)[:5]

    return {
        "success": True,
        "twse": {
            "volume": twse_top_volume,
            "price": twse_top_price
        },
        "tpex": {
            "volume": tpex_top_volume,
            "price": tpex_top_price
        }
    }

# ============================================================================
# 原有功能：歷史行情資料爬蟲
# ============================================================================
def get_stock_historical_data(code):
    """
    動態抓取特定個股過去 6 個月的歷史日收盤價與真實成交量
    支援上市（證交所）與上櫃（櫃買中心）股票
    """
    code = str(code).strip().zfill(4)
    print(f"📡 正在動態抓取股票代碼 {code} 過去 6 個月的歷史行情與真實成交量...")
    
    today = datetime.date.today()
    prices_list = []
    openingprice_list = []
    highprice_list = []
    lowprice_list = []
    dates_list = []
    volumes_list = []
    stock_name = "未知股票"
    market_type = "未知"

    months_to_fetch = []
    for i in range(5, -1, -1):
        d = today - datetime.timedelta(days=i * 30)
        months_to_fetch.append(d.strftime("%Y%m01"))

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
                    dates_list.append(row[0].strip())
                    volumes_list.append(row[1].strip())
                    openingprice_list.append(row[3].strip())
                    highprice_list.append(row[4].strip())
                    lowprice_list.append(row[5].strip())
                    prices_list.append(row[6].strip())
    except Exception as e:
        print(f"ℹ️ 嘗試上市 API 時發生異常 (可能非上市股票): {e}")

    if not is_listed:
        try:
            for date_str in months_to_fetch:
                dt = datetime.datetime.strptime(date_str, "%Y%m01")
                tpex_date_str = dt.strftime("%Y/%m/01")
                
                tpex_url = f"https://www.tpex.org.tw/www/zh-tw/afterTrading/tradingStock?response=json&date={tpex_date_str}&code={code}"
                res = requests.get(tpex_url, verify=False, timeout=10)
                data = res.json()
                
                if 'tables' in data and data['tables'] and len(data['tables']) > 0:
                    market_type = "上櫃"
                    stock_name = data.get('name', '未知上櫃')
                    table_data = data['tables'][0].get('data', [])
                    for row in table_data:
                        dates_list.append(row[0].strip())
                        volumes_list.append(row[1].strip())
                        openingprice_list.append(row[3].strip())
                        highprice_list.append(row[4].strip())
                        lowprice_list.append(row[5].strip())
                        prices_list.append(row[6].strip())
        except Exception as e:
            print(f"❌ 上櫃資料抓取失敗: {e}")

    if not prices_list:
        print(f"❌ 找不到股票代碼 {code} 的任何歷史資料")
        return pd.DataFrame()

    df = pd.DataFrame({
        '日期': dates_list,
        '開盤價': openingprice_list,
        '最高價': highprice_list,
        '最低價': lowprice_list,
        '收盤價': prices_list,
        '成交量': volumes_list
    })
    
    df['股票代碼'] = code
    df['名稱'] = stock_name
    df['市場'] = market_type

    return df