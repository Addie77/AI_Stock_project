import os
import sys

# =====================================================================
# 🟢 跨資料夾路徑設定：讓 Python 自動去隔壁的 sentiment_model 資料夾找模組
# =====================================================================
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sentiment_model_path = os.path.join(parent_dir, "sentiment_model")

if sentiment_model_path not in sys.path:
    sys.path.append(sentiment_model_path)

# =====================================================================
# 下方為標準套件與自訂情緒分析模組的引入
# =====================================================================
import json
import glob
from sentiment_analyzer import SentimentAnalyzer  # 這樣就絕對找得到了！

def process_memos_with_sentiment(input_json_path, analyzer):
    """
    讀取原始法說會 JSON，保留 heading、調和內容（zh為空則抓en），並對每一個 item 進行情緒評分。
    """
    if not os.path.exists(input_json_path):
        print(f"❌ 找不到檔案：{input_json_path}")
        return None

    # 1. 讀取 JSON 資料
    with open(input_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 2. 建立新結構，準備存放含有情緒分數的資料
    analyzed_output = {
        "stock_name": data.get("stock_name"),
        "stock_number": data.get("stock_number"),
        "audio_date": data.get("audio_date"),
        "memos": []
    }
    
    # 3. 遍歷每一個主題區塊 (Heading)
    for memo in data.get("memos", []):
        heading = memo.get("zh_heading") or memo.get("heading", "未分類")
        
        items_with_scores = []
        for item in memo.get("items", []):
            zh_text = item.get("zh", "").strip()
            en_text = item.get("en", "").strip()
            
            # 欄位調和邏輯：優先拿 zh，如果 zh 為空則拿 en (解決如 3008 等 en 欄位塞中文的問題)
            target_text = zh_text if zh_text else en_text
            
            if target_text:
                cleaned_text = target_text.lstrip("• ").strip()
                if cleaned_text:
                    # 🟢 呼叫 FinBERT 模型為這句話評分
                    score_result = analyzer.analyze_text(cleaned_text)
                    
                    # 將文字與評分結果打包在一起
                    items_with_scores.append({
                        "text": cleaned_text,
                        "sentiment": score_result
                    })
                    
        # 如果這個 heading 裡面有成功評分的內容，才加入輸出結果
        if items_with_scores:
            analyzed_output["memos"].append({
                "heading": heading,
                "items": items_with_scores
            })
            
    return analyzed_output



# === 動態執行與驗證區塊 ===
if __name__ == "__main__":
    output_dir = "memos_output"
    
    # 讓使用者動態輸入想要處理的股票代號
    query = input("請輸入想要進行情緒分析的股票代號 (例如 3008)：").strip()
    
    if query:
        # 動態搜尋 memos_output 資料夾內該股票的原始 Memo 檔案 (排除已處理過的檔案)
        search_pattern = os.path.join(output_dir, f"*_{query}_*_Memo.json")
        matching_files = glob.glob(search_pattern)
        
        if not matching_files:
            print(f"❌ 在 {output_dir} 資料夾中找不到該股票代號的原始 JSON 檔。")
            print("💡 請確認是否已經先執行過爬蟲下載資料。")
        else:
            print("\n⏳ 正在初始化 FinBERT 中文金融情緒模型 (這可能需要幾秒鐘)...")
            # 🟢 初始化分析器物件 (在迴圈外初始化，避免重複載入模型消耗記憶體)
            analyzer = SentimentAnalyzer()
            
            print(f"🔍 找到 {len(matching_files)} 筆原始檔案，開始進行主題細項情緒評分...\n")
            
            for json_file in matching_files:
                base_name = os.path.basename(json_file).replace("_Memo.json", "")
                print(f"🚀 正在分析並評分：{base_name} ...")
                
                # 傳入檔案路徑與 analyzer 物件
                result = process_memos_with_sentiment(json_file, analyzer)
                
                if result:
                    # 動態產生帶有情緒分數的輸出檔名 (例如: 大立光_3008_2026-07-09_sentiment_analyzed.json)
                    out_path = os.path.join(output_dir, f"{base_name}_sentiment_analyzed.json")
                    
                    with open(out_path, "w", encoding="utf-8") as f:
                        json.dump(result, f, ensure_ascii=False, indent=4)
                        
                    print(f"✅ 分析完成！已成功儲存至：{out_path}")
                    print("-" * 50)
                    
            print("\n🎉 所有指定股票的法說會主題細項評分已全數處理完畢！")