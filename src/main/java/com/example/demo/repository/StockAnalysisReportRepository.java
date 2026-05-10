package com.example.demo.repository;

import com.example.demo.entity.StockAnalysisReport;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.Optional;

@Repository
public interface StockAnalysisReportRepository extends JpaRepository<StockAnalysisReport, Long>{
    // 自定義查詢：透過股票代號和「日期」來尋找快取的報告
    Optional<StockAnalysisReport> findByStock_StockIdAndAnalysisDate(String stockId, LocalDate date);
}
