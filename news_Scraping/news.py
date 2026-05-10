import sys
import os
import time
import random
from news_cnyes import scrap_cnyes
from news_ettoday import scrap_ettoday
from news_yahoo import scrap_yahoo
from api_sender import send_news_to_springboot
import json
from opencc import OpenCC

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir,".."))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from sentiment_model.sentiment_analyzer import SentimentAnalyzer


def process_and_save(data_list):
    if not data_list:
        print("沒有資料可以儲存")
        return
    print("\n 繁體轉簡體")

    cc = OpenCC('t2s')

    print("正在載入 AI 情緒分析引擎 (這可能需要幾秒鐘)...")
    analyzer = SentimentAnalyzer()

    print("開始進行【繁簡轉換】與【情緒評分】...")
    for i,item in enumerate(data_list):
        item['title'] = cc.convert(item['title'])
        item['text'] = cc.convert(item['text'])

        scores = analyzer.analyze_text(item['text'])

        item.update(scores)

        if (i + 1) % 5 == 0:
            print(f"已完成處理 {i + 1}/{len(data_list)} 筆新聞...")

    print("\n 準備儲存 JSON 檔...")
    file_name = "news_data.json"

    try:
        with open(file_name, 'w', encoding='utf-8') as f:
            json.dump(data_list, f, ensure_ascii=False, indent=4)
        print(f"--- 成功儲存至: {file_name} ---")
    except Exception as e:
        print(f"儲存 JSON 失敗: {e}")

def news():
    all_news_results = []
    # limit_per_source = 5

    stock = ""
    
    print("=== 開始 ===")
    print("\n 抓取新聞...")
    
    try:
        stock = input("請輸入搜尋代碼: ")
        yahoo_news = scrap_yahoo(symbol=stock, daily_limit=30)
        all_news_results.extend(yahoo_news)
        print("成功獲取新聞")
    except Exception as e:
        print(f"新聞抓取失敗: {e}")

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

    print("\n" + "=" * 60)
    if not all_news_results:
        print("未抓取到任何新聞")
    else:
        for i, news in enumerate(all_news_results, 1):
            print(f"({i}) [標題]: {news['title']}")
            print(f"({i}) [ 連結 ]: {news['link']}")
            #print(f"    [來源]: {news['source']}")
            print(f"    [時間]: {news['time']}")
            #preview = news['full_text'][:100].replace('\n', ' ')
            print(f"    [摘要]: {news['text']}")
            print("-" * 60)
    return stock, all_news_results

if __name__ == "__main__":
    stock_id, data = news()
    # 3把資料交給我們的發送小幫手，打進 Spring Boot！
    # send_news_to_springboot(stock_id, data)
    #存一份 JSON 在本機
    process_and_save(data)
    
    