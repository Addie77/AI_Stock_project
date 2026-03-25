from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from newspaper import Article, Config
import time

def scrap_cnyes(limit=5):
    # 設定 Chrome 參數：不顯示視窗 (Headless 模式)
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")

    # 啟動瀏覽器
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    target_url = 'https://news.cnyes.com/news/cat/tw_stock'
    print(f"--- 啟動瀏覽器模擬抓取 (鉅亨網) ---")

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

                    # 放寬內文限制：有些台股短評字數不多，調降至 50 字避免跳過
                    if len(target.text.strip()) < 50: 
                        continue

                    # 建立結果字典
                    news_entry = {
                        "title": target.title.strip(),
                        "source": "鉅亨網",
                        "link": url,
                        "full_text": target.text.strip(),
                        "time": target.publish_date.strftime('%Y/%m/%d %H:%M') if target.publish_date else "未知"
                    }

                    results.append(news_entry)
                    processed_urls.add(url) # 成功存入結果後，才標記為已處理
                    print(f"成功抓取: {news_entry['title'][:15]}...")

                    if len(results) >= limit: 
                        break
                        
                except Exception as e:
                    # 如果這一次嘗試失敗，不加入 processed_urls，讓迴圈有機會在下一個相同的連結重試
                    continue

        # --- 顯示結果 ---
        print("\n" + "=" * 60)
        for i, news in enumerate(results, 1):
            print(f"({i}) [ 標題 ]: {news['title']}")
            print(f"    [ 來源 ]: {news['source']}")
            print(f"    [ 時間 ]: {news['time']}")
            print(f"    [ 網址 ]: {news['link']}")
            
            # 預覽內文前 50 字
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