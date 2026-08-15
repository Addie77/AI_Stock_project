/**
 * ============================================================================
 * 全域變數定義 (Global Variables)
 * ============================================================================
 */
let stockChart;          // 儲存 Chart.js 的圖表實例（Instance），以便後續銷毀並重建圖表
let currentStockCode = ''; // 💡 核心修正：將初始追蹤代碼設為空字串，完全移除預設股票
let isSearching = false;   // 💡 新增：全域變數，防止重複與並行搜尋導致狀態衝突

if (typeof Chart !== 'undefined') {
    const financialPlugin = window['chartjs-chart-financial'];
    if (financialPlugin) {
        Chart.register(
            financialPlugin.CandlestickController,
            financialPlugin.CandlestickElement,
            financialPlugin.FinancialLinearScale
        );
    } else if (Chart.CandlestickController) {
        Chart.register(
            Chart.CandlestickController,
            Chart.CandlestickElement
        );
    }
}
/**
 * ============================================================================
 * 網頁初始化與事件監聽 (Initialization & Event Listeners)
 * ============================================================================
 */
document.addEventListener('DOMContentLoaded', () => {
    initDashboardState();
    
    // 監聽搜尋框的按鍵事件
    document.getElementById('stockSearch').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const inputCode = e.target.value.trim();
            if (inputCode) {
                showDashboardView();
                fetchStockData(inputCode);
            }
        }
    });

    // 監聽「生成 AI 智能建議報告」按鈕的點擊事件
    document.getElementById('generateAiBtn').addEventListener('click', () => {
        if (!currentStockCode) {
            alert("請先在上方搜尋股票代碼，再生成 AI 報告。");
            return;
        }
        fetchAiReport(currentStockCode);
    });

    /**
     * 💡 互動功能：點擊左側「AI 報告」選單自動平滑跳轉至對應區塊
     */
    document.getElementById('navAiReport').addEventListener('click', () => {
        showDashboardView();

        const aiSection = document.getElementById('aiReportSection');
        if (aiSection) {
            aiSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        
        document.querySelectorAll('.nav-links li').forEach(li => li.classList.remove('active'));
        document.getElementById('navAiReport').classList.add('active');
    });

    /**
     * 💡 互動功能：點擊左側「市場總覽」回到網頁最頂端
     */
    document.getElementById('navMarketOverview').addEventListener('click', () => {
        showDashboardView();
        window.scrollTo({ top: 0, behavior: 'smooth' });
        
        document.querySelectorAll('.nav-links li').forEach(li => li.classList.remove('active'));
        document.getElementById('navMarketOverview').classList.add('active');
    });

    /**
     * 💡 新增互動功能：點擊左側「自選股」切換至自選頁面
     */
    document.getElementById('navWatchlist').addEventListener('click', () => {
        document.getElementById('mainDashboardViews').style.display = 'none';
        document.getElementById('trendingSection').style.display = 'none';
        document.getElementById('watchlistSection').style.display = 'block';
        window.scrollTo({ top: 0, behavior: 'smooth' });

        document.querySelectorAll('.nav-links li').forEach(li => li.classList.remove('active'));
        document.getElementById('navWatchlist').classList.add('active');

        if (typeof loadWatchlist === 'function') {
            loadWatchlist();
        }
    });

    /**
     * 💡 整合新增互動功能：點擊左側「熱門股票」切換至熱門頁面並自動載入
     */
    document.getElementById('navTrending').addEventListener('click', () => {
        document.getElementById('mainDashboardViews').style.display = 'none';
        document.getElementById('watchlistSection').style.display = 'none';
        document.getElementById('trendingSection').style.display = 'block';
        window.scrollTo({ top: 0, behavior: 'smooth' });

        document.querySelectorAll('.nav-links li').forEach(li => li.classList.remove('active'));
        document.getElementById('navTrending').classList.add('active');

        // 💡 切換過來時自動執行爬蟲更新
        fetchLiveTrendingStocks();
    });

    // 監聽心型「加入自選股」按鈕的點擊事件
    document.getElementById('addWatchlistBtn').addEventListener('click', async () => {
        if (!currentStockCode) {
            alert("請先搜尋股票代碼，再加入自選股。");
            return;
        }
        
        const displayNameText = document.getElementById('displayName').innerText;
        let stockName = "未知股票";
        if (displayNameText.includes('(')) {
            stockName = displayNameText.split('(')[0].trim();
        }

        try {
            const res = await fetch(`http://localhost:8080/api/favorites`);
            if (!res.ok) throw new Error("無法連接自選股服務");
            const favorites = await res.json();
            const isFav = favorites.some(fav => fav.stock.stockId === currentStockCode);
            
            if (isFav) {
                const delRes = await fetch(`http://localhost:8080/api/favorites/${currentStockCode}`, {
                    method: 'DELETE'
                });
                const delData = await delRes.json();
                if (delRes.ok && delData.success) {
                    updateFavoriteIcon(false);
                    if (document.getElementById('watchlistSection').style.display === 'block') {
                        loadWatchlist();
                    }
                } else {
                    alert("移除自選股失敗: " + (delData.error || "未知錯誤"));
                }
            } else {
                const addRes = await fetch(`http://localhost:8080/api/favorites`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        stockId: currentStockCode,
                        stockName: stockName
                    })
                });
                const addData = await addRes.json();
                if (addRes.ok && addData.success) {
                    updateFavoriteIcon(true);
                    if (document.getElementById('watchlistSection').style.display === 'block') {
                        loadWatchlist();
                    }
                } else {
                    alert("加入自選股失敗: " + (addData.error || "未知錯誤"));
                }
            }
        } catch (e) {
            console.error("操作自選股失敗:", e);
            alert("操作失敗: " + e.message);
        }
    });
});

