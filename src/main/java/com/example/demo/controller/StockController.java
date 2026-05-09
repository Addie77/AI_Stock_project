package com.example.demo.controller;

import com.example.demo.service.StockAnalysisService;
import org.springframework.web.bind.annotation.*;
import java.util.Map;

// 1. @RestController：告訴 Spring Boot，這是一個專門吐資料 (JSON) 的 API 接口，而不是回傳 HTML 網頁
@RestController

// 2. @RequestMapping：設定這個控制器的「基礎網址」。所有這裡面的方法，網址都會以 /api/stocks 開頭
@RequestMapping("/api/stocks")

// 3. @CrossOrigin：這行是「前端救星」！它允許不同網域（例如你的本機 HTML 檔案）來抓資料，防止瀏覽器的 CORS 跨域安全阻擋
@CrossOrigin(origins = "*")
public class StockController {
    private final StockAnalysisService stockAnalysisService;

    // 依賴注入：啟動時，Spring Boot 會自動把寫好的 Service 派進來工作
    public StockController(StockAnalysisService stockAnalysisService){
        this.stockAnalysisService = stockAnalysisService;
    }
    /**
     * 4. @GetMapping：告訴系統，當有人用 HTTP GET 方法訪問網址時，觸發這個方法。
     * 這裡的 "/{stockId}" 代表這是一個「變數」。
     * 例如訪問 /api/stocks/2330，這個 {stockId} 就會是 2330。
     */
    @GetMapping("/{stockId}")
    // 5. @PathVariable：負責把上面網址裡面的 {stockId} 抓下來，塞進這個 String 變數裡
    public Map<String, Object> getStockData(@PathVariable String stockId){
        // 收到請求後，直接呼叫大腦去處理，並把大腦打包好的 Map 直接回傳！
        // Spring Boot 會在背後自動把這個 Map 翻譯成前端看得懂的 JSON 格式
        return stockAnalysisService.getComprehensiveStockReport(stockId);
    }
}
