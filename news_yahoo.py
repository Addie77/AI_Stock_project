import requests
from bs4 import BeautifulSoup
from newspaper import Article, Config
import time
import random
from datetime import datetime, timedelta

# symbol 參數:股票代碼，每日上限 daily_limit
def scrap_yahoo(symbol, daily_limit=30):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'}
    config = Config()
    config.browser_user_agent = headers['User-Agent']
    config.fetch_images = False
    config.memoize_articles = False
    
    target_url = f'https://tw.news.yahoo.com/search?p={symbol}'
    print(f"--- 開始抓取 {symbol} 相關新聞 ---")

    # 只抓三天時間範圍的新聞，naive 單純的數字時間 
    now = datetime.now().replace(tzinfo=None)
    deadline = now - timedelta(days=3)

    # 紀錄每一天(日期字串)抓了幾則
    daily_counts = {}

    try:
        response = requests.get(target_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        #避免抓到側邊欄，優先鎖定搜尋結果容器
        container = soup.find('div', id='Main') #or soup
        all_a_tags = container.find_all('a', href=True)

        results = [] #放最後結果
        seen_titles = set() #看過的標題
        processed_urls = set() #處理過的網址

        for a in all_a_tags:
            url = a['href'] #提取網址連結
            #
            if 'search' not in url and url not in processed_urls:
                if url.startswith('/'):
                    url = 'https://tw.news.yahoo.com' + url
                
                processed_urls.add(url)

                try:
                    target = Article(url, config=config, language='zh')
                    target.download() #下載網頁
                    target.parse() #解析出標題內文日期

                    dt_tw = None
                    publish_time = "未知"

                    if target.publish_date:
                        # 去掉時區資訊以便比較
                        dt_tw = target.publish_date.replace(tzinfo=None)
                        publish_time = dt_tw.strftime('%Y/%m/%d %H:%M')
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

                    # 時間加權核心邏輯：檢查日期與配額
                    if dt_tw:
                        if dt_tw < deadline:
                            continue # 太舊了，跳過
                        
                        # 取得日期 Key (例如 "2026/04/17")
                        date_key = dt_tw.strftime('%Y/%m/%d')
                        current_count = daily_counts.get(date_key, 0)

                        if current_count >= daily_limit:
                            # 該日期配額已滿，跳過
                            continue
                    else:
                        continue # 沒有時間資訊的新聞無法進行權重分配，跳過

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
                        "source": "Yahoo 新聞",
                        "time": publish_time,
                        "full_text" : content,
                        "link" : url
                    }

                    seen_titles.add(clean_title) #將看過且去掉空格的標題放入 clean_title 防止抓取重複新聞
                    results.append(news_dict) #將打包好的新聞dict放入results
                    
                    # [新增] 更新該日期的抓取數量
                    daily_counts[date_key] = current_count + 1

                    # [修改] 判斷是否三天的總目標都達成了 (3 天 * 每日上限)
                    if len(results) >= daily_limit * 3:
                        break
                    
                    time.sleep(random.uniform(2,4)) # 搜尋時稍微加快速度

                except:
                    continue #如果抓取過程發生任何錯誤 則跳過

        #顯示結果
        print("\n" + "=" * 60)
        # [新增] 統計報告
        print(f"抓取統計: {daily_counts}")
        
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
    # [修改] 測試輸入
    stock = input("請輸入搜尋代碼: ")
    scrap_yahoo(symbol=stock, daily_limit=30)