/**
 * 💡 輔助函式：切換回主儀表板畫面
 */
function showDashboardView() {
    document.getElementById('mainDashboardViews').style.display = 'flex';
    document.getElementById('watchlistSection').style.display = 'none';
    document.getElementById('trendingSection').style.display = 'none';
}

/**
 * 💡 初始化儀表板待命狀態 UI
 */
function initDashboardState() {
    document.getElementById('displayName').innerText = "請搜尋股票代碼";
    document.getElementById('sentFill').style.width = '0%';
    document.getElementById('sentVal').innerText = "0 / 100";
    document.getElementById('aiSummary').innerText = "等待搜尋股票數據...";
    
    const predictValEl = document.getElementById('predictVal');
    if (predictValEl) {
        predictValEl.innerText = "待搜尋股票";
        predictValEl.style.color = "#64748b";
    }
    const predictProbEl = document.getElementById('predictProb');
    if (predictProbEl) {
        predictProbEl.innerText = "--%";
        predictProbEl.style.color = "#64748b";
    }
    const predictBadgeEl = document.getElementById('predictBadge');
    if (predictBadgeEl) {
        predictBadgeEl.style.display = "none";
    }
    
    if (typeof updateFavoriteIcon === 'function') {
        updateFavoriteIcon(false);
    }
    
    if (stockChart) {
        stockChart.destroy();
        stockChart = null;
    }
}

/**
 * 💡 統一更新機器學習預測卡片 UI
 */
