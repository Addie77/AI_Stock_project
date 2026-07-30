import os
import sys
import pandas as pd
import numpy as np
import yfinance as yf
import pickle
import pymysql
import requests
from datetime import datetime, date

# Reconfigure stdout/stderr to handle UTF-8 printing on Windows
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')  # type: ignore
except AttributeError:
    pass

# DB Connection Config
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "addie20041124",
    "database": "stock_analysis",
    "port": 3306,
    "charset": "utf8mb4"
}

MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".models")

def calculate_technical_indicators(df):
    """
    Calculate core technical indicators for feature engineering (same as ml_trainer.py)
    """
    df = df.copy()
    
    # Moving Averages
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA10'] = df['Close'].rolling(window=10).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    
    # MA Deviations
    df['MA_diff_5'] = (df['Close'] - df['MA5']) / df['MA5']
    df['MA_diff_10'] = (df['Close'] - df['MA10']) / df['MA10']
    df['MA_diff_20'] = (df['Close'] - df['MA20']) / df['MA20']
    df['MA_diff_60'] = (df['Close'] - df['MA60']) / df['MA60']
    
    # RSI (14)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    df['RSI14'] = 100 - (100 / (1 + rs))
    
    # Stochastic KD (9, 3, 3)
    low_9 = df['Low'].rolling(window=9).min()
    high_9 = df['High'].rolling(window=9).max()
    rsv = 100 * ((df['Close'] - low_9) / (high_9 - low_9 + 1e-9))
    df['K9'] = rsv.ewm(com=2, adjust=False).mean()
    df['D9'] = df['K9'].ewm(com=2, adjust=False).mean()
    
    # MACD
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_hist'] = df['MACD'] - df['MACD_signal']
    
    # Volume Indicators
    df['Vol_MA5'] = df['Volume'].rolling(window=5).mean()
    df['Volume_ratio'] = df['Volume'] / (df['Vol_MA5'] + 1e-9)
    
    # Price Return Momentum
    df['Return_1d'] = df['Close'].pct_change()
    df['Return_5d'] = df['Close'].pct_change(5)
    
    df = df.dropna()
    return df

def get_sentiment_baseline_and_today(stock_id):
    """
    Read sentiment baseline (mean & std dev) and today's score directly from 股票紀錄.xlsx.
    """
    excel_path = r"c:\Users\88696\OneDrive\桌面\AI_Stock_project\股票紀錄.xlsx"
    if not os.path.exists(excel_path):
        print(f"⚠️ 找不到 Excel 檔案: {excel_path}")
        return None, None, None
        
    sheet_mapping = {
        "2330": "台積電",
        "2317": "鴻海",
        "2454": "聯發科"
    }
    
    sheet_name = sheet_mapping.get(stock_id)
    if not sheet_name:
        return None, None, None
        
    try:
        # Read Excel sheet
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
        
        # Clean columns and rows
        if '情緒分數' not in df.columns or '日期' not in df.columns:
            print(f"⚠️ Sheet {sheet_name} 格式不正確，缺少 '情緒分數' 或 '日期' 欄位")
            return None, None, None
            
        # Ensure sentiment score is numeric
        df['情緒分數'] = pd.to_numeric(df['情緒分數'], errors='coerce')
        df = df.dropna(subset=['情緒分數', '日期'])
        
        if df.empty:
            return None, None, None
            
        # Calculate historical stats (from Excel)
        mean_val = df['情緒分數'].mean()
        std_val = df['情緒分數'].std()
        if pd.isna(mean_val) or pd.isna(std_val):
            return None, None, None
            
        mean_sent = mean_val
        std_sent = std_val
        if std_sent == 0:
            std_sent = 1.0
            
        # 💡 新增：自 MySQL 資料庫中動態讀取「今天剛爬取並分析出來」的情緒分數
        today_score = None
        conn = None
        try:
            conn = pymysql.connect(**DB_CONFIG)
            cursor = conn.cursor()
            # 優先讀取今天產生的 AI 報告中記錄的平均分數
            query = "SELECT avg_sentiment FROM stock_analysis_report WHERE stock_id = %s AND analysis_date = CURDATE()"
            cursor.execute(query, (stock_id,))
            row = cursor.fetchone()
            if row and row[0] is not None and row[0] != 0.0:
                today_score = float(row[0])
                print(f"📊 股票 {stock_id} 從資料庫讀取到今日最新分析情緒值: {today_score:.2f}")
            else:
                # 備援：若無今日報告，直接計算今日已爬取新聞的平均分
                query_news = "SELECT AVG(sentiment_score) FROM news_sentiment WHERE stock_id = %s AND DATE(publish_date) = CURDATE()"
                cursor.execute(query_news, (stock_id,))
                row_news = cursor.fetchone()
                if row_news and row_news[0] is not None:
                    today_score = float(row_news[0])
                    print(f"📊 股票 {stock_id} 從資料庫新聞表計算出今日平均情緒值: {today_score:.2f}")
        except Exception as db_err:
            print(f"⚠️ 讀取資料庫今日情緒失敗: {db_err}")
        finally:
            if conn:
                conn.close()

        if today_score is None:
            print(f"ℹ️ 股票 {stock_id} 資料庫中今日 ({date.today().strftime('%Y-%m-%d')}) 無今日情緒資料，不進行情緒修正。")
            
        return mean_sent, std_sent, today_score
        
    except Exception as e:
        print(f"⚠️ 讀取 Excel 發生異常: {e}")
        return None, None, None

