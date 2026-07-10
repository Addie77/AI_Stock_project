import os
import json
import requests
import time
import random
from datetime import datetime, timedelta  # 🟢 新增：用來計算日期的模組
from selenium import webdriver

def get_token_via_selenium():
    """步驟 1：啟動瀏覽器讓你登入，並自動擷取最新 Token (自動 Base64 解碼版)"""
    print("🌐 啟動瀏覽器以獲取登入權限...")
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    driver.get("https://www.alphamemo.ai/free-transcripts")
    
    print("\n" + "=" * 60)
    print("🔑 請在 30 秒內於 Chrome 視窗中點擊右上角並完成登入！")
    print("   (登入成功後放著即可，程式會自動擷取金鑰並關閉瀏覽器)")
    print("=" * 60 + "\n")
    
    for sec in range(30, 0, -5):
        print(f"⏳ 剩餘登入時間：{sec} 秒...")
        time.sleep(5)
        
    print("\n🚀 時間到！保險起見重新整理頁面確保狀態更新...")
    driver.refresh()
    time.sleep(3)
    
    print("🚀 正在從瀏覽器擷取驗證權杖...")
    
    js_script = """
    return (() => {
        try {
            for (let i = 0; i < localStorage.length; i++) {
                let key = localStorage.key(i);
                if (key && key.includes('-auth-token')) {
                    let data = JSON.parse(localStorage.getItem(key));
                    if (data && data.access_token) return data.access_token;
                }
            }
        } catch(e) {}
        
        try {
            const getC = (name) => document.cookie.split('; ').find(r => r.startsWith(name + '='))?.split('=')[1] || '';
            let full_b64 = '';
            for (let i = 0; i < 5; i++) {
                let chunk = getC('sb-api-auth-token.' + i);
                if (chunk) full_b64 += decodeURIComponent(chunk).replace(/^base64-/, '');
            }
            if (full_b64) {
                let sessionStr = decodeURIComponent(escape(atob(full_b64)));
                let sessionObj = JSON.parse(sessionStr);
                if (sessionObj && sessionObj.access_token) return sessionObj.access_token;
            }
        } catch(e) {}
        return null;
    })();
    """
    token = driver.execute_script(js_script)
    driver.quit() 
    
    if token:
        print(f"✅ 成功擷取登入權杖！(檢查碼: {token[:15]}...)")
        if token.startswith("eyJhbG"):
            print("🎉 檢查碼完全正確！準備進入極速抓取模式...\n")
        return f"Bearer {token}"
    else:
        print("❌ 擷取失敗，可能是登入未完成，或網站儲存機制已改變。")
        return None

def get_transcripts_list(query, headers):
    """步驟 2：透過 API 取得搜尋列表 (🟢 已加入近一個月篩選條件)"""
    
    # 🟢 計算 30 天前的日期 (格式：YYYY-MM-DD)
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    print(f"📅 篩選條件：只抓取 {thirty_days_ago} 之後的法說會...")

    url = "https://api.alphamemo.ai/rest/v1/free_transcripts"
    params = {
        'select': 'id,stock_name,stock_number,audio_date',
        'is_accessed': 'eq.true',
        'or': f'(stock_name.ilike.%{query}%,stock_number.ilike.%{query}%)',
        'audio_date': f'gte.{thirty_days_ago}',  # 🟢 關鍵：要求後端只回傳大於等於該日期的資料
        'order': 'audio_date.desc',
        'limit': '10'
    }
    res = requests.get(url, params=params, headers=headers)
    if res.status_code == 200:
        return res.json()
    else:
        print(f"❌ 搜尋列表 API 失敗，狀態碼：{res.status_code}")
        return []

def get_transcript_detail(transcript_id, headers):
    """步驟 3：透過 API 獲取內文與 Memo"""
    url = "https://api.alphamemo.ai/functions/v1/get_transcript"
    payload = {'transcriptId': transcript_id}
    
    post_headers = headers.copy()
    post_headers['content-type'] = 'application/json'
    
    try:
        res = requests.post(url, json=payload, headers=post_headers)
        if res.status_code == 200:
            data = res.json()
            if 'content' in data and isinstance(data['content'], str):
                try:
                    data['content_parsed'] = json.loads(data['content'])
                except:
                    data['content_parsed'] = {}
            elif 'content' in data and isinstance(data['content'], dict):
                data['content_parsed'] = data['content']
            return data
        else:
            print(f"❌ 抓取失敗 (ID: {transcript_id})，狀態碼：{res.status_code}")
            return None
    except Exception as e:
        print(f"❌ 發生例外異常：{e}")
        return None

def save_memo_only(data, filepath):
    """步驟 4：安全解析資料並寫入結構化 JSON 檔案"""
    content = data.get('content_parsed', {})
    memo_list = content.get('memo', [])
    
    if not memo_list:
        print(f"⚠️ 該場法說會尚未產生 Memo 摘要，跳過儲存。")
        return False

    meta = data.get('metadata', {})
    
    json_output = {
        "stock_name": meta.get('stock_name'),
        "stock_number": meta.get('stock_number'),
        "audio_date": meta.get('audio_date'),
        "memos": []
    }

    for topic in memo_list:
        heading = topic.get('zh_heading') or topic.get('heading', '未分類')
        topic_data = {
            "heading": heading,
            "items": []
        }
        for item in topic.get('items', []):
            zh_text = item.get('translate', {}).get('zh', '')
            en_text = item.get('text', '')
            if zh_text or en_text:
                topic_data["items"].append({
                    "zh": zh_text,
                    "en": en_text
                })
        json_output["memos"].append(topic_data)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(json_output, f, ensure_ascii=False, indent=4)
        
    return True


# === 主程式執行 ===
if __name__ == '__main__':
    query = input("請輸入股票代號 (例如 2330)：").strip()
    if not query:
        exit()

    bearer_token = get_token_via_selenium()
    if not bearer_token:
        exit()

    headers = {
        'accept': '*/*',
        'apikey': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVmbGR6dGNjY3Robm5qYmViYmFoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDE5NTIwNTMsImV4cCI6MjA1NzUyODA1M30.XJDInKWn10xUag0bl0Cu3ZwQ2nQ61ZAL_ClajR22t_I',
        'authorization': bearer_token,
        'origin': 'https://www.alphamemo.ai',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    transcripts = get_transcripts_list(query, headers)
    
    # 🟢 當抓不到近一個月的資料時，直接給予清楚的提示並結束程式
    if not transcripts:
        print(f"\n⚠️ 提示：未搜尋到【{query}】近一個月內的法說會紀錄。")
        exit()

    output_dir = "memos_output"
    os.makedirs(output_dir, exist_ok=True)

    for idx, item in enumerate(transcripts):
        t_id = item['id']
        title = f"{item['stock_name']}_{item['stock_number']}_{item['audio_date']}_Memo"
        print(f"[{idx+1}/{len(transcripts)}] 正在透過 API 下載：{title} ...")
        
        detail_data = get_transcript_detail(t_id, headers)
        if detail_data:
            out_file = f"{output_dir}/{title}.json"
            if save_memo_only(detail_data, out_file):
                print(f"✅ 已成功儲存至 {out_file}")

        if idx < len(transcripts) - 1:
            delay = random.uniform(3.0, 5.0)
            print(f"⏳ 防封鎖保護：等待 {delay:.2f} 秒再發送下一次請求...\n")
            time.sleep(delay)

    print("\n🎉 所有符合條件的 JSON 摘要已經下載完畢！")