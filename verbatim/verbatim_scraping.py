import os
import sys
import json
import requests
import time
import random
from datetime import datetime, timedelta
from selenium import webdriver

# =====================================================================
# 🟢 跨資料夾路徑設定
# =====================================================================
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sentiment_model_path = os.path.join(parent_dir, "sentiment_model")

if sentiment_model_path not in sys.path:
    sys.path.append(sentiment_model_path)


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
    #透過 driver.execute_script() 將一段匿名 JS 函式注入網頁前端執行
    #前半段：掃描前端 localStorage，尋找帶有 -auth-token 的金鑰，如果找到就提取裡面的 access_token
    #後半段：如果 localStorage 沒有，就去掃描網頁 Cookie，把被拆分成 5 個碎片的 Base64 字串拼湊回來，進行解碼還原成 JSON 並取出 Token。
    token = driver.execute_script(js_script)
    driver.quit() 
    
    #驗證 Token 是否成功抓到。
    #如果是以 eyJhbG（JWT 標準開頭）啟始，代表權杖完全合法，並加上網頁 Header 標準的 "Bearer " 格式後回傳；
    #失敗則回傳 None。
    if token:
        print(f"✅ 成功擷取登入權杖！(檢查碼: {token[:15]}...)")
        if token.startswith("eyJhbG"):
            print("🎉 檢查碼完全正確！準備進入極速抓取模式...\n")
        return f"Bearer {token}"
    else:
        print("❌ 擷取失敗，可能是登入未完成，或網站儲存機制已改變。")
        return None