function updatePredictionUI(pred) {
    const predictValEl = document.getElementById('predictVal');
    const predictProbEl = document.getElementById('predictProb');
    const predictBadgeEl = document.getElementById('predictBadge');
    
    if (pred) {
        let signalText = "中立觀望";
        let signalColor = "#64748b";
        if (pred.tradeSignal === "STRONG_BUY") {
            signalText = "強烈買進";
            signalColor = "#f87171";
        } else if (pred.tradeSignal === "BUY") {
            signalText = "偏多";
            signalColor = "#fca5a5";
        } else if (pred.tradeSignal === "HOLD") {
            signalText = "中立觀望";
            signalColor = "#94a3b8";
        } else if (pred.tradeSignal === "SELL") {
            signalText = "偏空";
            signalColor = "#86efac";
        } else if (pred.tradeSignal === "STRONG_SELL") {
            signalText = "強烈賣出";
            signalColor = "#4ade80";
        }
        
        if (predictValEl) {
            predictValEl.innerText = signalText;
            predictValEl.style.color = signalColor;
        }
        
        if (predictProbEl) {
            const upProbVal = parseFloat(pred.upProbability).toFixed(1);
            predictProbEl.innerText = `${upProbVal}%`;
            predictProbEl.style.color = signalColor;
        }
    } else {
        if (predictValEl) {
            predictValEl.innerText = "暫無預測數據";
            predictValEl.style.color = "#64748b";
        }
        if (predictProbEl) {
            predictProbEl.innerText = "--%";
            predictProbEl.style.color = "#64748b";
        }
    }
    
    if (predictBadgeEl) {
        if (pred && pred.isSentimentFused === true) {
            predictBadgeEl.className = "badge-ai";
            predictBadgeEl.innerText = "💡 綜合預測 (已融合 AI 新聞輿情)";
            predictBadgeEl.title = "此預測已結合 5 年技術指標大數據與最新 BERT 新聞情緒偏離值動態修正。";
            predictBadgeEl.style.display = "inline-block";
        } else {
            predictBadgeEl.className = "badge-tech";
            predictBadgeEl.innerText = "📊 量化預測 (純技術指標分析)";
            predictBadgeEl.title = "此預測基於 5 年技術指標大數據進行預測。";
            predictBadgeEl.style.display = "inline-block";
        }
    }
}

/**
 * ============================================================================
 * 第一階段：抓取基礎資料 (歷史價格、本地端 FinBERT 情感分數)
 * ============================================================================
 */
async function fetchStockData(code) {
    if (isSearching) {
        console.warn("⚠️ 搜尋任務正在進行中，忽略重複請求。");
        return;
    }
    isSearching = true;

    currentStockCode = code;
    
    document.getElementById('aiSummary').innerText = "請點擊上方按鈕，以生成基於 6 個月歷史數據的 AI 技術面分析建議。";
    const aiAdvice = document.getElementById('aiAdvice');
    aiAdvice.style.display = 'none';
    aiAdvice.innerHTML = '';

    document.getElementById('displayName').innerText = `🔍 正在擷取 ${code} 數據與進行即時預測中...`;

    try {
        const response = await fetch(`http://127.0.0.1:5000/api/analyze?code=${code}&_t=${new Date().getTime()}`);
        const data = await response.json();
        
        if (!response.ok) throw new Error(data.error);

        document.getElementById('displayName').innerText = `${data.name} (${code})`;
        document.getElementById('sentFill').style.width = data.sentiment_score + '%'; 
        document.getElementById('sentVal').innerText = data.sentiment_score + " / 100";
        
        updatePredictionUI(data.ai_prediction);

        renderChart(
            data.history_dates || [], 
            data.history_opens || data.history_prices || [], 
            data.history_highs || data.history_prices || [], 
            data.history_lows || data.history_prices || [], 
            data.history_prices || [], 
            data.history_volumes || []
        );

        if (typeof checkFavoriteStatus === 'function') {
            checkFavoriteStatus(code);
        }
        isSearching = false;
        
    } catch (error) {
        isSearching = false;
        console.error("Fetch Error:", error);
        initDashboardState();
        document.getElementById('aiSummary').innerText = `❌ 連線失敗或無此股票資料：${error.message}`;
    }
}

/**
 * ============================================================================
 * 第二階段：點擊按鈕同步新聞並生成雲端 AI 投顧級深度分析報告
 * ============================================================================
 */
