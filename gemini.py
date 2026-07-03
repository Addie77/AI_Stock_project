import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
from google.genai import types
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
import json
import requests
import threading

# 💡 輔助函式：處理 Gemini API 503 錯誤與重試機制
def is_503_error(exception):
    """判斷是否為 503 暫時性過載錯誤"""
    return "503" in str(exception) or "UNAVAILABLE" in str(exception)

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=4, min=4, max=60),
    retry=retry_if_exception(is_503_error),
    before_sleep=lambda retry_state: print(f"⚠️ [{retry_state.args[3] if len(retry_state.args) > 3 else 'Gemini'}] 伺服器忙碌 (503)，正在進行第 {retry_state.attempt_number} 次重試...")
)
def gemini_generate_with_retry(client, model, contents, task_label="未指定任務", config=None):
    """封裝帶有重試機制的內容生成函式"""
    if config:
        return client.models.generate_content(model=model, contents=contents, config=config)
    return client.models.generate_content(model=model, contents=contents)

# 💡 模組化解耦匯入
from stock import get_stock_historical_data
from news_Scraping.news import run_full_news_pipeline
from api_sender import send_news_to_springboot, send_report_to_springboot

# --- 1. 初始化環境與核心組件 (Initialization & Setup) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

app = Flask(__name__)
CORS(app)

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# 記憶體快取防禦機制
stock_cache = {}
ai_cache = {}
news_tasks = {}

# ============================================================================
# --- 2. API 路由 1：輸出真實歷史數據（加入 NaN 價格清洗防禦） ---
# ============================================================================
@app.route('/api/analyze', methods=['GET'])
def analyze():
    code = request.args.get('code', '').strip().zfill(4)
    
    if code in stock_cache:
        return jsonify(stock_cache[code])

    try:
        df_hist = get_stock_historical_data(code)
    except Exception as e:
        print(f"❌ 呼叫 stock.py 崩潰: {e}")
        return jsonify({"error": "內部資料擷取模組執行異常"}), 500

    if df_hist is None or df_hist.empty:
        return jsonify({"error": f"無法從證交所取得股票代碼 {code} 的歷史資料，請確認網路連線或代碼是否正確"}), 404

    name = df_hist.iloc[0]['名稱'] if '名稱' in df_hist.columns else "未知個股"
    dates = df_hist['日期'].tolist()      
    
    # 原始的字串價格與成交量陣列
    raw_prices = df_hist['收盤價'].tolist() if '收盤價' in df_hist.columns else []
    
    # 多重欄位比對成交量
    raw_volumes = []
    for col in ['成交量', 'TradeVolume', 'Volume', '成交股數', '成交張數']:
        if col in df_hist.columns:
            raw_volumes = df_hist[col].tolist()
            break

    if not dates or not raw_prices:
        return jsonify({"error": "官方數據格式不完整，無法解析日期或價格"}), 500

    # 💡 核心修正 1：後端價格清洗防線 (防禦 '--' 導致前端折線圖隱形)
    prices = []
    last_valid_price = None
    
    # 先找出第一個合法的價格當作初始備援值
    for p in raw_prices:
        try:
            clean_p = float(str(p).replace(',', '').strip())
            last_valid_price = clean_p
            break
        except (ValueError, TypeError):
            continue
            
    if last_valid_price is None:
        last_valid_price = 0.0

    # 逐日清洗價格
    for p in raw_prices:
        try:
            clean_p = float(str(p).replace(',', '').strip())
            prices.append(clean_p)
            last_valid_price = clean_p 
        except (ValueError, TypeError):
            print(f"⚠️ 偵測到個股 {code} 歷史收盤價含有異常字串 '{p}'，已啟動 Forward Fill 機制補齊。")
            prices.append(last_valid_price)

    # 💡 核心修正 2：後端成交量清洗防線
    volumes = []
    for v in (raw_volumes if raw_volumes else [0] * len(prices)):
        try:
            clean_v = int(str(v).replace(',', '').replace('--', '0').strip())
            volumes.append(clean_v)
        except (ValueError, TypeError):
            volumes.append(0)

    current_price = prices[-1]           

    # 💡 智慧防禦：讀取 Spring Boot 資料庫分數，預設回補 0 分
    real_score = 0
    try:
        java_res = requests.get(f"http://localhost:8080/api/stocks/{code}", timeout=2)
        if java_res.status_code == 200:
            java_data = java_res.json()
            # 優先從 Java 獲取分數，若無則預設為 0
            real_score = java_data.get("averageSentimentScore", 0)
    except Exception as e:
        print(f"⚠️ 無法取得 Java 資料庫現有分數 (Spring Boot 可能未啟動): {e}")

    # 封裝標準 JSON 回應包
    result = {
        "name": name,
        "current_price": current_price,
        "history_dates": dates,     
        "history_prices": prices,   
        "history_volumes": volumes,  
        "sentiment_score": real_score
    }
    
    stock_cache[code] = result
    return jsonify(result)

