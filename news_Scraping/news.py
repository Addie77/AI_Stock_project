import sys
import os
import json
from opencc import OpenCC

# 1. 💡 先計算並加入父目錄路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir,".."))

if current_dir not in sys.path:
    sys.path.append(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# 2. 💡 路徑加完後，再 import 根目錄的檔案
from news_yahoo import scrap_yahoo
from api_sender import send_news_to_springboot
from sentiment_model.sentiment_analyzer import SentimentAnalyzer

# --- 全域變數定義 ---
# 將分析器設為全域變數並初始為 None，實現「懶載入」，避免重複啟動耗時
_analyzer = None
_cc = OpenCC('t2s')

def get_analyzer():
    """ 確保 BERT 模型只會被載入一次 """
    global _analyzer
    if _analyzer is None:
        print("🧠 正在載入 FinBERT 情緒分析引擎 (模型較大，請稍候)...")
        _analyzer = SentimentAnalyzer()
    return _analyzer

def process_sentiment_and_conversion(data_list):
    """ 處理繁簡轉換與情緒評分 """
    if not data_list:
        return
    
    analyzer = get_analyzer()
    print(f"開始處理 {len(data_list)} 筆新聞的繁簡轉換與情緒評分...")
    
    for i, item in enumerate(data_list):
        # 1. 繁簡轉換 (BERT 模型在簡體中文上表現較精準)
        item['title'] = _cc.convert(item['title'])
        item['text'] = _cc.convert(item['text'])

        # 2. 呼叫 BERT 模型進行分析
        scores = analyzer.analyze_text(item['text'])

        # 3. 封裝結果
        item['sentiment_result'] = {
            "Positive": scores.get("Positive", 0.0),
            "Neutral": scores.get("Neutral", 0.0),
            "Negative": scores.get("Negative", 0.0),
            "Composite_Score": scores.get("Composite_Score", 0.0)
        }

        if (i + 1) % 5 == 0:
            print(f"已完成處理 {i + 1}/{len(data_list)} 筆新聞...")

def run_full_news_pipeline(stock_id):
    """
    一鍵執行流：爬蟲 -> 情緒分析 -> 存入 JSON -> 回傳資料
    供外部 (如 gemini.py) 調用。
    """
    all_news_results = []
    # limit_per_source = 5

    print(f"\n🚀 [Pipeline] 開始執行 {stock_id} 的完整新聞任務...")
    
    try:
        yahoo_news = scrap_yahoo(symbol=stock_id, daily_limit=30) 
        all_news_results.extend(yahoo_news)
        print("成功獲取 Yahoo 新聞")
    except Exception as e:
        print(f"Yahoo 新聞抓取失敗: {e}")

    # 保留備用爬蟲程式碼
    # print("\n 抓取 ETtoday 財經雲...")
    # try:
    #     ettoday_news = scrap_ettoday(limit=limit_per_source)
    #     all_news_results.extend(ettoday_news)
    #     print("成功獲取 ETtoday 財經雲")
    # except Exception as e:
    #     print(f" ETtoday 財經雲 抓取失敗: {e}")

    # print("\n 抓取 鉅亨網...")
    # try:
    #     cnyes_news = scrap_cnyes(limit=limit_per_source)
    #     all_news_results.extend(cnyes_news)
    #     print("成功獲取 鉅亨網")
    # except Exception as e:
    #     print(f" 鉅亨網 抓取失敗: {e}")

    if not all_news_results:
        print(f"⚠️ 無法獲取股票 {stock_id} 的任何相關新聞")
        return None
    
    # 2. 執行分析與轉換
    process_sentiment_and_conversion(all_news_results)

    # 3. 儲存一份備份 JSON 在本地 (除錯用)
    # file_name = "news_data.json"
    # try:
    #     with open(file_name, 'w', encoding='utf-8') as f:
    #         json.dump(all_news_results, f, ensure_ascii=False, indent=4)
    #     print(f"--- 成功儲存至: {file_name} ---")
    # except Exception as e:
    #     print(f"本地 JSON 儲存失敗: {e}")

    print(f"✨ {stock_id} 新聞任務執行完成！")
    return all_news_results

# --- 手動測試區塊 ---
if __name__ == "__main__":
    # 讓手動執行時也能走相同的 Pipeline
    stock_input = input("請輸入搜尋代碼 (如 2330): ").strip()
    if stock_input:
        data = run_full_news_pipeline(stock_input)
        if data:
            # 手動執行時，順便發送到 Spring Boot 驗證 (測試時名稱代入代號)
            send_news_to_springboot(stock_input, f"Manual_Test_{stock_input}", data)
