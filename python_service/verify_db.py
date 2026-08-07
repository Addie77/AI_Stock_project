import pymysql
from ml_inference import DB_CONFIG

if __name__ == "__main__":
    print("🔍 正在連線資料庫並查詢法說會資料寫入狀態...")
    try:
        conn = pymysql.connect(**DB_CONFIG)  # type: ignore
        cursor = conn.cursor()
        
        # 1. 統計帶有「法说会摘要」字樣的總數量
        query_count = "SELECT COUNT(*) FROM news_sentiment WHERE title LIKE '%法说会摘要%'"
        cursor.execute(query_count)
        row = cursor.fetchone()
        total_count = row[0] if row else 0
        print(f"📊 資料庫中帶有『法说会摘要』的總筆數：{total_count} 筆")
        
        # 2. 列出前 10 筆作為驗證證據
        query_rows = "SELECT news_id, title, content_url, sentiment_score FROM news_sentiment WHERE title LIKE '%法说会摘要%' ORDER BY news_id DESC LIMIT 10"
        cursor.execute(query_rows)
        rows = cursor.fetchall()
        
        if rows:
            print("\n📋 最新寫入的 10 筆法說會資料明細：")
            print(f"{'news_id':<8} | {'title':<30} | {'sentiment_score':<5} | {'content_url'}")
            print("-" * 100)
            for row in rows:
                news_id, title, url, score = row
                print(f"{news_id:<8} | {title:<30} | {score:<15} | {url}")
        else:
            print("⚠️ 未查到任何符合法說會摘要字樣的資料。")
            
        conn.close()
    except Exception as e:
        print(f"❌ 查詢失敗: {e}")
