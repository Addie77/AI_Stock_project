package com.example.demo.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.LocalDateTime;

@Entity // 告訴 Spring Boot 這是一個要對應資料庫的實體
@Table(name = "stock") // 明確指定它對應到 MySQL 裡的 "stock" 這張表
public class Stock {

    @Id // 告訴系統這是 Primary Key (主鍵)
    @Column(name = "stock_id", length = 10)
    private String stockId;

    @Column(name = "stock_name", length = 50, nullable = false)
    private String stockName;

    @Column(name = "industry", length = 50)
    private String industry;

    @Column(name = "update_time", nullable = false)
    private LocalDateTime updateTime;

    public String getStockId() {return stockId;}
    public void setStockId(String stockId) {this.stockId = stockId;}
    public String getStockName() {return stockName;}
    public void setStockName(String stockName) {this.stockName = stockName;}
    public String getIndustry() {return industry;}
    public void setIndustry(String industry) {this.industry = industry;}
    public LocalDateTime getUpdateTime() {return updateTime;}
    public void setUpdateTime(LocalDateTime updateTime) {this.updateTime = updateTime;}
}
