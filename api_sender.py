import requests
from datetime import datetime

def send_news_to_springboot(stock_id, stock_name="未知股票", news_list=None):
    """接收爬蟲資料，補齊模擬的 AI 欄位後，發送給 Spring Boot"""
    
    api_url = "http://localhost:8080/api/ingest/news"
    
    if not news_list:
        print("沒有資料可以發送！")
        return
    
    print(f"\n準備將 {len(news_list)} 筆新聞發送至 Spring Boot (Stock: {stock_name} [{stock_id}])...")
    
    for index, item in enumerate(news_list):
        # 1. 從爬蟲字典抓取已有資料 (這裡用 .get() 防呆，萬一 key 不存在也不會當機)
        title = item.get('title', '無標題')
        url = item.get('link')
        raw_time = item.get('time')
        sentiment_data = item.get('sentiment_result', {})
        composite_score = sentiment_data.get('Composite_Score', 0.0)
        text = item.get('text')
        # 爬下來的時間可能是 "2026-05-09 10:30:00"，但 Java 需要 "2026-05-09T10:30:00"
        try:
            parsed_time = datetime.strptime(raw_time, "%Y-%m-%d %H:%M:%S")
            java_date = parsed_time.strftime("%Y-%m-%dT%H:%M:%S")
        except BaseException:
            # 如果時間格式解析失敗(例如有些新聞只寫"2小時前")，為了不讓程式崩潰，先用現在時間墊檔
            java_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        # 2. 組合 Payload，加入未完工的 AI 模擬資料
        payload = {
            "stockId": stock_id,
            "stockName": stock_name, # 💡 新增：傳遞正確股票名稱
            "title": title,
            "contentUrl": url,
            "publishDate": java_date,
            "sentimentScore": composite_score,
            "contentSummary": text
        }
        
        # 3. 發射 POST 請求
        try:
            response = requests.post(api_url, json=payload)
            if response.status_code == 200:
                print(f"✅ [{index+1}/{len(news_list)}] 成功: {title[:15]}...")
            else:
                print(f"❌ [{index+1}/{len(news_list)}] 失敗 ({response.status_code}): {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("\n⚠️ 連線失敗！請確認你的 Spring Boot 伺服器 (8080 port) 正在執行中。")
            break

def send_report_to_springboot(stock_id, stock_name="未知股票", avg_score=0.0, gemini_summary=""):
    """將計算好的平均分數與 Gemini 總結發送給 Spring Boot"""
    api_url = "http://localhost:8080/api/ingest/report"
    # 抓取今天日期，格式為 YYYY-MM-DD
    today_str = datetime.now().strftime("%Y-%m-%d")

    payload = {
        "stockId": str(stock_id),
        "stockName": stock_name, # 💡 新增：傳遞正確股票名稱
        "analysisDate": today_str,
        "avgSentiment": float(avg_score),
        "overallSummary": gemini_summary,
        "reportType": "DEEP_AI" # 標記為深度分析
    }

    print(f"\n準備將 {stock_name} ({stock_id}) 的總評報告發送至 Spring Boot...")

    try:
        response = requests.post(api_url, json=payload)
        if response.status_code == 200:
            print(f"✅ 報告發送成功: {response.text}")
        else:
            print(f"❌ 報告發送失敗 ({response.status_code}): {response.text}")

    except requests.exceptions.ChunkedEncodingError:
        print("\n⚠️ 連線失敗！請確認 Spring Boot 伺服器 (8080 port) 正在執行中。") 
