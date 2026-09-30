erDiagram
    %% 第一層到第二層：主表連向基礎數據與自選清單
    stock ||--o{ daily_quote : "歷史行情"
    stock ||--o{ news_sentiment : "新聞輿情"
    stock ||--o{ favorite_stocks : "自選清單"

    %% 第二層到第三層：基礎數據向下延伸至分析與預測
    daily_quote ||--o{ ml_prediction : "特徵預測"
    news_sentiment ||--o{ stock_analysis_report : "彙整分析"

    stock {
        VARCHAR(10) stock_id PK "股票代碼"
        VARCHAR(50) stock_name "股票名稱"
        VARCHAR(50) industry "所屬產業"
        DATETIME update_time "最後更新時間"
    }

    daily_quote {
        BIGINT quote_id PK "流水號"
        VARCHAR(10) stock_id FK "股票代碼"
        DATE trade_date "交易日期"
        DECIMAL close_price "收盤價"
        BIGINT volume "成交量"
        DECIMAL ma_5 "5日均線"
        DECIMAL ma_20 "20日均線"
    }

    news_sentiment {
        BIGINT news_id PK "流水號"
        VARCHAR(10) stock_id FK "股票代碼"
        DATETIME publish_date "發布時間"
        VARCHAR(255) title "新聞標題"
        VARCHAR(500) content_url "新聞連結"
        INT sentiment_score "情緒分數 (-100~100)"
        TEXT content_summary "內容摘要"
    }

    ml_prediction {
        BIGINT predict_id PK "流水號"
        VARCHAR(10) stock_id FK "股票代碼"
        DATE target_date "預測目標日期"
        DECIMAL up_probability "次日上漲機率 (%)"
        VARCHAR(20) trade_signal "交易訊號"
        TINYINT is_sentiment_fused "是否融合情緒特徵 (0/1)"
    }

    stock_analysis_report {
        BIGINT report_id PK "流水號"
        VARCHAR(20) stock_id FK "股票代碼"
        DATE analysis_date "分析日期"
        DOUBLE avg_sentiment "當天平均情緒分數"
        TEXT overall_summary "AI分析評估長文"
        VARCHAR(20) report_type "報告類型 (TEMPLATE/DEEP_AI)"
    }

    favorite_stocks {
        BIGINT id PK "流水號"
        VARCHAR(255) stock_id FK "股票代碼"
        DATETIME added_at "加入時間"
        VARCHAR(255) memo "備忘筆記"
        DOUBLE target_price "目標價"
        DECIMAL average_cost "個人持有平均成本"
    }
