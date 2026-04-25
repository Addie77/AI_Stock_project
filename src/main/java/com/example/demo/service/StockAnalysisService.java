package com.example.demo.service;

import com.example.demo.entity.DailyQuote;
import com.example.demo.entity.MlPrediction;
import com.example.demo.entity.NewsSentiment;
import com.example.demo.entity.Stock;
import com.example.demo.repository.DailyQuoteRepository;
import com.example.demo.repository.MlPredictionRepository;
import com.example.demo.repository.NewsSentimentRepository;
import com.example.demo.repository.StockRepository;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;

// 告訴 Spring Boot：「這是一個大腦，請把它啟動並放進記憶體裡隨時待命」
@Service
public class StockAnalysisService {
    //宣告為 final 是業界安全標準
    private final StockRepository stockRepo;
    private final DailyQuoteRepository quoteRepo;
    private final NewsSentimentRepository newsRepo;
    private final MlPredictionRepository mlRepo;

    // 依賴注入 (Constructor Injection)：
    // 當這個 Service 被啟動時，Spring Boot 會自動把這 4 個遙控器的實體「塞」進來給我們用
    public StockAnalysisService(StockRepository stockRepo,
                                DailyQuoteRepository quoteRepo,
                                NewsSentimentRepository newsRepo,
                                MlPredictionRepository mlRepo){
        this.stockRepo = stockRepo;
        this.quoteRepo = quoteRepo;
        this.newsRepo = newsRepo;
        this.mlRepo = mlRepo;
    }
    /**
     *  核心功能：獲取單一股票的「全方位綜合大禮包」
     * 網頁端只要呼叫這個方法，就能拿到畫圖和顯示所需的所有數據！
     */
    public Map<String, Object> getComprehensiveStockReport(String stockId) {
        // 準備一個箱子 (Map) 來裝我們的大禮包
        Map<String, Object> reportBox = new HashMap<>();

        // 1. 拿遙控器 1 號：查詢股票基本資料
        Optional<Stock> stockOpt = stockRepo.findById(stockId);
        if (stockOpt.isEmpty()){
            // 如果資料庫根本沒有這檔股票，直接回傳錯誤訊息
            reportBox.put("error", "找不到代號為 " + stockId + " 的股票");
            return reportBox;
        }
        reportBox.put("stoclInfo", stockOpt.get());

        // 2. 拿遙控器 2 號：查詢歷史股價 (畫 K 線圖用)
        List<DailyQuote> quotes = quoteRepo.findByStock_StockIdOrderByTradeDateDesc(stockId);
        reportBox.put("historicalQuotes", quotes);

        // 3. 拿遙控器 3 號：查詢近 3 天的新聞與 AI 總評
        LocalDateTime threeDaysAgo = LocalDateTime.now().minusDays(3);
        List<NewsSentiment> recentNews = newsRepo.findByStock_StockIdAndPublishDateAfterOrderByPublishDateDesc(stockId, threeDaysAgo);

        // 4. 拿遙控器 4 號：查詢最新的 AI 預測機率
        Optional<MlPrediction> latestPrediction = mlRepo.findFirstByStock_StockIdOrderByTargetDateDesc(stockId);
        // 如果有預測資料就放進去，沒有就放 null
        reportBox.put("aiPrediction", latestPrediction.orElse(null));

        return reportBox;

    }
}
