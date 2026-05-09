from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from newspaper import Article, Config
import time
from datetime import datetime, timedelta

def scrap_cnyes(limit=5):
    # 設定 Chrome 參數 不顯示視窗 (Headless 模式)
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")

    # 啟動瀏覽器
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    target_url = 'https://news.cnyes.com/news/cat/tw_stock'
    print(f"--- 開始 ---")

    try:
        driver.get(target_url)
        # 等待 JavaScript 渲染內容，確保新聞列表載入完成
        time.sleep(5) 
        
        # 取得渲染後的網頁原始碼並關閉瀏覽器
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        driver.quit() 

        # 定位新聞列表容器
        news_container = soup.find('div', class_='cxugd4c')
        if not news_container:
            print("依然找不到容器，可能網頁結構有變")
            return []

        all_a_tags = news_container.find_all('a', href=True)
        results = []
        processed_urls = set()

        for a in all_a_tags:
            url = a['href']
            # 補全網址
            if url.startswith('/'):
                url = 'https://news.cnyes.com' + url
            
            # 只有當網址包含 /news/id/ 且尚未「成功」抓取過才處理
            if '/news/id/' in url and url not in processed_urls:
                try:
                    config = Config()
                    config.browser_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
                    config.request_timeout = 10 # 設定逾時避免卡死

                    target = Article(url, config=config, language='zh')
                    target.download()
                    target.parse()

                    # 放寬內文限制
                    if len(target.text.strip()) < 50: 
                        continue

                    publish_time = "未知"

                    if target.publish_date:
                        publish_time = (target.publish_date + timedelta(hours=8)).strftime('%Y/%m/%d %H:%M')
                    else:
                        article_soup = BeautifulSoup(target.html, 'html.parser')
                        time_tag = article_soup.find('time')
                        if time_tag and time_tag.has_attr('datetime'):
                            raw_dt_str = time_tag['datetime'] # 格式如: 2026-04-05T02:00:00+08:00
                            # 鉅亨網有些格式會寫 +08:00，但為了保險我們統一處理前 19 位
                            dt_obj = datetime.strptime(raw_dt_str[:19], '%Y-%m-%dT%H:%M:%S')
                            # 如果字串結尾是 Z 或確認是 UTC，就加 8
                            if 'Z' in raw_dt_str.upper() or '+00:00' in raw_dt_str:
                                dt_obj = dt_obj + timedelta(hours=8)
                            publish_time = dt_obj.strftime('%Y/%m/%d %H:%M')

                    news_entry = {
                        "title": target.title.strip(),
                        "source": "鉅亨網",
                        "time": publish_time,
                        "full_text": target.text.strip(),
                        "link": url
                    }

                    results.append(news_entry)
                    processed_urls.add(url)
                    print(f"成功抓取: {news_entry['title'][:15]}...")

                    if len(results) >= limit: 
                        break
                        
                except Exception as e:
                    continue

        # --- 顯示結果 ---
        print("\n" + "=" * 60)
        for i, news in enumerate(results, 1):
            print(f"({i}) [ 標題 ]: {news['title']}")
            print(f"    [ 來源 ]: {news['source']}")
            print(f"    [ 時間 ]: {news['time']}")
            print(f"    [ 網址 ]: {news['link']}")
            
            preview = news['full_text'][:50].replace('\n', ' ')
            print(f"    [ 內文 ]: {preview}...")
            print("-" * 60)

        return results

    except Exception as e:
        print(f"Selenium 執行出錯: {e}")
        if 'driver' in locals():
            driver.quit()
        return []

if __name__ == "__main__":
    scrap_cnyes(limit=5)