# ============================================================================
# --- 3. 新聞同步背景路由 (兩階段智慧載入) ---
# ============================================================================
@app.route('/api/sync_news', methods=['GET'])
def sync_news():
    code = request.args.get('code', '').strip().zfill(4)
    if not code:
        return jsonify({"error": "缺少股票代碼"}), 400
    
    if code in news_tasks and news_tasks[code]['status'] == 'running':
        return jsonify({"status": "already_running", "message": "任務已在背景執行中"})

    try:
        java_res = requests.get(f"http://localhost:8080/api/stocks/{code}", timeout=2)
        if java_res.status_code == 200:
            java_data = java_res.json()
            
            # 💡 方案 B 關鍵邏輯：只有當報告存在且類型為 'DEEP_AI' 時，才跳過爬蟲
            report_type = java_data.get("reportType")
            if java_data.get("averageSentimentScore") and java_data.get("overallAiSummary") and report_type == "DEEP_AI":
                print(f"🎯 {code} 今日已有深度分析報告，跳過爬蟲。")
                avg_score = java_data.get("averageSentimentScore")
                summary_text = java_data.get("overallAiSummary")
                
                news_tasks[code] = {
                    "status": "completed",
                    "avg_sentiment": avg_score,
                    "ai_summary": summary_text
                }
                return jsonify({
                    "status": "completed", 
                    "message": "今日深度報告已存在，直接載入快取數據",
                    "avg_sentiment": avg_score,
                    "ai_summary": summary_text
                })
            else:
                print(f"📝 {code} 目前僅有模板報告或資料未完全 (Type: {report_type})，準備執行深度 AI 分析...")
    except Exception as e:
        print(f"⚠️ 檢查 Java 報告失敗: {e}")

    if code in ai_cache:
        del ai_cache[code]

    news_tasks[code] = {"status": "running", "avg_sentiment": 0, "ai_summary": "正在處理中..."}

    def background_sync(stock_id):
        print(f"📡 [Background] 開始處理 {stock_id} 的新聞同步流程...")
        try:
            # 💡 新增：從快取中取得股票名稱
            stock_name = stock_cache.get(stock_id, {}).get('name', '未知股票')

            analyzed_data = run_full_news_pipeline(stock_id)
            if not analyzed_data:
                news_tasks[stock_id] = {"status": "error", "message": "未能獲取新聞資料"}
                return
            
            # 傳遞股票名稱
            send_news_to_springboot(stock_id, stock_name, analyzed_data)

            scores = [item.get('sentiment_result', {}).get('Composite_Score', 50) for item in analyzed_data]
            avg_score = round(sum(scores) / len(scores), 2)

            news_text = "\n".join([f"新聞: {n['title']}\n內容: {n['text']}" for n in analyzed_data[:10]])
            
            # 💡 方案 B 擴充：根據分數決定情緒標籤，並強迫 Gemini 加入總評開頭
            if avg_score >= 80:
                tag = "【極度樂觀】"
            elif avg_score >= 60:
                tag = "【偏向樂觀】"
            elif avg_score >= 40:
                tag = "【中立觀望】"
            else:
                tag = "【警訊注意】"

            prompt = (
                f"你是一名專業財經分析師。股票 {stock_id} 的最新新聞平均情緒分數為 {avg_score}，市場情緒等級為 {tag}。\n"
                f"以下是新聞內容摘要：\n{news_text}\n\n"
                f"請分析目前的新聞對股價的潛在影響，給出一段 150 字內的綜合總評。\n"
                f"【注意】請務必在總評的最開頭加上標籤「{tag}」。"
            )
            # 使用重試機制呼叫 Gemini
            # response = gemini_generate_with_retry(client, model="gemini-3-pro-preview", contents=prompt, task_label="新聞總評")  #換模型3，把原本的註解掉
            response = gemini_generate_with_retry(client, model="gemini-2.5-flash", contents=prompt, task_label="新聞總評")
            gemini_summary = response.text.strip()

            if stock_id in stock_cache:
                stock_cache[stock_id]['sentiment_score'] = avg_score

            # 傳遞股票名稱
            send_report_to_springboot(stock_id, stock_name, avg_score, gemini_summary)
            
            news_tasks[stock_id] = {
                "status": "completed",
                "avg_sentiment": avg_score,
                "ai_summary": gemini_summary
            }
            print(f"✨ [Background] {stock_id} 新聞處理完成！")
        except Exception as e:
            print(f"❌ [Background] 同步失敗: {e}")
            news_tasks[stock_id] = {"status": "error", "message": str(e)}

    thread = threading.Thread(target=background_sync, args=(code,))
    thread.start()
    return jsonify({"status": "started", "message": "已在背景啟動新聞爬蟲與分析任務"})