def get_transcripts_list(query, headers):
    """步驟 2：透過 API 取得搜尋列表 (限制近一個月內)"""
    #利用 datetime 計算出「今天往回推 30 天」的日期字串
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    print(f"📅 篩選條件：只抓取 {thirty_days_ago} 之後的法說會...")

    url = "https://api.alphamemo.ai/rest/v1/free_transcripts"
    params = {
        'select': 'id,stock_name,stock_number,audio_date',
        'is_accessed': 'eq.true',
        'or': f'(stock_name.ilike.%{query}%,stock_number.ilike.%{query}%)',
        'audio_date': f'gte.{thirty_days_ago}',
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

# 用來存成json檔方便看內容
# def process_and_save_data(data, output_dir, base_title):
#     """
#     步驟 4：在記憶體中清洗資料，並將保有 Heading 分類的原始樹狀摘要儲存成本地 JSON。
#     🟢 [除錯優化] 重新啟用儲存功能，提供格式漂亮、方便除錯的本地備份。
#     """
#     content = data.get('content_parsed', {})
#     memo_list = content.get('memo', [])
    
#     if not memo_list:
#         print(f"⚠️ 該場法說會尚未產生 Memo 摘要，跳過處理。")
#         return False

#     meta = data.get('metadata', {})
    
#     # 這是你的除錯用容器，用來維持完整的「法說會主題樹狀架構」
#     raw_output = {
#         "stock_name": meta.get('stock_name'),
#         "stock_number": meta.get('stock_number'),
#         "audio_date": meta.get('audio_date'),
#         "memos": []
#     }

#     for topic in memo_list:
#         heading = topic.get('zh_heading') or topic.get('heading', '未分類')
#         raw_topic_data = {"heading": heading, "items": []}
        
#         for item in topic.get('items', []):
#             zh_text = item.get('translate', {}).get('zh', '').strip()
#             en_text = item.get('text', '').strip()
            
#             if zh_text or en_text:
#                 raw_topic_data["items"].append({
#                     "zh": zh_text,
#                     "en": en_text
#                 })
                    
#         if raw_topic_data["items"]:
#             raw_output["memos"].append(raw_topic_data)
            
#     # 🟢 真正將檔案寫入本地硬碟，供你隨時檢視除錯
#     memo_path = f"{output_dir}/{base_title}_Memo.json"
#     with open(memo_path, 'w', encoding='utf-8') as f:
#         json.dump(raw_output, f, ensure_ascii=False, indent=4)
#     print(f"   💾 本地除錯備份 -> 原始摘要已儲存至：{memo_path}")
    
#     return True


def verbatim_scraping(query):
    """
    彙整主執行函式
    🟢 核心邏輯：本地儲存樹狀結構以利除錯，同時回傳扁平化對齊新聞格式的資料流。
    """
    query = query.strip()
    if not query:
        print("⚠️ 錯誤：請輸入有效的股票代號或名稱。")
        return []

    bearer_token = get_token_via_selenium()
    if not bearer_token:
        print("❌ 無法取得 Token，結束執行。")
        return []

    headers = {
        'accept': '*/*',
        'apikey': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVmbGR6dGNjY3Robm5qYmViYmFoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDE5NTIwNTMsImV4cCI6MjA1NzUyODA1M30.XJDInKWn10xUag0bl0Cu3ZwQ2nQ61ZAL_ClajR22t_I',
        'authorization': bearer_token,
        'origin': 'https://www.alphamemo.ai',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    transcripts = get_transcripts_list(query, headers)
    
    if not transcripts:
        print(f"\n⚠️ 提示：未搜尋到【{query}】近一個月內的法說會紀錄。")
        return []

    #配合process_and_save_data
    # # 確保儲存除錯檔案的資料夾存在
    # output_dir = "memos_output"
    # os.makedirs(output_dir, exist_ok=True)

    # 用來搜集轉換為「新聞格式 4 欄位」的法說會資料容器
    verbatim_news_results = []

    for idx, item in enumerate(transcripts):
        t_id = item['id']
        stock_name = item.get('stock_name', '未知個股')
        stock_num = item.get('stock_number', query)
        audio_date = item.get('audio_date', '未知日期')
        
        base_title = f"{stock_name}_{stock_num}_{audio_date}"
        print(f"\n🚀 [{idx+1}/{len(transcripts)}] 正在處理：{base_title} ...")
        
        detail_data = get_transcript_detail(t_id, headers)
        if detail_data:
            #配合process_and_save_data
            # # 🟢 執行記憶體清洗，並寫入本地端 `_Memo.json` 檔案
            # process_and_save_data(detail_data, output_dir, base_title)
            
            # 欄位完美對齊加工：將這場法說會的所有項目打平，包裝成符合新聞的 4 欄位結構
            content = detail_data.get('content_parsed', {})
            for topic in content.get('memo', []):
                heading = topic.get('zh_heading') or topic.get('heading', '未分類')
                for sub_item in topic.get('items', []):
                    zh_text = sub_item.get('translate', {}).get('zh', '').strip()
                    en_text = sub_item.get('text', '').strip()
                    
                    # 欄位調和
                    target_text = zh_text if zh_text else en_text
                    if target_text:
                        cleaned_text = target_text.lstrip("• ").strip()
                        if cleaned_text:
                            # ☯️ 完美對齊新聞的 4 個核心欄位
                            verbatim_news_results.append({
                                "title": f"【法說會摘要-{stock_name}_{heading}】",
                                "text": cleaned_text,
                                "time": audio_date.replace("-", "/"),  # 對齊 Yahoo 的 YYYY/MM/DD 格式
                                "link": "https://www.alphamemo.ai/free-transcripts"
                            })
            print(f"   ✅ 已成功將該場次的細項扁平化對齊，目前整合容器內共 {len(verbatim_news_results)} 條。")
            print("-" * 50)

        if idx < len(transcripts) - 1:
            delay = random.uniform(3.0, 5.0)
            print(f"⏳ 防封鎖保護：等待 {delay:.2f} 秒...")
            time.sleep(delay)

    print("\n🎉 所有法說會紀錄已全數處理完畢並轉換完成！")
    return verbatim_news_results


# === 實際手動執行進入點 ===
if __name__ == '__main__':
    user_input = input("請輸入股票代號 (例如 3008)：")
    results = verbatim_scraping(user_input)
    print(f"\n🔍 手動測試回傳結果筆數：{len(results)} 筆")