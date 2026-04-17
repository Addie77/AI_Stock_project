package com.example.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "news_sentiment")
public class NewSentiment {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "news_id")
    private Long newsId;

    // 外鍵關聯到 Stock
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "stock_id", nullable = false)
    private Stock stock;

    @Column(name = "piblish_data", nullable = false)
    private LocalDateTime publishDate;

    @Column(name = "title", nullable = false)
    private String title;

    @Column(name = "content_url", length = 500)
    private String contentUrl;

    @Column(name = "sentiment_score")
    private Integer sentimentScore;

    // 關鍵字：明確指定資料庫要對應 TEXT 型態，能塞超長文章
    @Column(name = "ai_summary", columnDefinition = "TEXT")
    private String aiSummary;

    public Long getNewsId() { return newsId; }
    public void setNewsId(Long newsId) { this.newsId = newsId; }
    public Stock getStock() { return stock; }
    public void setStock(Stock stock) { this.stock = stock; }
    public LocalDateTime getPublishDate() { return publishDate; }
    public void setPublishDate(LocalDateTime publishDate) { this.publishDate = publishDate; }
    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    public String getContentUrl() { return contentUrl; }
    public void setContentUrl(String contentUrl) { this.contentUrl = contentUrl; }
    public Integer getSentimentScore() { return sentimentScore; }
    public void setSentimentScore(Integer sentimentScore) { this.sentimentScore = sentimentScore; }
    public String getAiSummary() { return aiSummary; }
    public void setAiSummary(String aiSummary) { this.aiSummary = aiSummary; }
}
