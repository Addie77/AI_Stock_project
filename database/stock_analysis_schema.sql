CREATE DATABASE IF NOT EXISTS `stock_analysis` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `stock_analysis`;

-- 1. 股票基本資料表 (stock)
DROP TABLE IF EXISTS `favorite_stocks`;
DROP TABLE IF EXISTS `daily_quote`;
DROP TABLE IF EXISTS `ml_prediction`;
DROP TABLE IF EXISTS `news_sentiment`;
DROP TABLE IF EXISTS `stock_analysis_report`;
DROP TABLE IF EXISTS `stock`;

CREATE TABLE `stock` (
  `stock_id` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  `stock_name` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `industry` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `update_time` datetime NOT NULL,
  PRIMARY KEY (`stock_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. 每日行情與技術指標表 (daily_quote)
CREATE TABLE `daily_quote` (
  `quote_id` bigint NOT NULL AUTO_INCREMENT,
  `stock_id` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  `trade_date` date NOT NULL,
  `close_price` decimal(10,2) DEFAULT NULL,
  `volume` bigint DEFAULT NULL,
  `ma_5` decimal(10,2) DEFAULT NULL,
  `ma_20` decimal(10,2) DEFAULT NULL,
  PRIMARY KEY (`quote_id`),
  KEY `stock_id` (`stock_id`),
  CONSTRAINT `daily_quote_ibfk_1` FOREIGN KEY (`stock_id`) REFERENCES `stock` (`stock_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. 新聞輿情與情緒分數表 (news_sentiment)
CREATE TABLE `news_sentiment` (
  `news_id` bigint NOT NULL AUTO_INCREMENT,
  `stock_id` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  `publish_date` datetime NOT NULL,
  `title` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `content_url` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sentiment_score` int DEFAULT NULL,
  `content_summary` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`news_id`),
  KEY `stock_id` (`stock_id`),
  CONSTRAINT `news_sentiment_ibfk_1` FOREIGN KEY (`stock_id`) REFERENCES `stock` (`stock_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. 機器學習預測表 (ml_prediction)
CREATE TABLE `ml_prediction` (
  `predict_id` bigint NOT NULL AUTO_INCREMENT,
  `stock_id` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  `target_date` date NOT NULL,
  `up_probability` decimal(5,2) DEFAULT NULL,
  `trade_signal` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_sentiment_fused` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`predict_id`),
  KEY `stock_id` (`stock_id`),
  CONSTRAINT `ml_prediction_ibfk_1` FOREIGN KEY (`stock_id`) REFERENCES `stock` (`stock_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. AI 分析報告表 (stock_analysis_report)
CREATE TABLE `stock_analysis_report` (
  `report_id` bigint NOT NULL AUTO_INCREMENT,
  `stock_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `analysis_date` date NOT NULL,
  `avg_sentiment` double DEFAULT NULL,
  `overall_summary` text COLLATE utf8mb4_unicode_ci,
  `report_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'TEMPLATE' COMMENT '報告類型：TEMPLATE(預設模板) / DEEP_AI(Gemini深度分析)',
  PRIMARY KEY (`report_id`),
  KEY `stock_id` (`stock_id`),
  CONSTRAINT `stock_analysis_report_ibfk_1` FOREIGN KEY (`stock_id`) REFERENCES `stock` (`stock_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. 使用者自選股與持股管理表 (favorite_stocks)
CREATE TABLE `favorite_stocks` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `stock_id` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `added_at` datetime NOT NULL,
  `memo` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `target_price` double DEFAULT NULL,
  `average_cost` decimal(10,2) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `stock_id` (`stock_id`),
  CONSTRAINT `favorite_stocks_ibfk_1` FOREIGN KEY (`stock_id`) REFERENCES `stock` (`stock_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
