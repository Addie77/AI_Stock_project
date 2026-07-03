CREATE DATABASE  IF NOT EXISTS `stock_analysis` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `stock_analysis`;


DROP TABLE IF EXISTS `daily_quote`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
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


DROP TABLE IF EXISTS `ml_prediction`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ml_prediction` (
  `predict_id` bigint NOT NULL AUTO_INCREMENT,
  `stock_id` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  `target_date` date NOT NULL,
  `up_probability` decimal(5,2) DEFAULT NULL,
  `trade_signal` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`predict_id`),
  KEY `stock_id` (`stock_id`),
  CONSTRAINT `ml_prediction_ibfk_1` FOREIGN KEY (`stock_id`) REFERENCES `stock` (`stock_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


DROP TABLE IF EXISTS `news_sentiment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
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
) ENGINE=InnoDB AUTO_INCREMENT=29 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


DROP TABLE IF EXISTS `stock`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stock` (
  `stock_id` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  `stock_name` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `industry` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `update_time` datetime NOT NULL,
  PRIMARY KEY (`stock_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `stock_analysis_report`
--

DROP TABLE IF EXISTS `stock_analysis_report`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stock_analysis_report` (
  `report_id` bigint NOT NULL AUTO_INCREMENT,
  `stock_id` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  `analysis_date` date NOT NULL,
  `avg_sentiment` double DEFAULT NULL,
  `overall_summary` text COLLATE utf8mb4_unicode_ci,
  `report_type` VARCHAR(20) NOT NULL DEFAULT 'TEMPLATE',
  PRIMARY KEY (`report_id`),
  KEY `stock_id` (`stock_id`),
  CONSTRAINT `stock_analysis_report_ibfk_1` FOREIGN KEY (`stock_id`) REFERENCES `stock` (`stock_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE favorite_stocks (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_id VARCHAR(255) NOT NULL,
    added_at DATETIME NOT NULL,
    memo VARCHAR(255),
    target_price DOUBLE,
    FOREIGN KEY (stock_id) REFERENCES stock(stock_id)
);

