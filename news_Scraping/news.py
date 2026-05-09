import time
import random
from news_cnyes import scrap_cnyes
from news_ettoday import scrap_ettoday
from news_yahoo import scrap_yahoo
import json
from opencc import OpenCC


def simp_and_save(data_list):
    if not data_list:
        print("沒有資料可以儲存")
        return
    print("\n 繁體轉簡體")

    cc = OpenCC('t2s')

    for item in data_list:
        item['title'] = cc.convert(item['title'])
        item['full_text'] = cc.convert(item['full_text'])

    print("\n 儲存JSON檔")

    # 執行儲存
    file_name = f"news_data.json"
    try:
        with open(file_name, 'w', encoding='utf-8') as f:
            json.dump(data_list, f, ensure_ascii=False, indent=4)
        print(f"--- 成功儲存至: {file_name} ---")
    except Exception as e:
        print(f"儲存 JSON 失敗: {e}")

def news():
    all_news_results = []
    # limit_per_source = 5

    print("=== 開始 ===")

    print("\n 抓取 yahoo 財經新聞...")

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
            print(f"    [來源]: {news['source']}")
            print(f"    [時間]: {news['time']}")
            preview = news['full_text'][:100].replace('\n', ' ')
            print(f"    [內容]: {preview}...")
            print("-" * 60)
    return all_news_results

if __name__ == "__main__":
    data = news()
    simp_and_save(data)