@app.route('/api/check_status', methods=['GET'])
def check_status():
    code = request.args.get('code', '').strip().zfill(4)
    status_info = news_tasks.get(code, {"status": "not_found"})
    return jsonify(status_info)


# ============================================================================
# --- 4. API 路由 2：調用雲端大語言模型產生技術面形態報告 ---
# ============================================================================
@app.route('/api/generate_ai', methods=['GET'])
def generate_ai():
    code = request.args.get('code', '').strip().zfill(4)
    
    if code in ai_cache:
        return jsonify(ai_cache[code])

    if code in stock_cache:
        base_data = stock_cache[code]
        name = base_data["name"]
        current_price = base_data["current_price"]
        final_sentiment_score = base_data["sentiment_score"]
        prices = base_data["history_prices"] 
    else:
        return jsonify({"error": "請先進行股票基本搜尋以載入數據來源"}), 400

    prompt = (
        f"你是一名精通技術分析、形態學與市場心理學的資深台股首席分析師。\n"
        f"目前系統利用本地端 FinBERT 模型對 {name}({code}) 計算出的客觀市場情感分數為 {final_sentiment_score} 分（滿分 100）。\n"
        f"最新真實收盤價為 {current_price} 元。過去一段時間的連續歷史價格序列為：{prices[-15:]}。\n\n"
        f"請針對該個股過去 3 個月的走勢特徵，撰寫一份極為詳盡、專業且充實的技術面分析報告。\n"
        f"報告必須包含以下四大核心維度：\n"
        f"1. 形態學解讀（如：箱型整理、頭肩底、多頭排列、或是高檔背離等突破/修正訊號）。\n"
        f"2. 情感分數結合：深入闡述 FinBERT 算出的 {final_sentiment_score} 分在量價結構上代表的散戶與法人心理拉鋸。\n"
        f"3. 支撐與壓力位評估：根據最新價格 {current_price} 元，給出明確的短中長期支撐與壓力區間。\n"
        f"4. 實戰操作策略：提供分批佈局、停損、停利點的具體建議。\n\n"
        f"【重要限制】\n"
        f"- 內容篇幅請儘量詳盡充實（分析總結至少 150 字，操作建議至少 150 字），展現專業投顧報告的深度。\n"
        f"- 請嚴格回傳標準 JSON 格式，不可以包含任何 Markdown 的 ```json 標籤或其餘雜訊文字，直接以花括號開頭與結尾：\n"
        f'{{"analysis_summary":"此處填寫極為詳盡的技術形態與市場情緒深度分析總結（文長）", "advice":"此處填寫具體的實戰操作、資金配置、支撐壓力位與避險戰術策略建議（文長）"}}'
    )

    try:
        # 使用重試機制呼叫 Gemini
        response = gemini_generate_with_retry(
            client,
            # model="gemini-3-pro-preview", #換模型3，把原本的註解掉
            model="gemini-2.5-flash",
            contents=prompt,
            task_label="技術分析報告",
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        raw_text = response.text.replace("```json", "").replace("```", "").strip()
        ai_data = json.loads(raw_text, strict=False)
        result = {
            "analysis_summary": ai_data.get("analysis_summary"),
            "advice": ai_data.get("advice")
        }
        print(f"✨ Gemini 深度分析報告生成成功！({name})")
        
        if not result["analysis_summary"] or not result["advice"]:
            raise ValueError("AI 回傳欄位內容不完整")
        
        ai_cache[code] = result
        return jsonify(result)
            
    except Exception as e:
        print(f"❌ 雲端 AI 報告生成失敗: {e}")
        return jsonify({"error": "雲端 AI 服務暫時無法連線，報告生成失敗。請檢查您的 API 金鑰狀態或網路環境。"}), 502

if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)