async function fetchAiReport(code) {
    const aiSummary = document.getElementById('aiSummary');
    const aiAdvice = document.getElementById('aiAdvice');
    const btn = document.getElementById('generateAiBtn');

    aiSummary.innerText = "🚀 正在啟動深度新聞分析任務 (預計耗時較長，請勿關閉視窗)...";
    aiAdvice.style.display = 'none'; 
    btn.disabled = true;             

    try {
        const startRes = await fetch(`http://127.0.0.1:5000/api/sync_news?code=${code}`, { cache: 'no-store' });
        const startData = await startRes.json();
        if (!startRes.ok) throw new Error(startData.error || "啟動任務失敗");

        if (startData.status === 'completed') {
            console.log("🚀 快取命中！直接載入今日分析數據。");
            document.getElementById('sentFill').style.width = startData.avg_sentiment + '%'; 
            document.getElementById('sentVal').innerText = startData.avg_sentiment + " / 100";
            if (startData.ai_prediction) {
                updatePredictionUI(startData.ai_prediction);
            }
            var finalSyncResult = {
                avg_sentiment: startData.avg_sentiment,
                ai_summary: startData.ai_summary || "今日報告已儲存。"
            };
        } else {
            let isFinished = false;
            var finalSyncResult = null;
            let waitTime = 0;

            while (!isFinished) {
                await new Promise(resolve => setTimeout(resolve, 10000));
                waitTime += 10;
                aiSummary.innerText = `⏳ 正在爬取新聞並進行 AI 語意分析... (已耗時 ${waitTime} 秒)\n這可能需要 5-10 分鐘，您可以先查看其他分頁。`;

                const statusRes = await fetch(`http://127.0.0.1:5000/api/check_status?code=${code}&_t=${new Date().getTime()}`, { cache: 'no-store' });
                const statusData = await statusRes.json();

                if (statusData.status === 'completed') {
                    isFinished = true;
                    finalSyncResult = statusData;
                    document.getElementById('sentFill').style.width = statusData.avg_sentiment + '%'; 
                    document.getElementById('sentVal').innerText = statusData.avg_sentiment + " / 100";
                    if (statusData.ai_prediction) {
                        updatePredictionUI(statusData.ai_prediction);
                    }
                } else if (statusData.status === 'error') {
                    throw new Error(statusData.message || "背景分析發生錯誤");
                }
            }
        }

        aiSummary.innerText = "✅ 新聞分析完成！正在調用 Gemini 生成最終實戰建議報告...";
        const aiResponse = await fetch(`http://127.0.0.1:5000/api/generate_ai?code=${code}`, { cache: 'no-store' });
        const aiResult = await aiResponse.json();

        if (!aiResponse.ok) throw new Error(aiResult.error || "AI 報告生成失敗");

        aiSummary.innerText = aiResult.analysis_summary;
        aiAdvice.innerHTML = `
            <div style="background: rgba(56, 189, 248, 0.08); border-left: 5px solid #38bdf8; padding: 18px; margin-bottom: 20px; border-radius: 8px;">
                <div style="color: #38bdf8; font-weight: 800; font-size: 1.1em; margin-bottom: 8px; display: flex; align-items: center;">
                    <span style="margin-right: 8px;">📰</span> 新聞消息面深度總評
                </div>
                <div style="color: #e2e8f0; line-height: 1.7; font-size: 0.95em;">
                    ${finalSyncResult.ai_summary}
                </div>
            </div>
            
            <div style="background: rgba(52, 211, 153, 0.08); border-left: 5px solid #34d399; padding: 18px; border-radius: 8px;">
                <div style="color: #34d399; font-weight: 800; font-size: 1.1em; margin-bottom: 8px; display: flex; align-items: center;">
                    <span style="margin-right: 8px;">💡</span> AI 技術面實戰建議
                </div>
                <div style="color: #e2e8f0; line-height: 1.7; font-size: 0.95em;">
                    ${aiResult.advice}
                </div>
            </div>
        `;
        
        aiAdvice.style.display = 'block'; 
        console.log("✨ 綜合 AI 報告渲染成功！");
        
    } catch (error) {
        console.error("Polling Error:", error);
        aiSummary.innerText = `❌ 執行失敗：${error.message}`;
        aiAdvice.style.display = 'none';
    } finally {
        btn.disabled = false;
    }
}

