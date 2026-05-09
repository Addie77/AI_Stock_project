import requests
from bs4 import BeautifulSoup
from newspaper import Article, Config
import time
import random
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
# [新增] 引入 By 模組用來找按鈕
from selenium.webdriver.common.by import By 

# symbol 參數:股票代碼，每日上限 daily_limit
def scrap_yahoo(symbol, daily_limit=30):

    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 不開啟瀏覽器視窗
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # [新增] 強制設定 User-Agent，蓋掉 Headless 機器人特徵
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    chrome_options.add_argument(f"--user-agent={user_agent}")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    headers = {'User-Agent': user_agent}
    config = Config()
    config.browser_user_agent = headers['User-Agent']
    config.fetch_images = False
    config.memoize_articles = False

    target_url = f'https://tw.news.yahoo.com/search?p={symbol}'
    print(f"--- 開始抓取 {symbol} 相關新聞 ---")

    now = datetime.now().replace(tzinfo=None)
    deadline = now - timedelta(days=3)
    daily_counts = {}

    try:
        driver.get(target_url)

        # [修改] 放棄瞬間移動，改用「平滑連續捲動」破解防跳躍機制
        print(f"--- 開始動態加載新聞 ---")
        for i in range(15): # 嘗試往下加載 8 批
            print(f"往下捲動加載中... 批次 ({i+1})")
            
            # 模擬真人滾動滑鼠，每次往下滾 600 像素，連續滾 5 次
            for _ in range(5):
                driver.execute_script("window.scrollBy(0, 600);")
                time.sleep(0.5)
                
            # 滾完一段後，等待新新聞長出來
            time.sleep(2.5)

            # [新增] 如果遇到「顯示更多」的按鈕，自動點擊
            try:
                # 尋找各種可能的載入按鈕
                more_btn = driver.find_element(By.XPATH, "//*[contains(text(), '更多結果') or contains(text(), '更多新聞') or contains(text(), '載入更多')]")
                if more_btn.is_displayed():
                    driver.execute_script("arguments[0].click();", more_btn)
                    print("--> 發現並點擊『載入更多』按鈕")
                    time.sleep(2)
            except:
                pass # 沒找到按鈕就繼續往下滾
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # [確認] 印出到底抓到幾個 h3，藉此驗證滾動是否成功
        # containers = soup.find_all('h3', class_='Mb(5px)')

        # [修改] 放棄綁定特定的 CSS Class，改抓大範圍
        # 為了避免抓到側邊欄，優先鎖定搜尋結果容器 (如果 id 沒變的話)
        a_tags = soup.select('#mfi-search-stream li h3 a[href]')        # [修改] 直接抓取容器內所有的 <h3> 標籤
        if not a_tags:
            a_tags = soup.select('h3 a[href]')
            print("⚠️ 警告：找不到主要的搜尋結果區塊，改為全域抓取")
        
        print(f"\n====================================")
        print(f"🟢 DEBUG: 利用 Selector 成功抓到 {len(a_tags)} 個新聞連結")
        print(f"====================================\n")
        
        driver.quit() # 拿到資料後關閉瀏覽器
        
        results = [] 
        seen_titles = set() 
        processed_urls = set() 

        for tag in a_tags:
            url = tag['href']
            if not url:
                continue
                 
            
            if 'search' not in url and url not in processed_urls:
                if url.startswith('/'):
                    url = 'https://tw.news.yahoo.com' + url
                
                processed_urls.add(url)

                try:
                    target = Article(url, config=config, language='zh')
                    target.download() 
                    target.parse() 

                    dt_tw = None
                    publish_time = "未知"

                    if target.publish_date:
                        dt_tw = target.publish_date.replace(tzinfo=None)
                        publish_time = dt_tw.strftime('%Y/%m/%d %H:%M')
                    else: 
                        article_soup = BeautifulSoup(target.html,'html.parser')
                        time_tag = article_soup.find('time')
                        if time_tag: 
                            raw_dt = time_tag['datetime'] 
                            dt = datetime.strptime(raw_dt[:19], '%Y-%m-%dT%H:%M:%S')
                            dt_tw = dt + timedelta(hours=8)
                            publish_time = dt_tw.strftime('%Y/%m/%d %H:%M')
                        else:
                            publish_time = time_tag.text.strip() if time_tag else "未知"

                    if dt_tw:
                        if dt_tw < deadline:
                            continue 
                        
                        date_key = dt_tw.strftime('%Y/%m/%d')
                        current_count = daily_counts.get(date_key, 0)

                        if current_count >= daily_limit:
                            continue
                    else:
                        continue 

                    raw_title = target.title.strip() 

                    junk_keywords = ["Yahoo股市", "Yahoo奇摩", "專輯", "信箱"] 
                    if any(junk in raw_title for junk in junk_keywords) and len(raw_title) < 15:
                        continue 
                    clean_title = "".join(raw_title.split()) 
                    if len(clean_title) < 10 or clean_title in seen_titles:
                        continue 

                    content = target.text.strip() 
                    garbage_text = "將 Yahoo 設為首選來源，在 Google 上查看更多我們的精彩報導"
                    content = content.replace(garbage_text, "").strip() 

                    if "，" not in content:
                        continue 

                    news_dict = {
                        "title": raw_title,
                        "source": "Yahoo 新聞",
                        "time": publish_time,
                        "full_text" : content,
                        "link" : url
                    }

                    seen_titles.add(clean_title) 
                    results.append(news_dict) 
                    daily_counts[date_key] = current_count + 1

                    if len(results) >= daily_limit * 3:
                        break
                    
                    time.sleep(random.uniform(1,2)) 

                except:
                    continue 

        print("\n" + "=" * 60)
        print(f"抓取統計: {daily_counts}")
        
        for i, news in enumerate(results, 1): 
            print(f"({i}) [ 標題 ]: {news['title']}")
            print(f"    [ 來源 ]: {news['source']}")
            print(f"    [ 時間 ]: {news['time']}")

            preview = news['full_text'][:50].replace('\n',' ') 
            print(f"    [ 內文 ]: {preview}...")
            print("-" * 60)
        return results
        
    except Exception as e:
        print(f"連線失敗:{e}")
        if 'driver' in locals():
            driver.quit()
        return []
    
if __name__ == "__main__":
    stock = input("請輸入搜尋代碼: ")
    scrap_yahoo(symbol=stock, daily_limit=30)