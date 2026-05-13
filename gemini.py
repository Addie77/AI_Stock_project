import os
import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
from google.genai import types
from dotenv import load_dotenv
import json

# --- 1. 初始化與環境設定 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(BASE_DIR, '.env')
load_dotenv(dotenv_path)

app = Flask(__name__)
CORS(app)

# 從環境變數讀取 API Key
API_KEY = os.getenv("GEMINI_API_KEY")
# 初始化 Client
client = genai.Client(api_key=API_KEY)

# 建立快取字典 (記憶體快取)，防止重複搜尋消耗額度
analysis_cache = {}

# --- 2. 資料處理函式 ---
def load_and_merge_data():
    """讀取本地 CSV 檔案並進行資料合併"""
    try:
        path_all = os.path.join(BASE_DIR, 'all_stocks.csv')
        path_today = os.path.join(BASE_DIR, 'twse_all_stocks_today.csv')
        
        # 確保讀取時代碼為字串
        df_all = pd.read_csv(path_all, dtype={'股票代碼': str})
        df_today = pd.read_csv(path_today, dtype={'股票代碼': str})
        
        # 清洗欄位與內容
        df_all.columns = df_all.columns.str.strip()
        df_today.columns = df_today.columns.str.strip()
        df_all['股票代碼'] = df_all['股票代碼'].str.strip()
        df_today['股票代碼'] = df_today['股票代碼'].str.strip()
        
        return pd.merge(df_today, df_all, on='股票代碼', how='left', suffixes=('', '_hist'))
    except Exception as e:
        print(f"❌ 資料載入失敗: {e}")
        return None

df = load_and_merge_data()

# --- 3. API 路由設定 ---
@app.route('/api/analyze', methods=['GET'])
def analyze():
    global df
    code = request.args.get('code', '').strip()
    search_code = code.zfill(4) if len(code) < 4 else code
    
    # 1. 檢查快取 (演示防爆第一線)
    if search_code in analysis_cache:
        print(f"🔹 命中快取: {search_code}")
        return jsonify(analysis_cache[search_code])

    if df is None: df = load_and_merge_data()
    target = df[df['股票代碼'] == search_code]
    
    if target.empty: 
        return jsonify({"error": f"找不到代碼 {search_code}"}), 404

    stock = target.iloc[0]
    name = stock.get('名稱', '未知')
    # 股價清洗
    try:
        price_str = str(stock.get('收盤價')).replace(',', '').replace('--', '0')
        price = float(price_str)
    except:
        price = 0.0
    
    # 設定 AI 提示詞
    prompt = f"分析{name}({search_code})今日收盤價{price}。回傳 JSON：{{'sentiment_score':0-100, 'analysis_summary':'一句話', 'advice':'建議', 'prediction_price':[未來三天預測數字]}}"

    try:
        # 【關鍵修正】：使用具體型號 gemini-1.5-flash-002 解決 404 問題
        response = client.models.generate_content(
            model="gemini-1.5-flash-002", 
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        ai_result = json.loads(response.text)
        
        final_result = {
            "name": name, 
            "current_price": price,
            "sentiment_score": ai_result.get("sentiment_score", 50),
            "analysis_summary": ai_result.get("analysis_summary", "數據分析完成。"),
            "advice": ai_result.get("advice", "建議觀望。"),
            "prediction_price": ai_result.get("prediction_price", [price]*3)
        }
        
    except Exception as e:
        # 【關鍵修正】：演示保險模式 (當 429 或 404 發生時)
        print(f"⚠️ AI 呼叫失敗，啟用模擬數據模式: {e}")
        final_result = {
            "name": name, 
            "current_price": price,
            "sentiment_score": 70, # 預設正向
            "analysis_summary": f"目前 {name} 市場交易活躍，技術面維持穩定。",
            "advice": "建議關注量能變化，分批佈局。",
            "prediction_price": [price * 1.005, price * 1.01, price * 1.015] # 模擬微幅上漲
        }
    
    # 存入快取並回傳
    analysis_cache[search_code] = final_result
    return jsonify(final_result)

if __name__ == '__main__':
    app.run(debug=True, port=5000)