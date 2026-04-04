import requests
from bs4 import BeautifulSoup
from newspaper import Article, Config
import time
import random
from datetime import datetime, timedelta

def scrap_yahoo(limit=5):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'}
    config = Config()
    config.browser_user_agent = headers['User-Agent']
    config.fetch_images = False
    config.memoize_articles = False
    
    target_url = 'https://tw.stock.yahoo.com/tw-market'
    print(f"--- 開始 ---")

    try:
        response = requests.get(target_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        all_a_tags = soup.find_all('a', href=True)

        results = [] #放最後結果
        seen_titles = set() #看過的標題
        processed_urls = set() #處理過的網址

        for a in all_a_tags:
            url = a['href'] #提取網址連結
            if 'news' in url and len(url) > 40 and url not in processed_urls:
                if url.startswith('/'):
                    url = 'https://tw.stock.yahoo.com' + url
                elif url.startswith('https://tw.news.yahoo.com'):
                    pass
                processed_urls.add(url)

                try:
                    target = Article(url, config=config, language='zh')
                    target.download() #下載網頁
                    target.parse() #解析出標題內文日期

                    publish_time = "未知"

                    if target.publish_date:
                        publish_time = target.publish_date.strftime('%Y/%m/%d  %H:%M0')
                    else: #抓不到時間時 改用BeautifulSoup在HTML找<time>標籤
                        article_soup = BeautifulSoup(target.html,'html.parser')
                        time_tag = article_soup.find('time')
                        if time_tag: #轉時區
                            raw_dt = time_tag['datetime'] # 取得 2026-04-05T02:00:00Z
                            dt = datetime.strptime(raw_dt[:19], '%Y-%m-%dT%H:%M:%S')
                            dt_tw = dt + timedelta(hours=8)
                            publish_time = dt_tw.strftime('%Y/%m/%d %H:%M')
                        else:
                            publish_time = time_tag.text.strip()

                    raw_title = target.title.strip() #取得標題並去除前後空白
                    junk_keywords = ["Yahoo股市", "Yahoo奇摩", "專輯", "信箱"] #定義垃圾字詞
                    if any(junk in raw_title for junk in junk_keywords) and len(raw_title) < 15:
                        continue #如果有垃圾字詞 如果標題字數小於15 就跳過 回到line 26
                    clean_title = "".join(raw_title.split()) #把標題內的空格都拿掉
                    if len(clean_title) < 10 or clean_title in seen_titles:
                        continue #標題太短或重複就跳過

                    content = target.text.strip() #取得新聞內容

                    garbage_text = "將 Yahoo 設為首選來源，在 Google 上查看更多我們的精彩報導"
                    content = content.replace(garbage_text, "").strip() # 將該字串替換成空字串，並再次去除前後空白

                    if "，" not in content:
                        continue #若內文沒有逗號 代表內容很零碎或沒抓到內容 跳過

                    news_dict = {
                        "title": raw_title,
                        "source": "Yahoo 財經新聞",
                        "time": publish_time,
                        "full_text" : content,
                        "link" : url
                    }

                    seen_titles.add(clean_title) #將看過且去掉空格的標題放入 clean_title 防止抓取重複新聞
                    results.append(news_dict) #將打包好的新聞dict放入results

                    if len(results) >= limit:
                        break
                    time.sleep(random.uniform(1,3))

                except:
                    continue #如果抓取過程發生任何錯誤 則跳過

        #顯示結果
        print("\n" + "=" * 60)
        for i, news in enumerate(results, 1): #遍歷result清單;news為那則新聞的字典資料
            print(f"({i}) [ 標題 ]: {news['title']}")
            print(f"    [ 來源 ]: {news['source']}")
            print(f"    [ 時間 ]: {news['time']}")

            preview = news['full_text'][:50].replace('\n',' ') #只取前五十字預覽 將換行變成空格
            print(f"    [ 內文 ]: {preview}...")
            print("-" * 60)
        return results
        
    except Exception as e:
        print(f"連線失敗:{e}")
        return []
    
if __name__ == "__main__":
    scrap_yahoo(limit=5)
