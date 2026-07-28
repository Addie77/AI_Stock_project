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
from selenium.webdriver.common.by import By 

import re
import jieba.analyse 

# 使用TextRank演算法 與 關鍵字密度 進行抽取式摘要
# 🟢 [修改] 增加 title 參數，用來過濾標題句子
def textrank_summary(text, title="", top_k=2):
    text_length = len(text) if text else 0
    if not text or text_length < 100:
        if text:
            preview = text[:50].replace('\n', ' ') + "..." if text_length > 50 else text
        else:
            preview = "無內容"
        print(f"   ℹ️ [摘要跳過] 內文過短 ({text_length} 字)，不執行 TextRank。內文預覽: [{preview}]")
        return text
        
    try:
        keywords = jieba.analyse.textrank(text, topK=20)
        
        # 精準斷句：使用正規表達式切分中文句子
        sentences = re.split(r'[。！？：；:;\[\]【】・/\\／〔〕]\s*', text)
        
        # 🟢 [修改] 過濾條件升級：拔除與標題重疊的句子
        clean_sentences = []
        title_no_space = title.replace(" ", "").replace(" ", "") # 移除標題空白以利比對
        
        for s in sentences:
            s_str = s.strip()
            if len(s_str) > 5:
                # 將句子也去除空白
                s_no_space = s_str.replace(" ", "").replace(" ", "")
                
                # 如果這句話包含在標題內，或標題包含在這句話內，直接捨棄，不參與評分
                if title_no_space and (s_no_space in title_no_space or title_no_space in s_no_space):
                    continue
                    
                clean_sentences.append(s_str)

        # 句子評分
        scored_sentences = []
        for s in clean_sentences:
            score = sum(1 for word in keywords if word in s)
            scored_sentences.append((score, s))

        # 挑選分數最高的前 top_k 句
        top_sentences = sorted(scored_sentences, key=lambda x: x[0], reverse=True)[:top_k]
        
        # 依照原始出現順序排列 
        # (因為我們在 sorted 時沒有保留原始 index，如果要有序，這段要改成先找回原始 index)
        # 這裡為了簡單，目前是依分數高低排列，若要依文章順序可以加 index，這邊先維持原本邏輯接合
        final_summary = "。".join([s for _, s in top_sentences]) + "。"
        return final_summary 
    except Exception as e: 
        print(f"   🔴 [演算法錯誤] TextRank 執行失敗: {e}")
        return text[:150] + "..."


