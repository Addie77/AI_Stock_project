import os
import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
from google.genai import types
from dotenv import load_dotenv
import json

# --- 1. 初始化與環境設定 ---
# 獲取當前檔案所在的目錄路徑
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 拼接出 .env 檔案的絕對路徑
dotenv_path = os.path.join(BASE_DIR, '.env')
# 載入 .env 檔案中的環境變數 (例如 API Key)
load_dotenv(dotenv_path)

app = Flask(__name__)
# 啟用跨來源資源共用 (CORS)，讓前端 (Port 5500) 能夠存取後端 (Port 5000)
CORS(app)

# 從環境變數中讀取 Gemini API 金鑰
API_KEY = os.getenv("GEMINI_API_KEY")
# 初始化 Google Gemini API 客戶端
client = genai.Client(api_key=API_KEY)

# 建立快取字典：存放已搜尋過的分析結果，減少 API 呼叫次數並節省配額 (防止 429 錯誤)
analysis_cache = {}

# --- 2. 資料處理函式 ---
def load_and_merge_data():
    """讀取本地 CSV 檔案並進行資料合併"""
    try:
        # 定義 CSV 檔案路徑
        path_all = os.path.join(BASE_DIR, 'all_stocks.csv')
        path_today = os.path.join(BASE_DIR, 'twse_all_stocks_today.csv')
        
        # 讀取 CSV，指定「股票代碼」為字串格式，避免開頭的 0 被省略 (如 0050)
        df_all = pd.read_csv(path_all, dtype={'股票代碼': str})
        df_today = pd.read_csv(path_today, dtype={'股票代碼': str})
        
        # 清洗欄位名稱：移除標題前後可能存在的空格
        df_all.columns = df_all.columns.str.strip()
        df_today.columns = df_today.columns.str.strip()
        
        # 清洗資料內容：移除股票代碼前後的空格
        df_all['股票代碼'] = df_all['股票代碼'].str.strip()
        df_today['股票代碼'] = df_today['股票代碼'].str.strip()
        
        # 執行左合併 (Left Join)：以今日資料為主，補上歷史主表的資訊
        return pd.merge(df_today, df_all, on='股票代碼', how='left', suffixes=('', '_hist'))
    except Exception as e:
        print(f"❌ 資料載入或合併失敗: {e}")
        return None

# 伺服器啟動時，先載入一次資料到記憶體中
df = load_and_merge_data()

# --- 3. API 路由設定 ---
@app.route('/api/analyze', methods=['GET'])
def analyze():
    global df
    # 獲取前端傳來的股票代碼參數 (URL Query String)
    code = request.args.get('code', '').strip()
    
    # 格式化代碼：如果輸入 50 則補人成 0050
    search_code = code.zfill(4) if len(code) < 4 else code
    
    # 檢查快取：如果這支股票剛搜尋過，直接回傳舊結果，不消耗 API 額度
    if search_code in analysis_cache:
        print(f"🔹 命中快取資料: {search_code}")
        return jsonify(analysis_cache[search_code])

    # 萬一資料遺失，嘗試重新載入
    if df is None: df = load_and_merge_data()
    
    # 在合併後的表格中搜尋對應的股票代碼
    target = df[df['股票代碼'] == search_code]
    
    # 如果找不到該股票，回傳 404 錯誤
    if target.empty: 
        return jsonify({"error": f"在 CSV 中找不到代碼 {search_code}"}), 404

    # 取得搜尋到的第一筆資料
    stock = target.iloc[0]
    name = stock.get('名稱', '未知')
    # 處理股價字串：移除逗號 (,) 並將代表無交易的 '--' 替換為 '0'，最後轉為浮點數
    price = float(str(stock.get('收盤價')).replace(',', '').replace('--', '0'))
    
    # 設計給 Gemini AI 的指令 (Prompt)
    prompt = f"分析{name}({search_code})今日收盤價{price}。請依此回傳 JSON：{{sentiment_score:0-100 分數, sentiment_tag:標籤字串, analysis_summary:一句話短結, advice:投資建議字串, prediction_price:[預測未來三天價格的3個數字]}}"

    try:
        # 呼叫 Gemini 2.0 Flash 模型產生內容
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        # 解析 AI 回傳的 JSON 文字
        ai_result = json.loads(response.text)
        
        # 整合 CSV 原始數據與 AI 分析結果
        final_result = {
            "name": name, 
            "current_price": price,
            "sentiment_score": ai_result.get("sentiment_score", 50),
            "analysis_summary": ai_result.get("analysis_summary", ""),
            "advice": ai_result.get("advice", ""),
            "prediction_price": ai_result.get("prediction_price", [price]*3) # 若無預測則給予目前價格
        }
        
        # 將結果存入快取，供下次搜尋使用
        analysis_cache[search_code] = final_result
        return jsonify(final_result)
        
    except Exception as e:
        print(f"❌ AI 分析出錯: {e}")
        return jsonify({"error": "AI 分析服務暫時不可用"}), 500

# --- 4. 啟動伺服器 ---
if __name__ == '__main__':
    # debug=True 代表開發模式，檔案修改存檔後會自動重新載入
    app.run(debug=True, port=5000)