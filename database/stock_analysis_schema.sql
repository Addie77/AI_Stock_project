CREATE DATABASE stock_analysis CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE stock_analysis;

CREATE TABLE stock (
    stock_id VARCHAR(10) PRIMARY KEY,
    stock_name VARCHAR(50) NOT NULL,
    industry VARCHAR(50),
    update_time DATETIME NOT NULL
);

CREATE TABLE daily_quote (
    quote_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_id VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    close_price DECIMAL(10 , 2 ),
    volume BIGINT,
    ma_5 DECIMAL(10 , 2 ),
    ma_20 DECIMAL(10 , 2 ),
    FOREIGN KEY (stock_id)
        REFERENCES stock (stock_id)
);

CREATE TABLE news_sentiment (
    news_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_id VARCHAR(10) NOT NULL,
    publish_date DATETIME NOT NULL,
    title VARCHAR(255) NOT NULL,
    content_url VARCHAR(500),
    sentiment_score INT,
    ai_summary TEXT,
    FOREIGN KEY (stock_id)
        REFERENCES stock (stock_id)
);

CREATE TABLE ml_prediction (
    predict_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_id VARCHAR(10) NOT NULL,
    target_date DATE NOT NULL,
    up_probability DECIMAL(5 , 2 ),
    trade_signal VARCHAR(10),
    FOREIGN KEY (stock_id)
        REFERENCES stock (stock_id)
);