def send_prediction_to_springboot(stock_id, target_date, up_probability, trade_signal, is_sentiment_fused, stock_name=None):
    """
    Send the ML prediction output to Spring Boot backend
    """
    api_url = "http://localhost:8080/api/ingest/prediction"
    
    # up_probability is percentage, e.g. 68.50
    payload = {
        "stockId": stock_id,
        "targetDate": target_date.strftime("%Y-%m-%d"),
        "upProbability": float(up_probability),
        "tradeSignal": trade_signal,
        "isSentimentFused": bool(is_sentiment_fused)
    }
    if stock_name:
        payload["stockName"] = stock_name
    
    print(f"📡 準備向 Spring Boot 發送預測結果: {payload}")
    try:
        res = requests.post(api_url, json=payload, timeout=5)
        if res.status_code == 200:
            print(f"✅ 預測結果寫入成功: {res.text}")
            return True
        else:
            print(f"❌ 預測結果寫入失敗 ({res.status_code}): {res.text}")
            return False
    except Exception as e:
        print(f"⚠️ 無法連線至 Spring Boot (請確保 8080 埠運行中): {e}")
        return False

def predict_stock(stock_id, stock_name=None):
    """
    Load LightGBM model, fetch latest stock prices, compute features, 
    integrate sentiment gating (Option A), and output predictions.
    """
    print(f"\n---------------------------------------------")
    print(f"🔮 開始執行股票 {stock_id} 的明日走勢預測 (方案 A)...")
    print(f"---------------------------------------------")
    
    # 1. Load trained model
    model_path = os.path.join(MODELS_DIR, f"lgb_model_{stock_id}.pkl")
    if not os.path.exists(model_path):
        print(f"⚠️ 找不到股票 {stock_id} 的已訓練模型，開始進行動態即時訓練...")
        try:
            from ml_trainer import train_model_for_stock
            success = train_model_for_stock(stock_id)
            if not success:
                print(f"❌ 股票 {stock_id} 動態訓練失敗。")
                return False
        except Exception as te:
            print(f"❌ 載入訓練模組或執行訓練失敗: {te}")
            return False
        
    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)
        
    model = model_data['model']
    features = model_data['features']
    
    # 2. Download latest daily stock prices (last 100 days)
    ticker_str = f"{stock_id}.TW"
    try:
        df = yf.download(ticker_str, period="100d")
        if df.empty:
            ticker_str = f"{stock_id}.TWO"
            df = yf.download(ticker_str, period="100d")
    except Exception as e:
        print(f"❌ 無法下載個股行情: {e}")
        return False
        
    if df.empty or len(df) < 65:
        print(f"❌ 歷史價格天數不足以計算技術指標 (目前僅 {len(df)} 天)")
        return False
        
    # Flatten MultiIndex columns if needed
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    # 3. Calculate features and get the last row
    df_feat = calculate_technical_indicators(df)
    last_row = df_feat.iloc[-1:]
    X_last = last_row[features]
    
    # 4. Predict pure technical probability
    # predict_proba returns [prob_down, prob_up]
    p_tech = model.predict_proba(X_last)[0][1]
    print(f"📊 技術面預測明日上漲機率 (P_tech): {p_tech*100:.2f}%")
    
    # 5. Integrate Sentiment Gating (Option A Fallback logic)
    p_final = p_tech
    is_sentiment_fused = False
    mean_sent, std_sent, today_score = get_sentiment_baseline_and_today(stock_id)
    
    if mean_sent is not None and std_sent is not None and today_score is not None:
        z_score = (today_score - mean_sent) / std_sent
        print(f"💬 新聞輿情特徵:")
        print(f"   - 歷史平均值: {mean_sent:.2f}, 標準差: {std_sent:.2f}")
        print(f"   - 今日平均值: {today_score:.2f} (Z-Score: {z_score:.2f})")
        
        # Apply gating rules
        delta_p = 0.0
        if z_score > 1.0:
            delta_p = min(0.15, 0.05 * z_score)
            p_final = min(0.95, p_tech + delta_p)
            is_sentiment_fused = True
            print(f"   🔥 觸發【極度樂觀】輿情，上漲機率調整: +{delta_p*100:.2f}%")
        elif z_score < -1.0:
            delta_p = max(-0.20, 0.06 * z_score)
            p_final = max(0.05, p_tech + delta_p)
            is_sentiment_fused = True
            print(f"   ❄️ 觸發【極度悲觀】輿情，上漲機率調整: {delta_p*100:.2f}%")
        else:
            is_sentiment_fused = True
            print(f"   💤 輿情情緒在正常偏離區間內，不調整預測值。")
    else:
        print(f"📊 此個股無新聞輿情基底資料或今日無資料，安全退回 (Fallback) 至 100% 純技術指標分析。")
        
    p_final_pct = p_final * 100.0
    print(f"🎯 最終預測明日上漲機率 (P_final): {p_final_pct:.2f}%")
    
    # 6. Determine trade signal
    if p_final >= 0.75:
        signal = "STRONG_BUY"
        cn_signal = "強烈買進"
    elif p_final >= 0.60:
        signal = "BUY"
        cn_signal = "偏多"
    elif p_final > 0.40:
        signal = "HOLD"
        cn_signal = "中立觀望"
    elif p_final > 0.25:
        signal = "SELL"
        cn_signal = "偏空"
    else:
        signal = "STRONG_SELL"
        cn_signal = "強烈賣出"
        
    print(f"🚦 交易訊號: {cn_signal} ({signal})")
    
    # 7. Post back to Spring Boot
    target_date = date.today()
    send_prediction_to_springboot(stock_id, target_date, p_final_pct, signal, is_sentiment_fused, stock_name=stock_name)
    return True

if __name__ == "__main__":
    # 預測我們的四個標的
    target_stocks = ["2330", "2317", "2454", "2408"]
    for stock in target_stocks:
        predict_stock(stock)
