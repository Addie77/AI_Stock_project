package com.example.demo.repository;

import com.example.demo.entity.DailyQuote;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface DailyQuoteRepository extends JpaRepository<DailyQuote, Long> {
    // 語法解析：
    // findBy      -> 告訴系統我要執行 SELECT
    // Stock_StockId -> 透過外鍵 Stock 找到裡面的 StockId
    // OrderBy     -> 告訴系統我要排序 (ORDER BY)
    // TradeDate   -> 用交易日期排序
    // Desc        -> 降冪排列 (新到舊)
    List<DailyQuote> findByStock_StockIdOrderByTradeDateDesc(String stockId);
}
