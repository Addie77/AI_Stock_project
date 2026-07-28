import os
import sys
import json
import base64
import requests
import time
import random
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver as Chrome
from selenium.webdriver.chrome.options import Options as ChromeOptions


# 🟢 解決 Windows 下印出 Emoji 可能產生的 UnicodeEncodeError
try:
    reconfig = getattr(sys.stdout, 'reconfigure', None)
    if reconfig:
        reconfig(errors='replace')
except Exception:
    pass

# =====================================================================
# 🟢 跨資料夾路徑設定
# =====================================================================
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sentiment_model_path = os.path.join(parent_dir, "sentiment_model")

if sentiment_model_path not in sys.path:
    sys.path.append(sentiment_model_path)


SESSION_FILE = os.path.join(current_dir, "verbatim_session.json")

def is_jwt_token_valid(token_str):
    """驗證 JWT Token 是否仍在有效期限內 (預留 5 分鐘緩衝)"""
    if not token_str:
        return False
    try:
        # 移除 Bearer 前綴
        raw_token = token_str.replace("Bearer ", "").strip()
        parts = raw_token.split('.')
        if len(parts) != 3:
            return False
        
        payload_b64 = parts[1]
        # 補足 Base64 填充字元 =
        payload_b64 += '=' * (-len(payload_b64) % 4)
        payload_json = base64.b64decode(payload_b64).decode('utf-8')
        payload = json.loads(payload_json)
        
        exp = payload.get('exp')
        if exp:
            # 預留 300 秒 (5 分鐘) 的緩衝期，避免即將過期的 Token 導致請求失敗
            return time.time() < (exp - 300)
    except Exception as e:
        print(f"⚠️ 解析 Token 效期時發生異常: {e}")
    return False


def get_valid_token():
    """取得有效的 Token。若快取有效則直接使用，否則啟動瀏覽器取得並更新快取"""
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                cached_token = data.get("access_token")
                if is_jwt_token_valid(cached_token):
                    print("✅ 偵測到有效的本地快取權杖，直接載入！(無須啟動瀏覽器)")
                    return cached_token
                else:
                    print("⏳ 本地快取權杖已過期或無效，準備重新獲取...")
        except Exception as e:
            print(f"⚠️ 讀取快取權杖檔案失敗: {e}")

    # 執行 Selenium 取得新 Token
    token = get_token_via_selenium()
    if token:
        try:
            with open(SESSION_FILE, 'w', encoding='utf-8') as f:
                json.dump({"access_token": token}, f, ensure_ascii=False, indent=4)
            print("💾 新權杖已成功快取至本地檔案。")
        except Exception as e:
            print(f"⚠️ 儲存快取權杖檔案失敗: {e}")
    return token


def get_token_via_selenium():
    """步驟 1：啟動瀏覽器讓你登入，並自動擷取最新 Token (自動 Base64 解碼與持久化 Profile 版)"""
    print("🌐 啟動瀏覽器以獲取登入權限...")
    options = ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # 🟢 優化：使用持久性 Chrome Profile，保持 Google 登入狀態與網站 Session
    # 解決 Windows 下若路徑含非 ASCII 字元 (例如「桌面」) 導致 Chrome 啟動崩潰的問題
    profile_path = os.path.join(current_dir, "chrome_profile")
    try:
        profile_path.encode('ascii')
    except UnicodeEncodeError:
        user_home = os.environ.get('USERPROFILE') or os.path.expanduser('~')
        profile_path = os.path.join(user_home, ".verbatim_chrome_profile")
        
    print(f"📂 使用的 Chrome 設定檔路徑: {profile_path}")
    options.add_argument(f'--user-data-dir={profile_path}')
    
    driver = Chrome(options=options)
    driver.get("https://www.alphamemo.ai/free-transcripts")
    
    print("\n" + "=" * 60)
    print("🔑 正在偵測登入狀態...")
    print("   * 若您先前已登入，程式將在數秒內自動感應並擷取 Token，自動關閉瀏覽器。")
    print("   * 若尚未登入或 Session 已過期，請在瀏覽器視窗中手動完成登入！")
    print("=" * 60 + "\n")
    
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
    
    token = None
    max_wait_sec = 45
    for sec in range(1, max_wait_sec + 1):
        try:
            token = driver.execute_script(js_script)
        except Exception:
            # 避免網頁載入中或關閉時執行 JS 報錯
            pass
            
        if token:
            print(f"✨ 已成功感應到登入權杖！(偵測耗時: {sec} 秒)")
            break
            
        # 在第 8 秒時，若有持續 Profile 但仍未抓到 Token，自動重新整理一次確保 Supabase Session 刷新
        if sec == 8:
            print("🔄 自動重新整理頁面以觸發 Session 刷新...")
            try:
                driver.refresh()
            except:
                pass
                
        if sec % 5 == 0:
            print(f"⏳ 偵測中，已等待 {sec} 秒 (最長等待 {max_wait_sec} 秒)...")
            
        time.sleep(1)
        
    driver.quit() 
    
    # 驗證 Token 是否成功抓到。
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

    bearer_token = get_valid_token()
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