/**
 * ============================================================================
 * 數據視覺化核心：Chart.js K 線圖 (Candlestick) + 成交量雙 Y 軸引擎
 * ============================================================================
 */
function renderChart(dates = [], opens = [], highs = [], lows = [], prices = [], volumes = []) {
    const canvas = document.getElementById('stockChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    if (stockChart) {
        stockChart.destroy();
        stockChart = null;
    }

    if (!dates || dates.length === 0) {
        console.warn("⚠️ 歷史資料為空，跳過圖表渲染。");
        return;
    }

    const formattedDates = dates.map(dStr => {
        if (!dStr) return '';
        const parts = String(dStr).split('/');
        if (parts.length === 3) {
            const year = parseInt(parts[0], 10) + 1911;
            const month = parts[1].padStart(2, '0');
            const day = parts[2].padStart(2, '0');
            return `${year}-${month}-${day}`;
        }
        return dStr;
    });

    const candlestickData = formattedDates.map((date, i) => ({
        x: date,
        o: Number(opens[i]) || 0,
        h: Number(highs[i]) || 0,
        l: Number(lows[i]) || 0,
        c: Number(prices[i]) || 0
    }));

    const validHighs = candlestickData.map(d => d.h).filter(v => v > 0);
    const validLows = candlestickData.map(d => d.l).filter(v => v > 0);

    let priceMax = validHighs.length > 0 ? Math.max(...validHighs) : 100;
    let priceMin = validLows.length > 0 ? Math.min(...validLows) : 0;

    if (priceMax > priceMin) {
        const diff = priceMax - priceMin;
        priceMax += diff * 0.05;
        priceMin -= diff * 0.05;
    }

    const numericVolumesIn張 = volumes.map(v => Math.round((Number(v) || 0) / 1000));
    
    const volumeData = formattedDates.map((date, i) => ({
        x: date,
        y: numericVolumesIn張[i]
    }));

    const maxVol = numericVolumesIn張.length > 0 ? Math.max(...numericVolumesIn張) * 3 : 100;

    stockChart = new Chart(ctx, {
        data: {
            datasets: [
                {
                    type: 'candlestick',
                    label: '股票 K 線',
                    data: candlestickData,
                    color: {
                        up: '#ef4444',
                        down: '#22c55e',
                        unchanged: '#94a3b8'
                    },
                    borderColor: {
                        up: '#ef4444',
                        down: '#22c55e',
                        unchanged: '#94a3b8'
                    },
                    yAxisID: 'y',
                    order: 1      
                },
                {
                    type: 'bar',
                    label: '成交張數 (張)', 
                    data: volumeData, 
                    backgroundColor: 'rgba(148, 163, 184, 0.25)', 
                    hoverBackgroundColor: 'rgba(56, 189, 248, 0.4)',
                    barPercentage: 0.8,
                    yAxisID: 'y1', 
                    order: 2       
                }
            ]
        },
        plugins: [ChartDataLabels], 
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { 
                mode: 'index',         
                intersect: false       
            },
            scales: {
                y: { 
                    type: 'linear',
                    display: true,
                    position: 'left',
                    beginAtZero: false, 
                    min: Math.max(0, priceMin),
                    max: priceMax,
                    grid: { color: '#334155' }, 
                    ticks: { color: '#94a3b8' },
                    title: { display: true, text: '價格 (TWD)', color: '#94a3b8' }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    beginAtZero: true,  
                    grid: { display: false }, 
                    ticks: { 
                        color: '#64748b',
                        callback: function(value) { return value.toLocaleString(); } 
                    },
                    title: { display: true, text: '成交量 (張)', color: '#64748b' },
                    max: maxVol
                },
                x: { 
                    type: 'timeseries',
                    time: {
                        unit: 'day',
                        displayFormats: { day: 'MM/dd' }
                    },
                    grid: { display: false },
                    ticks: { 
                        color: '#94a3b8', 
                        maxTicksLimit: 10,
                        source: 'data' 
                    } 
                }
            },
            plugins: {
                datalabels: { display: false },
                legend: { display: true, labels: { color: '#94a3b8' } },
                tooltip: {
                    enabled: true,
                    callbacks: {
                        label: function(context) {
                            if (context.dataset.type === 'candlestick') {
                                const raw = context.raw || {};
                                return [
                                    ` 開盤: $${raw.o || 0}`,
                                    ` 最高: $${raw.h || 0}`,
                                    ` 最低: $${raw.l || 0}`,
                                    ` 收盤: $${raw.c || 0}`
                                ];
                            } else {
                                return ` 成交張數: ${(context.parsed.y || 0).toLocaleString()} 張`;
                            }
                        }
                    }
                }
            }
        }
    });
}

