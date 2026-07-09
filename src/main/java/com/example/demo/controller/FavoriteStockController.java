package com.example.demo.controller;

import com.example.demo.entity.FavoriteStock;
import com.example.demo.entity.Stock;
import com.example.demo.repository.FavoriteStockRepository;
import com.example.demo.repository.StockRepository;
import org.springframework.http.ResponseEntity;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@RestController
@RequestMapping("/api/favorites")
@CrossOrigin(origins = "*")
public class FavoriteStockController {

    private final FavoriteStockRepository favoriteStockRepo;
    private final StockRepository stockRepo;

    public FavoriteStockController(FavoriteStockRepository favoriteStockRepo, StockRepository stockRepo) {
        this.favoriteStockRepo = favoriteStockRepo;
        this.stockRepo = stockRepo;
    }

    /**
     * 1. 取得所有自選股清單 (GET /api/favorites)
     */
    @GetMapping
    public ResponseEntity<List<FavoriteStock>> getAllFavorites() {
        List<FavoriteStock> favorites = favoriteStockRepo.findAllWithStock();
        return ResponseEntity.ok(favorites);
    }

    /**
     * 2. 新增自選股 (POST /api/favorites)
     * Payload 範例: { "stockId": "2330", "memo": "長期持有", "targetPrice": 1000.0 }
     */
    @PostMapping
    public ResponseEntity<Map<String, Object>> addFavorite(@RequestBody Map<String, Object> payload) {
        Map<String, Object> response = new HashMap<>();
        String stockId = (String) payload.get("stockId");
        String memo = (String) payload.get("memo");
        
        Double targetPrice = null;
        if (payload.get("targetPrice") != null) {
            targetPrice = ((Number) payload.get("targetPrice")).doubleValue();
        }

        if (stockId == null || stockId.trim().isEmpty()) {
            response.put("error", "股票代碼 (stockId) 為必填欄位");
            return ResponseEntity.badRequest().body(response);
        }

        // 檢查股票是否存在於資料庫中，若無則自動註冊
        Optional<Stock> stockOpt = stockRepo.findById(stockId);
        Stock stock;
        if (stockOpt.isEmpty()) {
            String stockName = (String) payload.getOrDefault("stockName", "自動新增股票");
            stock = new Stock();
            stock.setStockId(stockId);
            stock.setStockName(stockName);
            stock.setUpdateTime(LocalDateTime.now());
            stockRepo.save(stock);
            System.out.println("📝 自選股觸發：已自動註冊新股票：" + stockName + " (" + stockId + ")");
        } else {
            stock = stockOpt.get();
            String stockName = (String) payload.get("stockName");
            if (stockName != null && !stockName.isEmpty() && 
                ("未知股票".equals(stock.getStockName()) || "自動新增股票".equals(stock.getStockName()))) {
                stock.setStockName(stockName);
                stock.setUpdateTime(LocalDateTime.now());
                stockRepo.save(stock);
            }
        }

        // 檢查是否已經在自選清單中
        if (favoriteStockRepo.existsByStock_StockId(stockId)) {
            response.put("message", "此股票已在自選清單中");
            response.put("success", true);
            return ResponseEntity.ok(response);
        }

        FavoriteStock favorite = new FavoriteStock();
        favorite.setStock(stock);
        favorite.setAddedAt(LocalDateTime.now());
        favorite.setMemo(memo);
        favorite.setTargetPrice(targetPrice);

        favoriteStockRepo.save(favorite);

        response.put("success", true);
        response.put("message", "成功加入自選股");
        response.put("favorite", favorite);
        return ResponseEntity.ok(response);
    }

    /**
     * 3. 更新自選股的備忘錄或目標價 (PUT /api/favorites/{stockId})
     * Payload 範例: { "memo": "等拉回再買", "targetPrice": 950.0 }
     */
    @PutMapping("/{stockId}")
    public ResponseEntity<Map<String, Object>> updateFavorite(
            @PathVariable String stockId,
            @RequestBody Map<String, Object> payload) {

        Map<String, Object> response = new HashMap<>();
        Optional<FavoriteStock> favOpt = favoriteStockRepo.findByStock_StockId(stockId);
        
        if (favOpt.isEmpty()) {
            response.put("error", "該股票不在自選清單中");
            return ResponseEntity.status(404).body(response);
        }

        FavoriteStock favorite = favOpt.get();

        if (payload.containsKey("memo")) {
            favorite.setMemo((String) payload.get("memo"));
        }
        if (payload.containsKey("targetPrice")) {
            Number tp = (Number) payload.get("targetPrice");
            favorite.setTargetPrice(tp != null ? tp.doubleValue() : null);
        }

        favoriteStockRepo.save(favorite);

        response.put("success", true);
        response.put("message", "自選股設定已更新");
        response.put("favorite", favorite);
        return ResponseEntity.ok(response);
    }

    /**
     * 4. 刪除自選股 (DELETE /api/favorites/{stockId})
     */
    @DeleteMapping("/{stockId}")
    @Transactional
    public ResponseEntity<Map<String, Object>> deleteFavorite(@PathVariable String stockId) {
        Map<String, Object> response = new HashMap<>();

        if (!favoriteStockRepo.existsByStock_StockId(stockId)) {
            response.put("error", "該股票不在自選清單中");
            return ResponseEntity.status(404).body(response);
        }

        favoriteStockRepo.deleteByStock_StockId(stockId);

        response.put("success", true);
        response.put("message", "已將股票從自選清單中移除");
        return ResponseEntity.ok(response);
    }
}
