package com.example.demo.entity;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.LocalDate;

@Entity
@Table(name = "daily_quote")
public class DailyQuote {

    @Id
    // 告訴 Spring Boot 這個主鍵是資料庫自動遞增的 (AUTO_INCREMENT)
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "quote_id")
    private Long quoteId;

    //外鍵關聯！在 Java 裡我們不存 String stockId，而是直接關聯整個 Stock 物件
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "stock_id", nullable = false)
    private Stock stock;

    @Column(name = "trade_date", nullable = false)
    private LocalDate tradeDate;

    // 金融界標準：凡是遇到精確小數點 (DECIMAL)，在 Java 一律使用 BigDecimal
    @Column(name = "close_price", precision = 10, scale = 2)
    private BigDecimal closePrice;

    @Column(name = "volume")
    private Long volume;

    @Column(name = "ma_5", precision = 10, scale = 2)
    private BigDecimal ma5;

    @Column(name = "ma_20", precision = 10, scale = 2)
    private BigDecimal ma20;

    public Long getQuoteId() {return quoteId;}
    public void setQuoteId(Long quoteId) {this.quoteId = quoteId;}
    public Stock getStock() {return stock;}
    public void setStock(Stock stock) {this.stock = stock;}
    public LocalDate getTradeDate() {return tradeDate;}
    public void setTradeDate(LocalDate tradeDate) {this.tradeDate = tradeDate;}
    public BigDecimal getClosePrice() {return closePrice;}
    public void setClosePrice(BigDecimal closePrice) {this.closePrice = closePrice;}
    public Long getVolume() {return volume;}
    public void setVolume(Long volume) {this.volume = volume;}
    public BigDecimal getMa5() {return ma5;}
    public void setMa5(BigDecimal ma5) {this.ma5 = ma5;}
    public BigDecimal getMa20() {return ma20;}
    public void setMa20(BigDecimal ma20) {this.ma20 = ma20;}
}
