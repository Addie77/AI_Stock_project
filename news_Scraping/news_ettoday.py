import requests
from bs4 import BeautifulSoup
from newspaper import Article, Config
import time
import random

def scrap_ettoday(limit=5):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'}
    config = Config()
    config.browser_user_agent = headers['User-Agent']
    config.fetch_images = False
    config.memoize_articles = False    

    target_url = 'https://finance.ettoday.net/focus/104'
    
    try:
        response = requests.get(target_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        all_a_tags = soup.find_all('a', href=True)

        results = []
        seen_titles = set()
        processed_urls = set()

        for a in all_a_tags:
            url = a['href']
            
            if url.startswith('//'):
                url = 'https:' + url
            elif url.startswith('/'):
                url = 'https://finance.ettoday.net' + url
            
            if 'finance.ettoday.net/news/' in url and len(url) > 35 and url not in processed_urls:
                processed_urls.add(url)
                
                try:
                    target = Article(url, config=config, language='zh')
                    target.download()
                    target.parse()

                    artitle_soup = BeautifulSoup(target.html,'html.parser')
                    time_tag = artitle_soup.find('time', class_='date')

                    if time_tag:
                        raw_time_text = time_tag.text.strip()
                        publish_time = raw_time_text.replace('年','/').replace('月','/').replace('日','')
                    elif target.publish_date:
                        publish_time = target.publish_date.strftime('%Y/%m/%d %H:%M')
                    else:
                        publish_time = "未知"

                    raw_title = target.title.strip()
                    clean_title = "".join(raw_title.split())
                    
                    if len(clean_title) < 10 or clean_title in seen_titles:
                        continue

                    content = target.text.strip()
                    if "，" not in content or len(content) < 100:
                        continue

                    news_dict = {
                        "title": raw_title,
                        "source": "ETtoday 財經雲",
                        "time": publish_time,
                        "full_text": content,
                        "link": url
                    }

                    seen_titles.add(clean_title)
                    results.append(news_dict)

                    if len(results) >= limit:
                        break
                    time.sleep(random.uniform(1, 4))
                
                except:
                    continue

        print("\n" + "=" * 60)
        for i, news in enumerate(results, 1):
            print(f"({i}) [標題]: {news['title']}")
            print(f"    [來源]: {news['source']}")
            print(f"    [時間]: {news['time']}")
            preview = news['full_text'][:100].replace('\n', ' ')
            print(f"    [內容]: {preview}...")
            print("-" * 60)

        return results
    
    except Exception as e:
        print(f"連線失敗: {e}")
        return []

if __name__ == "__main__":
    scrap_ettoday(limit=5)