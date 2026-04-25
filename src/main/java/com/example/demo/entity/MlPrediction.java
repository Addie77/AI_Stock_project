package com.example.demo.entity;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.LocalDate;

@Entity
@Table(name = "ml_prediction")
public class MlPrediction {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "predict_id")
    private Long predictId;

    // 外鍵關聯到 Stock
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "stock_id", nullable = false)
    private Stock stock;

    @Column(name = "target_date", nullable = false)
    private LocalDate targetDate;

    // 關鍵字：對齊資料庫的 DECIMAL(5,2) 用來存百分比機率
    @Column(name = "up_probability", precision = 5, scale = 2)
    private BigDecimal upProbability;

    @Column(name = "trade_signal", length = 10)
    private String tradeSignal;

    public Long getPredictId() { return predictId; }
    public void setPredictId(Long predictId) { this.predictId = predictId; }
    public Stock getStock() { return stock; }
    public void setStock(Stock stock) { this.stock = stock; }
    public LocalDate getTargetDate() { return targetDate; }
    public void setTargetDate(LocalDate targetDate) { this.targetDate = targetDate; }
    public BigDecimal getUpProbability() { return upProbability; }
    public void setUpProbability(BigDecimal upProbability) { this.upProbability = upProbability; }
    public String getTradeSignal() { return tradeSignal; }
    public void setTradeSignal(String tradeSignal) { this.tradeSignal = tradeSignal; }
}
