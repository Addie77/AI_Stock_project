package com.example.demo.controller;

import com.example.demo.entity.NewsSentiment;
import com.example.demo.entity.Stock;
import com.example.demo.repository.NewsSentimentRepository;
import com.example.demo.repository.StockRepository;
import org.springframework.web.bind.annotation.*;
import com.example.demo.entity.StockAnalysisReport; // 加入這行
import com.example.demo.repository.StockAnalysisReportRepository; // 加入這行
import java.time.LocalDate;

import java.time.LocalDateTime;
import java.util.Map;

@RestController
@RequestMapping("/api/ingest")// 專門給 Python 呼叫的內部 API 路徑
public class DataIngestionController {

    private final StockRepository stockRepo;
    private final NewsSentimentRepository newsRepo;
    private final StockAnalysisReportRepository reportRepo;

    public DataIngestionController(StockRepository stockRepo, NewsSentimentRepository newsRepo,  StockAnalysisReportRepository reportRepo) {
        this.stockRepo = stockRepo;
        this.newsRepo = newsRepo;
        this.reportRepo = reportRepo;
    }

    // 接收 Python 發送的 POST 請求
    @PostMapping("/news")
    public String receiveNewsData(@RequestBody Map<String, Object> payload){

        // 1. 從 Python 傳來的 JSON 中取出股票代號
        String stockId = (String) payload.get("stockId");
        // 🌟 自動註冊機制：檢查資料庫有沒有這檔股票
        Stock stock = stockRepo.findById(stockId).orElse(null);
        if(stock == null){
            // 如果沒有，就自動幫它建檔！
            stock = new Stock();
            stock.setStockId(stockId);
            stock.setStockName("自動新增股票");   // 先給預設名稱
            stock.setUpdateTime(LocalDateTime.now());
            stockRepo.save(stock);  // 存進 stock 表
            System.out.println("⚠️ 偵測到新股票，已自動註冊代號：" + stockId);
        }

        // 3. 建立新聞實體，把 Python 傳來的資料塞進去
        NewsSentiment news = new NewsSentiment();
        news.setStock(stock);
        // 注意：Python 傳來的時間格式必須是 ISO 8601 (例如 2026-04-25T10:30:00)
        news.setPublishDate(LocalDateTime.parse((String) payload.get("publishDate")));
        news.setTitle((String) payload.get("title"));
        news.setContentUrl((String) payload.get("contentUrl"));
        news.setSentimentScore((Integer) payload.get("sentimentScore"));
        news.setContentSummary((String) payload.get("contentSummary"));

        // 4. 遙控器按下 Save，存入 MySQL！
        newsRepo.save(news);

        return "成功：已將 " + stockId + " 的新聞與情緒分析寫入資料庫！";

    }

    @PostMapping("/report")
    public String receiveAnalysisReport(@RequestBody Map<String, Object> payload){

        String stockId = (String) payload.get("stockId");
        // 1. 檢查股票是否存在
        Stock stock = stockRepo.findById(stockId).orElse(null);
        if (stock == null) {
            return "錯誤：找不到股票代號 " + stockId + "，無法儲存報告。";
        }

        // 2. 解析日期 (Python 傳來的是 YYYY-MM-DD)
        LocalDate analysisDate = LocalDate.parse((String) payload.get("analysisDate"));

        // 3. 檢查今天是否已經有報告了 (Update or Insert)
        StockAnalysisReport report = reportRepo.findByStock_StockIdAndAnalysisDate(stockId, analysisDate).orElse(null);

        if(report == null){
            // 如果沒有，建一個新的
            report = new StockAnalysisReport();
            report.setStock(stock);
            report.setAnalysisDate(analysisDate);
            System.out.println("📝 建立新的分析報告：" + stockId);
        }else{
            System.out.println("🔄 更新今日分析報告：" + stockId);
        }

        // 4. 塞入分數與 Gemini 產生的總評
        // 處理 Double 型態轉換，避免 JSON 傳整數時出錯
        Number avgScore = (Number) payload.get("avgSentiment");
        report.setAvgSentiment(avgScore.doubleValue());

        report.setOverallSummary((String) payload.get("overallSummary"));

        // 5. 存入資料庫
        reportRepo.save(report);

         return "成功：已儲存 " + stockId + " 的 AI 綜合分析報告！";

    }
}