/**
 * ============================================================================
 * 自選股功能模組 (Watchlist Feature Module)
 * ============================================================================
 */
function updateFavoriteIcon(isFavorite) {
    const btn = document.getElementById('addWatchlistBtn');
    if (!btn) return;
    if (isFavorite) {
        btn.style.color = '#ef4444';
        btn.style.webkitTextStroke = '0px';
        btn.title = '移除自選股';
    } else {
        btn.style.color = 'transparent';
        btn.style.webkitTextStroke = '2px #ffffff';
        btn.title = '加入自選股';
    }
}

async function checkFavoriteStatus(code) {
    try {
        const res = await fetch(`http://localhost:8080/api/favorites`);
        if (!res.ok) return;
        const favorites = await res.json();
        const isFav = favorites.some(fav => fav.stock.stockId === code);
        updateFavoriteIcon(isFav);
    } catch (e) {
        console.error("無法取得自選股狀態:", e);
    }
}

async function loadWatchlist() {
    const container = document.querySelector('.watchlist-card div');
    if (container) {
        container.innerHTML = `<div style="text-align: center; padding: 20px; color: #94a3b8;">載入自選股中...</div>`;
    }
    
    try {
        const res = await fetch(`http://localhost:8080/api/favorites`);
        if (!res.ok) throw new Error("無法取得自選股資料");
        const favorites = await res.json();
        renderWatchlist(favorites);
    } catch (e) {
        console.error("載入自選股失敗:", e);
        if (container) {
            container.innerHTML = `<div style="text-align: center; padding: 20px; color: #f87171;">❌ 載入自選股失敗: ${e.message}</div>`;
        }
    }
}

function renderWatchlist(favorites) {
    const container = document.querySelector('.watchlist-card div');
    if (!container) return;

    if (favorites.length === 0) {
        container.innerHTML = `
            <div style="margin-top: 20px; text-align: center; padding: 40px; color: #64748b;">
                <span style="font-size: 3em; display: block; margin-bottom: 10px;">⭐</span>
                暫無自選股資料，請先在上方搜尋股票並點擊 ❤ 加入自選。
            </div>
        `;
        return;
    }

    let html = `
        <table class="watchlist-table">
            <thead>
                <tr>
                    <th>股票代碼</th>
                    <th>股票名稱</th>
                    <th>目標價 (TWD)</th>
                    <th>備忘錄</th>
                    <th>加入時間</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody>
    `;

    favorites.forEach(fav => {
        const addedDate = new Date(fav.addedAt).toLocaleString('zh-TW', { hour12: false });
        const targetPriceDisplay = fav.targetPrice !== null && fav.targetPrice !== undefined ? fav.targetPrice : '--';
        const memoDisplay = fav.memo ? fav.memo : '';
        
        html += `
            <tr id="fav-row-${fav.stock.stockId}">
                <td style="font-weight: 700; color: #38bdf8;">${fav.stock.stockId}</td>
                <td>${fav.stock.stockName}</td>
                <td class="target-price-cell">
                    <span class="view-mode">${targetPriceDisplay}</span>
                    <input type="number" step="0.1" class="edit-mode watchlist-input" value="${fav.targetPrice || ''}" style="display: none; width: 100px;">
                </td>
                <td class="memo-cell">
                    <span class="view-mode">${memoDisplay}</span>
                    <input type="text" class="edit-mode watchlist-input" value="${fav.memo || ''}" style="display: none; width: 180px;">
                </td>
                <td style="color: #64748b; font-size: 0.9em;">${addedDate}</td>
                <td>
                    <button class="action-btn btn-view" onclick="viewFavorite('${fav.stock.stockId}')">查看</button>
                    <button class="action-btn btn-edit edit-btn" onclick="toggleEditRow('${fav.stock.stockId}')">編輯</button>
                    <button class="action-btn save-btn" onclick="saveFavoriteRow('${fav.stock.stockId}')" style="display: none; background: rgba(52, 211, 153, 0.15); color: #34d399; border: 1px solid rgba(52, 211, 153, 0.3);">儲存</button>
                    <button class="action-btn btn-delete delete-btn" onclick="deleteFavoriteRow('${fav.stock.stockId}')">刪除</button>
                </td>
            </tr>
        `;
    });

    html += `
            </tbody>
        </table>
    `;

    container.innerHTML = html;
}

