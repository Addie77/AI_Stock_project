package com.example.demo.repository;

import com.example.demo.entity.NewsSentiment;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface NewsSentimentRepository extends JpaRepository<NewsSentiment, Long> {

    // 語法解析：
    // findBy         -> 執行 SELECT
    // Stock_StockId    -> 條件一：股票代號
    // And            -> 加上 AND 邏輯
    // PublishDateAfter -> 條件二：發布時間「晚於」某個時間點 (用來抓近3天)
    // OrderByPublishDateDesc -> 照新聞時間新到舊排序
    List<NewsSentiment> findByStock_StockIdAndPublishDateAfterOrderByPublishDateDesc(String stockId, LocalDateTime date);
}