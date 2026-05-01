package com.example.demo.repository;

import com.example.demo.entity.MlPrediction;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.Optional;

@Repository
public interface MlPredictionRepository extends JpaRepository<MlPrediction, Long> {

    // 語法解析：
    // findFirstBy -> 只抓第一筆 (LIMIT 1)
    // 條件：股票代號，並依照預測目標日期排序，抓最新的
    Optional<MlPrediction> findFirstByStock_StockIdOrderByTargetDateDesc(String stockId);
}