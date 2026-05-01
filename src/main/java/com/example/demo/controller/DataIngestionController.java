package com.example.demo.controller;

import com.example.demo.entity.NewsSentiment;
import com.example.demo.entity.Stock;
import com.example.demo.repository.NewsSentimentRepository;
import com.example.demo.repository.StockRepository;
import com.sun.jdi.event.StepEvent;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.Map;

@RestController
@RequestMapping("/api/ingest")// 專門給 Python 呼叫的內部 API 路徑
public class DataIngestionController {

    private final StockRepository stockRepo;
    private final NewsSentimentRepository newsRepo;

    public DataIngestionController(StockRepository stockRepo, NewsSentimentRepository newsRepo) {
        this.stockRepo = stockRepo;
        this.newsRepo = newsRepo;
    }

    // 接收 Python 發送的 POST 請求
    @PostMapping("/news")
    public String receiveNewsData(@RequestBody Map<String, Object> payload){

        // 1. 從 Python 傳來的 JSON 中取出股票代號
        String stockId = (String) payload.get("stockId");

        // 2. 檢查資料庫有沒有這檔股票 (因為外鍵關聯，必須先找出 Stock 實體)
        Stock stock = stockRepo.findById(stockId).orElse(null);
        if(stock == null){
            return "寫入失敗：資料庫找不到股票代號 " + stockId;
        }

        // 3. 建立新聞實體，把 Python 傳來的資料塞進去
        NewsSentiment news = new NewsSentiment();
        news.setStock(stock);
        // 注意：Python 傳來的時間格式必須是 ISO 8601 (例如 2026-04-25T10:30:00)
        news.setPublishDate(LocalDateTime.parse((String) payload.get("publishDate")));
        news.setTitle((String) payload.get("title"));
        news.setContentUrl((String) payload.get("contentUrl"));
        news.setSentimentScore((Integer) payload.get("sentimentScore"));
        news.setAiSummary((String) payload.get("aiSummary"));

        // 4. 遙控器按下 Save，存入 MySQL！
        newsRepo.save(news);

        return "成功：已將 " + stockId + " 的新聞與情緒分析寫入資料庫！";

    }

}