# symbol 參數:股票代碼，每日上限 daily_limit
def scrap_yahoo(symbol, daily_limit=30):

    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 不開啟瀏覽器視窗
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    chrome_options.add_argument(f"--user-agent={user_agent}")
    
    print("🛠️  正在啟動 Chrome 瀏覽器...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    headers = {'User-Agent': user_agent}
    config = Config()
    config.browser_user_agent = headers['User-Agent']
    config.fetch_images = False
    config.memoize_articles = False

    target_url = f'https://tw.news.yahoo.com/search?p={symbol}'
    print(f"\n🚀 --- 開始抓取 {symbol} 相關新聞 ---")
    print(f"🔗 目標 URL: {target_url}")

    now = datetime.now().replace(tzinfo=None)
    deadline = now - timedelta(days=3)
    print(f"📅 篩選時間下限 (3天內): {deadline.strftime('%Y/%m/%d %H:%M')}")
    
    daily_counts = {}

    try:
        driver.get(target_url)

        print(f"\n⏳ --- 開始動態加載新聞 ---")
        for i in range(15): 
            print(f"   [批次 {i+1}/15] 正在向下捲動...")
            
            for _ in range(5):
                driver.execute_script("window.scrollBy(0, 600);")
                time.sleep(0.5)
                
            time.sleep(2.5)

            try:
                more_btn = driver.find_element(By.XPATH, "//*[contains(text(), '更多結果') or contains(text(), '更多新聞') or contains(text(), '載入更多')]")
                if more_btn.is_displayed():
                    driver.execute_script("arguments[0].click();", more_btn)
                    print("   --> 🎯 發現並點擊『載入更多』按鈕")
                    time.sleep(2)
            except:
                pass 
        
        print("\n📝 正在解析網頁 DOM 結構...")
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # 擴大搜尋範圍，確保能抓到新聞連結
        a_tags = soup.select('#mfi-search-stream li h3 a[href]')
        if not a_tags:
            a_tags = soup.select('div.NewsArticle a[href], div.StreamMegaItem a[href], h3 a[href]')
            if not a_tags:
                print("   ⚠️ 警告：找不到標準標籤，啟動備案：抓取全域 news 連結")
                all_links = soup.find_all('a', href=True)
                a_tags = [tag for tag in all_links if '/news/' in tag['href'] or '/video/' in tag['href']]
        
        print(f"\n====================================")
        print(f"🟢 DEBUG: 利用 Selector 成功抓到 {len(a_tags)} 個原始連結標籤")
        print(f"====================================\n")
        
        driver.quit() 
        print("🛑 已關閉 Chrome 瀏覽器，開始逐篇解析新聞內容...\n")
        
        results = [] 
        seen_titles = set() 
        processed_urls = set() 

        for idx, tag in enumerate(a_tags, 1):
            url = tag['href']
            if not url:
                print(f"   [{idx}] ❌ 跳過: 連結為空")
                continue
                 
            if 'search' not in url and url not in processed_urls:
                if url.startswith('/'):
                    url = 'https://tw.news.yahoo.com' + url
                
                processed_urls.add(url)
                print(f"\n🔎 [{idx}] 正在處理連結: {url}")

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
                        article_soup = BeautifulSoup(target.html, 'html.parser')
                        time_tag = article_soup.find('time')
                        if time_tag and 'datetime' in time_tag.attrs: 
                            raw_dt = time_tag['datetime'] 
                            dt = datetime.strptime(raw_dt[:19], '%Y-%m-%dT%H:%M:%S')
                            dt_tw = dt + timedelta(hours=8)
                            publish_time = dt_tw.strftime('%Y/%m/%d %H:%M')
                        else:
                            publish_time = time_tag.text.strip() if time_tag else "未知"

                    # 1. 時間過濾檢查
                    if dt_tw:
                        if dt_tw < deadline:
                            print(f"   🔴 [過濾] 逾期新聞: {publish_time}")
                            continue 
                        
                        date_key = dt_tw.strftime('%Y/%m/%d')
                        current_count = daily_counts.get(date_key, 0)

                        if current_count >= daily_limit:
                            print(f"   🟡 [過濾] 當日已達上限 ({daily_limit}篇): {date_key}")
                            continue
                    else:
                        print(f"   🟣 [過濾] 找不到發布時間 (解析失敗)")
                        continue 

                    # 2. 標題檢查
                    raw_title = target.title.strip() 
                    junk_keywords = ["Yahoo股市", "Yahoo奇摩", "專輯", "信箱"] 
                    if any(junk in raw_title for junk in junk_keywords) and len(raw_title) < 15:
                        print(f"   🟤 [過濾] 包含垃圾關鍵字且長度過短: {raw_title}")
                        continue 
                    
                    clean_title = "".join(raw_title.split()) 
                    if len(clean_title) < 10:
                        print(f"   🟤 [過濾] 標題太短 ({len(clean_title)}字): {raw_title}")
                        continue 
                    if clean_title in seen_titles:
                        print(f"   🔵 [過濾] 標題重複: {raw_title}")
                        continue

                    # 3. 內文清洗與過濾 (導入正則深度清洗)
                    article_soup = BeautifulSoup(target.html, 'html.parser')
                    content = ""
                    
                    main_body = article_soup.select_one('div.atoms, div.caas-body, div.article-body, article')
                    
                    if main_body:
                        # 將內文以換行符號拆成陣列
                        raw_lines = main_body.get_text(separator="\n", strip=True).split('\n')
                        
                        # 【步驟一】：防誤殺按鈕與雜訊字過濾
                        # 擴充 Google 變形按鈕與社群分享按鈕
                        spam_buttons = [
                            "Google 偏好來源", "Google偏好來源", "Google 優先推薦來源", 
                            "設為首選來源", "在 Google 上查看",
                            "分享至Facebook", "分享至Line"
                        ]
                        exact_match_buttons = ["分享", "留言", "複製連結"]
                        
                        clean_lines = []
                        for line in raw_lines:
                            line_strip = line.strip()
                            if not line_strip:
                                continue
                                
                            # 處理長字串按鈕 (包含比對)
                            if any(spam in line_strip for spam in spam_buttons):
                                continue
                                
                            # 處理完全比對按鈕
                            if line_strip in exact_match_buttons:
                                continue

                            # 【正則深度清洗】：抹除句內雜訊，避免 TextRank 抓錯
                            # 1. 抹除時間戳記 (例: 2026年5月25日週一 上午1:05)
                            line_cleaned = re.sub(r'\d{4}年\d{1,2}月\d{1,2}日.*?\d{1,2}:\d{2}', '', line_strip)
                            
                            # 2. 抹除開頭署名 (例: 許如鎧｜Yahoo財經特派記者。 或 記者xxx／綜合報導。)
                            line_cleaned = re.sub(r'^.*?｜.*?記者。?', '', line_cleaned)
                            line_cleaned = re.sub(r'^.*?[/／].*?報導。?', '', line_cleaned)
                            
                            # 3. 抹除括號內新聞網 (例: (TVBS新聞網))
                            line_cleaned = re.sub(r'[\(（【].*?新聞網[\)）】]', '', line_cleaned)
                            line_cleaned = re.sub(r'^圖[／/].*?。?', '', line_cleaned) # 清除圖說開頭

                            # 【二次特徵過濾】：若殘留的字串極短且包含特定雜訊，視為整行廢話，捨棄
                            if "新聞網" in line_cleaned and len(line_cleaned) < 15:
                                continue
                            if any(k in line_cleaned for k in ["記者", "綜合報導", "廣告", "即時中心"]) and len(line_cleaned) < 20:
                                continue

                            line_cleaned = line_cleaned.strip()
                            if line_cleaned:
                                clean_lines.append(line_cleaned)
                                
                        # 先將文字用換行符號接合，供後續一刀切使用
                        content = "\n".join(clean_lines)
                    else:
                        print("   ⚠️ [解析失敗] 找不到標準新聞內文區塊 (atoms 或 caas-body)，放棄此篇。")
                        continue

                    if not content or len(content) < 30:
                        print(f"   🟣 [過濾] 抓取到的內文過短或為空。")
                        continue

                    # 【步驟二】：一刀切機制，切除尾端推薦新聞與免責聲明
                    cutoff_pattern = r'延伸閱讀|更多.*?報導|其他人也在看|猜你喜歡|推薦新聞|免責聲明|投資理財有賺有賠'
                    content = re.split(cutoff_pattern, content)[0]

                    # 【步驟三】：將處理完的段落，安全地接合成一整篇文章
                    final_paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
                    content = "。".join(final_paragraphs)
                    content = re.sub(r'。+', '。', content) # 合併多餘句號，讓文字更平順

                    # 檢查句號，並在 debug 訊息中印出內文預覽
                    if "。" not in content:
                        preview = content[:50].replace('\n', ' ') + "..." if len(content) > 50 else content
                        print(f"   🟠 [過濾] 內文無句號，可能非正常文章。內文預覽: [{preview}]")
                        continue

                    # 4. 產生摘要
                    print(f"   📝 原始內文長度: {len(content)} 字 -> 開始進行 TextRank 摘要...")
                    # 🟢 [修改] 將 raw_title 當作參數傳給 TextRank 進行過濾
                    news_summary = textrank_summary(content, title=raw_title, top_k=2)

                    news_dict = {
                        "title": raw_title,
                        "time": publish_time,
                        "text": news_summary,
                        "link": url
                    }

                    seen_titles.add(clean_title) 
                    results.append(news_dict) 
                    daily_counts[date_key] = current_count + 1
                    print(f"   ✅ 成功加入。目前 {date_key} 已累積: {daily_counts[date_key]} 篇")

                    if len(results) >= daily_limit * 3:
                        print(f"\n🚨 已達到總體抓取限制數量 ({daily_limit * 3} 篇)，中斷爬取。")
                        break
                    
                    # 隨機冷卻：2~4 秒
                    sleep_time = random.uniform(2, 4)
                    time.sleep(sleep_time) 

                except Exception as article_error:
                    print(f"   🔺 [單篇錯誤] 解析此新聞失敗: {article_error}")
                    continue 
            else:
                if 'search' in url:
                    print(f"   [{idx}] ❌ 跳過: 屬於搜尋頁面連結而非新聞頁面")
                elif url in processed_urls:
                    print(f"   [{idx}] ❌ 跳過: 此 URL 已處理過")

        print("\n" + "=" * 60)
        print(f"📊 最終抓取統計: {daily_counts}")
        print("=" * 60 + "\n")
        
        for i, news in enumerate(results, 1): 
            print(f"({i}) [ 標題 ]: {news['title']}")
            print(f"    [ 連結 ]: {news['link']}")
            print(f"    [ 時間 ]: {news['time']}")
            print(f"    [ 內文 ]: {news['text']}")
            print("-" * 60)
        return results
        
    except Exception as e:
        print(f"\n💥 [嚴重連線失敗]: {e}")
        if 'driver' in locals():
            driver.quit()
        return []
    
if __name__ == "__main__":
    stock = input("請輸入搜尋代碼: ")
    scrap_yahoo(symbol=stock, daily_limit=30)