function viewFavorite(stockId) {
    showDashboardView();
    document.getElementById('navWatchlist').classList.remove('active');
    document.getElementById('navAiReport').classList.remove('active');
    document.getElementById('navMarketOverview').classList.add('active');
    
    document.getElementById('stockSearch').value = stockId;
    fetchStockData(stockId);
}

function toggleEditRow(stockId) {
    const row = document.getElementById(`fav-row-${stockId}`);
    if (!row) return;
    
    const viewElements = row.querySelectorAll('.view-mode');
    const editElements = row.querySelectorAll('.edit-mode');
    const editBtn = row.querySelector('.edit-btn');
    const saveBtn = row.querySelector('.save-btn');
    
    viewElements.forEach(el => el.style.display = 'none');
    editElements.forEach(el => el.style.display = 'inline-block');
    
    editBtn.style.display = 'none';
    saveBtn.style.display = 'inline-block';
}

async function saveFavoriteRow(stockId) {
    const row = document.getElementById(`fav-row-${stockId}`);
    if (!row) return;
    
    const targetPriceInput = row.querySelector('.target-price-cell input').value;
    const memoInput = row.querySelector('.memo-cell input').value;
    
    const targetPrice = targetPriceInput === '' ? null : parseFloat(targetPriceInput);
    const memo = memoInput;

    try {
        const res = await fetch(`http://localhost:8080/api/favorites/${stockId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                memo: memo,
                targetPrice: targetPrice
            })
        });
        
        if (!res.ok) throw new Error("更新失敗");
        const data = await res.json();
        
        if (data.success) {
            row.querySelector('.target-price-cell .view-mode').innerText = targetPrice !== null ? targetPrice : '--';
            row.querySelector('.memo-cell .view-mode').innerText = memo;
            
            const viewElements = row.querySelectorAll('.view-mode');
            const editElements = row.querySelectorAll('.edit-mode');
            const editBtn = row.querySelector('.edit-btn');
            const saveBtn = row.querySelector('.save-btn');
            
            viewElements.forEach(el => el.style.display = 'inline-block');
            editElements.forEach(el => el.style.display = 'none');
            
            editBtn.style.display = 'inline-block';
            saveBtn.style.display = 'none';
        } else {
            alert("更新失敗: " + (data.error || "未知錯誤"));
        }
    } catch (e) {
        console.error("更新自選股失敗:", e);
        alert("更新失敗: " + e.message);
    }
}

async function deleteFavoriteRow(stockId) {
    if (!confirm(`確定要將股票 ${stockId} 從自選清單中刪除嗎？`)) {
        return;
    }
    
    try {
        const res = await fetch(`http://localhost:8080/api/favorites/${stockId}`, {
            method: 'DELETE'
        });
        if (!res.ok) throw new Error("刪除失敗");
        const data = await res.json();
        
        if (data.success) {
            if (stockId === currentStockCode) {
                updateFavoriteIcon(false);
            }
            loadWatchlist();
        } else {
            alert("刪除失敗: " + (data.error || "未知錯誤"));
        }
    } catch (e) {
        console.error("刪除自選股失敗:", e);
        alert("刪除失敗: " + e.message);
    }
}

