package com.example.demo.service;

import com.example.demo.entity.*;
import com.example.demo.repository.*;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.*;

// 告訴 Spring Boot：「這是一個大腦，請把它啟動並放進記憶體裡隨時待命」
@Service
public class StockAnalysisService {

    // 宣告為 final 是業界安全標準，確保遙控器在初始化後不會被惡意修改
    private final StockRepository stockRepo;
    private final DailyQuoteRepository quoteRepo;
    private final NewsSentimentRepository newsRepo;
    private final MlPredictionRepository mlRepo;
    private final StockAnalysisReportRepository reportRepo;

    // 依賴注入 (Constructor Injection)：
    // 當這個 Service 被啟動時，Spring Boot 會自動把這 5 個遙控器的實體「塞」進來給我們用
    public StockAnalysisService(StockRepository stockRepo,
                                DailyQuoteRepository quoteRepo,
                                NewsSentimentRepository newsRepo,
                                MlPredictionRepository mlRepo,
                                StockAnalysisReportRepository reportRepo){
        this.stockRepo = stockRepo;
        this.quoteRepo = quoteRepo;
        this.newsRepo = newsRepo;
        this.mlRepo = mlRepo;
        this.reportRepo = reportRepo;
    }

    /**
     * 核心功能：獲取單一股票的「全方位綜合大禮包」
     * 網頁端只要呼叫這個方法，就能拿到畫圖和顯示所需的所有數據！
     */
    public Map<String, Object> getComprehensiveStockReport(String stockId) {
        Map<String, Object> reportBox = new HashMap<>();

        // 1. 查詢股票基本資料
        Optional<Stock> stockOpt = stockRepo.findById(stockId);
        if (stockOpt.isEmpty()){
            reportBox.put("error", "找不到代號為 " + stockId + " 的股票");
            return reportBox;
        }
        Stock stock = stockOpt.get();
        reportBox.put("stockInfo", stock);

        // 🌟 最佳化調整：將「撈取近 3 天新聞」的動作提前
        // 不管今天有沒有快取報告，網頁端最後都需要顯示最近的新聞，因此先撈出來，避免在 else 區塊重複查詢資料庫
        LocalDateTime threeDaysAgo = LocalDateTime.now().minusDays(3);
        List<NewsSentiment> recentNews = newsRepo.findByStock_StockIdAndPublishDateAfterOrderByPublishDateDesc(stockId, threeDaysAgo);
        reportBox.put("recentNews", recentNews); // 直接塞入準備回傳的箱子裡

        // 🌟 2. 核心快取邏輯：檢查今天的報告是否已經算過了
        LocalDate today = LocalDate.now();
        Optional<StockAnalysisReport> todayReportOpt = reportRepo.findByStock_StockIdAndAnalysisDate(stockId, today);

        if (todayReportOpt.isPresent()) {
            // ✅ 情況 A：今天已經有報告了，直接拿出來用 (秒殺級速度，0 資料庫新聞運算負擔)
            StockAnalysisReport todayReport = todayReportOpt.get();
            reportBox.put("averageSentimentScore", todayReport.getAvgSentiment());
            reportBox.put("overallAiSummary", todayReport.getOverallSummary());
            reportBox.put("reportType", todayReport.getReportType()); // 加入這行
            System.out.println("⚡ 讀取快取：使用今日已生成的分析報告！");
        } else {
            // ❌ 情況 B：今天還沒算過，啟動分析邏輯並存入資料庫
            System.out.println("🤖 今日無紀錄，開始計算平均分與總評...");

            // 計算平均分：直接重複利用上面已經撈好的 recentNews 變數，不用再查一次資料庫！
            double avgScore = 0.0;
            if (!recentNews.isEmpty()) {
                avgScore = recentNews.stream()
                        .mapToInt(NewsSentiment::getSentimentScore)
                        .average()
                        .orElse(0.0);
            }
            
            // 四捨五入到小數點後兩位
            double finalAvgScore = Math.round(avgScore * 100.0) / 100.0;

            // 根據平均分生成總評文字
            String totalAiSummary;
            if (finalAvgScore >= 80) {
                totalAiSummary = "【極度樂觀】近期新聞情緒極佳，看好短期表現。";
            } else if (finalAvgScore >= 60) {
                totalAiSummary = "【偏向樂觀】新聞多為正面，建議持續關注。";
            } else if (finalAvgScore >= 40) {
                totalAiSummary = "【中立觀望】近期新聞多空交雜，市場情緒不明朗。";
            } else {
                totalAiSummary = "【警訊注意】近期新聞情緒偏低，需留意潛在利空。";
            }

            // 🌟 將算好的結果打包成新報告，存進資料庫，下次查詢就能直接走情況 A！
            StockAnalysisReport newReport = new StockAnalysisReport();
            newReport.setStock(stock);
            newReport.setAnalysisDate(today);
            newReport.setAvgSentiment(finalAvgScore);
            newReport.setOverallSummary(totalAiSummary);
            newReport.setReportType("TEMPLATE"); // 明確標記為模板
            reportRepo.save(newReport); // 存檔完成

            // 放進準備回傳給網頁的箱子裡
            reportBox.put("averageSentimentScore", finalAvgScore);
            reportBox.put("overallAiSummary", totalAiSummary);
            reportBox.put("reportType", "TEMPLATE"); // 加入這行
        }

        // 3. 補上其他原本就該回傳的資料（歷史股價與機器學習預測）
        List<DailyQuote> quotes = quoteRepo.findByStock_StockIdOrderByTradeDateDesc(stockId);
        reportBox.put("historicalQuotes", quotes);

        Optional<MlPrediction> latestPrediction = mlRepo.findFirstByStock_StockIdOrderByTargetDateDesc(stockId);
        reportBox.put("aiPrediction", latestPrediction.orElse(null));

        return reportBox;
    }
}