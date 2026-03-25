import time
import random
from news_cnyes import scrap_cnyes
from news_ettoday import scrap_ettoday
from news_yahoo import scrap_yahoo

def news():
    all_news_results = []
    limit_per_source = 5

    print("=== 開始 ===")

    print("\n 抓取 yahoo 財經新聞...")

    try:
        yahoo_news = scrap_yahoo(limit=limit_per_source)
        all_news_results.extend(yahoo_news)
        print("成功獲取 yahoo 財經新聞")
    except Exception as e:
        print(f" yahoo 財經新聞 抓取失敗: {e}")

    print("\n 抓取 ETtoday 財經雲...")

    try:
        ettoday_news = scrap_ettoday(limit=limit_per_source)
        all_news_results.extend(ettoday_news)
        print("成功獲取 ETtoday 財經雲")
    except Exception as e:
        print(f" ETtoday 財經雲 抓取失敗: {e}")

    print("\n 抓取 鉅亨網...")

    try:
        cnyes_news = scrap_cnyes(limit=limit_per_source)
        all_news_results.extend(cnyes_news)
        print("成功獲取 鉅亨網")
    except Exception as e:
        print(f" 鉅亨網 抓取失敗: {e}")

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
    news()