/**
 * ============================================================================
 * 🔥 核心新增：熱門股票抓取與渲染模組 (Live Trending Stocks Module)
 * ============================================================================
 */
async function fetchLiveTrendingStocks() {
    // 1. 先顯示載入中提示
    const setListLoading = (id) => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = `<li style="color: #64748b; text-align: center; cursor: default; background: transparent;">即時爬取分析中...</li>`;
    };
    
    setListLoading('twseVolumeList');
    setListLoading('twsePriceList');
    setListLoading('tpexVolumeList');
    setListLoading('tpexPriceList');

    try {
        // 💡 向 Python gemini.py (Port 5000) 請求熱門股票數據
        const res = await fetch(`http://127.0.0.1:5000/api/market/trending_stocks?_t=${new Date().getTime()}`);
        if (!res.ok) throw new Error("無法連接熱門股票服務");
        
        const data = await res.json();
        
        if (data.success) {
            // 渲染上市 (TWSE)
            renderTrendingList('twseVolumeList', data.twse.volume, '張');
            renderTrendingList('twsePriceList', data.twse.price, '元');
            
            // 渲染上櫃 (TPEx)
            renderTrendingList('tpexVolumeList', data.tpex.volume, '張');
            renderTrendingList('tpexPriceList', data.tpex.price, '元');
        } else {
            throw new Error(data.error || "抓取失敗");
        }
    } catch (e) {
        console.error("爬取熱門股票失敗:", e);
        const setListError = (id) => {
            const el = document.getElementById(id);
            if (el) el.innerHTML = `<li style="color: #f87171; text-align: center; cursor: default; background: transparent;">❌ 資料載入失敗</li>`;
        };
        setListError('twseVolumeList');
        setListError('twsePriceList');
        setListError('tpexVolumeList');
        setListError('tpexPriceList');
    }
}

// 動態渲染 HTML 清單的輔助函式
function renderTrendingList(elementId, stockList, unit) {
    const listEl = document.getElementById(elementId);
    if (!listEl) return;

    if (!stockList || stockList.length === 0) {
        listEl.innerHTML = `<li style="color: #64748b; text-align: center; cursor: default; background: transparent;">今日暫無數據</li>`;
        return;
    }

    listEl.innerHTML = stockList.map((stock, index) => {
        const valDisplay = unit === '張' 
            ? `${stock.volume.toLocaleString()} 張` 
            : `$${stock.price.toLocaleString()}`;

        return `
            <li onclick="analyzeFromTrending('${stock.code}')">
                <div>
                    <span style="color: #38bdf8; font-weight: bold; margin-right: 10px;">#${index + 1}</span>
                    <span class="trend-name">${stock.name}</span>
                    <span class="trend-code">${stock.code}</span>
                </div>
                <div style="display: flex; align-items: center; gap: 15px;">
                    <span style="color: #34d399; font-weight: bold;">${valDisplay}</span>
                    <button class="trend-action-btn">分析</button>
                </div>
            </li>
        `;
    }).join('');
}

/**
 * ============================================================================
 * 💡 熱門股票純前端跳轉與分析邏輯
 * ============================================================================
 */
function analyzeFromTrending(code) {
    showDashboardView();
    document.querySelectorAll('.nav-links li').forEach(li => li.classList.remove('active'));
    document.getElementById('navMarketOverview').classList.add('active');
    
    document.getElementById('stockSearch').value = code;
    fetchStockData(code);
}