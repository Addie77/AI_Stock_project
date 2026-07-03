package com.example.demo.repository;

import com.example.demo.entity.FavoriteStock;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface FavoriteStockRepository extends JpaRepository<FavoriteStock, Long> {

    // 使用 JOIN FETCH 一次載入 Stock 關聯，避免 N+1 查詢問題與 LazyInitializationException
    @Query("SELECT f FROM FavoriteStock f JOIN FETCH f.stock")
    List<FavoriteStock> findAllWithStock();

    // 根據股票代號尋找自選股紀錄
    Optional<FavoriteStock> findByStock_StockId(String stockId);

    // 檢查自選股是否存在
    boolean existsByStock_StockId(String stockId);

    // 根據股票代號刪除自選股紀錄
    void deleteByStock_StockId(String stockId);
}
