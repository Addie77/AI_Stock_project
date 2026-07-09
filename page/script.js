/**
 * ============================================================================
 * 全域變數定義 (Global Variables)
 * ============================================================================
 */
let stockChart;          // 儲存 Chart.js 的圖表實例（Instance），以便後續銷毀並重建圖表
let currentStockCode = ''; // 💡 核心修正：將初始追蹤代碼設為空字串，完全移除預設股票

/**
 * ============================================================================
 * 網頁初始化與事件監聽 (Initialization & Event Listeners)
 * ============================================================================
 */
document.addEventListener('DOMContentLoaded', () => {
    // 💡 核心修正：拔除所有預設載入與 localStorage 讀取邏輯，維持網頁初始待命狀態
    initDashboardState();
    
    // 監聽搜尋框的按鍵事件
    document.getElementById('stockSearch').addEventListener('keypress', (e) => {
        // 當使用者在搜尋框內按下 'Enter' 鍵時，觸發新股票的資料讀取流
        if (e.key === 'Enter') {
            const inputCode = e.target.value.trim();
            if (inputCode) {
                // 如果在自選股頁面進行搜尋，自動切回市場總覽以利觀看圖表
                showDashboardView();
                fetchStockData(inputCode);
            }
        }
    });

    // 監聽「生成 AI 智能建議報告」按鈕的點擊事件
    document.getElementById('generateAiBtn').addEventListener('click', () => {
        // 安全防禦機制：如果使用者還沒搜尋股票就按按鈕，進行提示攔截
        if (!currentStockCode) {
            alert("請先在上方搜尋股票代碼，再生成 AI 報告。");
            return;
        }
        // 傳入目前全域追蹤的股票代碼，向後端第二階段 API 請求大語言模型分析
        fetchAiReport(currentStockCode);
    });

    /**
     * 💡 互動功能：點擊左側「AI 報告」選單自動平滑跳轉至對應區塊
     */
    document.getElementById('navAiReport').addEventListener('click', () => {
        // 確保儀表板主內容是顯示的
        showDashboardView();

        const aiSection = document.getElementById('aiReportSection');
        if (aiSection) {
            // 使用原生 Web API 進行平滑（Smooth）垂直滾動，並對齊區塊頂端
            aiSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        
        // 動態切換側邊欄的 CSS 高亮樣式 (Active Class Tab)
        document.getElementById('navMarketOverview').classList.remove('active');
        document.getElementById('navWatchlist').classList.remove('active'); // 新增：移除自選股高亮
        document.getElementById('navAiReport').classList.add('active');
    });

    /**
     * 💡 互動功能：點擊左側「市場總覽」回到網頁最頂端
     */
    document.getElementById('navMarketOverview').addEventListener('click', () => {
        // 確保儀表板主內容是顯示的
        showDashboardView();

        // 平滑滾動回瀏覽器視窗最頂部 (Y 軸 0 的位置)
        window.scrollTo({ top: 0, behavior: 'smooth' });
        
        document.getElementById('navAiReport').classList.remove('active');
        document.getElementById('navWatchlist').classList.remove('active'); // 新增：移除自選股高亮
        document.getElementById('navMarketOverview').classList.add('active');
    });

    /**
     * 💡 新增互動功能：點擊左側「自選股」切換至自選頁面
     */
    document.getElementById('navWatchlist').addEventListener('click', () => {
        // 隱藏原本的市場總覽與 AI 報告，顯示自選股區塊
        document.getElementById('mainDashboardViews').style.display = 'none';
        document.getElementById('watchlistSection').style.display = 'block';
        window.scrollTo({ top: 0, behavior: 'smooth' });

        // 切換側邊欄高亮
        document.getElementById('navMarketOverview').classList.remove('active');
        document.getElementById('navAiReport').classList.remove('active');
        document.getElementById('navWatchlist').classList.add('active');

        // 💡 載入自選股清單
        if (typeof loadWatchlist === 'function') {
            loadWatchlist();
        }
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
 * 💡 新增：輔助函式，切換回主儀表板畫面
 */
function showDashboardView() {
    document.getElementById('mainDashboardViews').style.display = 'flex';
    document.getElementById('watchlistSection').style.display = 'none';
}

/**
 * 💡 新增：初始化儀表板待命狀態 UI 表現
 * 作用：當網頁第一時間打開時，呈現乾淨且具備導引性的提示文字
 */
function initDashboardState() {
    document.getElementById('displayName').innerText = "請搜尋股票代碼";
    document.getElementById('sentFill').style.width = '0%';
    document.getElementById('sentVal').innerText = "0 / 100";
    document.getElementById('aiSummary').innerText = "等待搜尋股票數據...";
    
    // 重設最愛心型圖示
    if (typeof updateFavoriteIcon === 'function') {
        updateFavoriteIcon(false);
    }
    
    // 如果有殘留的舊圖表，將其銷毀以釋放資源
    if (stockChart) {
        stockChart.destroy();
        stockChart = null;
    }
}

/**
 * ============================================================================
 * 第一階段：抓取基礎資料 (歷史價格、本地端 FinBERT 情感分數)
 * ============================================================================
 */
async function fetchStockData(code) {
    // 同步更新當前全域控制的股票代碼，確保第二階段按鈕能拿到正確的代碼
    currentStockCode = code;
    
    // 💡 核心修正：移除 localStorage.setItem，不將資料寫入本地儲存，確保每次重新整理都是乾淨重置
    
    // 重設底部的 AI 智能建議報告區塊，將其還原為初始待命狀態，提供更好的 UI 體驗
    document.getElementById('aiSummary').innerText = "請點擊上方按鈕，以生成基於 3 個月歷史數據的 AI 技術面分析建議。";
    const aiAdvice = document.getElementById('aiAdvice');
    aiAdvice.style.display = 'none'; // 隱藏前次的 AI 建議框
    aiAdvice.innerHTML = '';        // 清空前次的 AI 內容

    try {
        // 發送 HTTP GET 請求至後端第一階段 API (此階段純粹運行爬蟲與本地端權重模型，速度極快)
        const response = await fetch(`http://127.0.0.1:5000/api/analyze?code=${code}`);
        const data = await response.json();
        
        // 檢查 HTTP 狀態碼，如果後端回傳 404 等非 ok 狀態，直接拋出錯誤進入 catch
        if (!response.ok) throw new Error(data.error);

        // 【更新 UI 元素 1】：動態呈現股票名稱與代碼
        document.getElementById('displayName').innerText = `${data.name} (${code})`;
        
        // 【更新 UI 元素 2】：控制 CSS Width 屬性，觸發彩色情感進度條（Sentiment Bar）的平滑動畫
        document.getElementById('sentFill').style.width = data.sentiment_score + '%'; 
        
        // 【更新 UI 元素 3】：更新數字文字顯示
        document.getElementById('sentVal').innerText = data.sentiment_score + " / 100";
        
        // 將後端回傳的歷史收盤價與交易量陣列同步傳入繪圖引擎
        renderChart(data.history_dates, data.history_prices, data.history_volumes);
        
        // 💡 檢查自選股狀態以更新心型按鈕
        if (typeof checkFavoriteStatus === 'function') {
            checkFavoriteStatus(code);
        }
        
    } catch (error) {
        // 錯誤控制安全機制：如遇網路斷線或無此股票，如實呈年在網頁畫面上並恢復初始 UI
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

    // 更新 UI 為載入中狀態
    aiSummary.innerText = "🚀 正在啟動深度新聞分析任務 (預計耗時較長，請勿關閉視窗)...";
    aiAdvice.style.display = 'none'; 
    btn.disabled = true;             

    try {
        // --- 階段 1：啟動任務 ---
        const startRes = await fetch(`http://127.0.0.1:5000/api/sync_news?code=${code}`, { cache: 'no-store' });
        const startData = await startRes.json();
        if (!startRes.ok) throw new Error(startData.error || "啟動任務失敗");

        // 智慧判斷：如果後端回傳已完成 (快取命中)，直接更新 UI 並跳過輪詢
        if (startData.status === 'completed') {
            console.log("🚀 快取命中！直接載入今日分析數據。");
            document.getElementById('sentFill').style.width = startData.avg_sentiment + '%'; 
            document.getElementById('sentVal').innerText = startData.avg_sentiment + " / 100";
            // 模擬已完成的結果供階段 3 使用
            var finalSyncResult = {
                avg_sentiment: startData.avg_sentiment,
                ai_summary: startData.ai_summary || "今日報告已儲存。"
            };
        } else {
            // --- 階段 2：狀態輪詢 (Polling) ---
            let isFinished = false;
            var finalSyncResult = null; // 改用 var 提升作用域
            let waitTime = 0;

            while (!isFinished) {
                // 每隔 10 秒詢問一次
                await new Promise(resolve => setTimeout(resolve, 10000));
                waitTime += 10;
                aiSummary.innerText = `⏳ 正在爬取新聞並進行 AI 語意分析... (已耗時 ${waitTime} 秒)\n這可能需要 5-10 分鐘，您可以先查看其他分頁。`;

                const statusRes = await fetch(`http://127.0.0.1:5000/api/check_status?code=${code}&_t=${new Date().getTime()}`, { cache: 'no-store' });
                const statusData = await statusRes.json();

                if (statusData.status === 'completed') {
                    isFinished = true;
                    finalSyncResult = statusData;
                    // 即時更新 UI 上的情感分數
                    document.getElementById('sentFill').style.width = statusData.avg_sentiment + '%'; 
                    document.getElementById('sentVal').innerText = statusData.avg_sentiment + " / 100";
                } else if (statusData.status === 'error') {
                    throw new Error(statusData.message || "背景分析發生錯誤");
                }
            }
        }

        // --- 階段 3：新聞分析完畢，執行最終 Gemini 技術面報告 ---
        aiSummary.innerText = "✅ 新聞分析完成！正在調用 Gemini 生成最終實戰建議報告...";
        const aiResponse = await fetch(`http://127.0.0.1:5000/api/generate_ai?code=${code}`, { cache: 'no-store' });
        const aiResult = await aiResponse.json();

        if (!aiResponse.ok) throw new Error(aiResult.error || "AI 報告生成失敗");

        // 渲染最終報告：拆分為兩個獨立、美觀的方框
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
        console.log("✨ 輪詢式綜合 AI 報告渲染成功！");
        
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
 * 數據視覺化核心：Chart.js 長週期雙 Y 軸混合圖表渲染引擎 (張數換算版)
 * ============================================================================
 */
function renderChart(dates, prices, volumes) {
    const ctx = document.getElementById('stockChart').getContext('2d');
    if (stockChart) stockChart.destroy();

    // 強制將收盤價轉為純數字陣列
    const numericPrices = prices.map(Number);
    
    // 💡 核心修正：將官方的「股數」數據，在前端實時除以 1000，完全真實換算為「張數」
    const numericVolumesIn張 = volumes.map(v => Math.round(Number(v) / 1000));

    stockChart = new Chart(ctx, {
        data: {
            labels: dates, // 橫軸共享 3 個月交易日期
            datasets: [
                {
                    // --- 數據集 1：收盤價折線圖 ---
                    type: 'line',
                    label: '歷史收盤價 (TWD)',
                    data: numericPrices,
                    borderColor: '#38bdf8',
                    backgroundColor: 'rgba(56, 189, 248, 0.03)', 
                    borderWidth: 2.5,
                    fill: true,
                    tension: 0.15,
                    pointRadius: 0, 
                    pointHoverRadius: 6,
                    pointHoverBackgroundColor: '#4ade80',
                    yAxisID: 'y',
                    order: 1      
                },
                {
                    // --- 數據集 2：成交量柱狀圖 ---
                    type: 'bar',
                    label: '成交張數 (張)', // 💡 UI 優化：標籤改為張數
                    data: numericVolumesIn張, // 💡 使用換算為「張」的數字陣列
                    backgroundColor: 'rgba(148, 163, 184, 0.15)', 
                    hoverBackgroundColor: 'rgba(56, 189, 248, 0.4)',
                    barPercentage: 0.85,
                    yAxisID: 'y1', // 對接右側 Y 軸 (交易量軸)
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
                // 左側 Y 軸：主導收盤價
                y: { 
                    type: 'linear',
                    display: true,
                    position: 'left',
                    beginAtZero: false, 
                    grid: { color: '#334155' }, 
                    ticks: { color: '#94a3b8' },
                    title: { display: true, text: '價格 (TWD)', color: '#94a3b8' }
                },
                // 💡 右側 Y 軸：主導成交量（張數）
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    beginAtZero: true,  
                    grid: { display: false }, 
                    ticks: { 
                        color: '#64748b',
                        // 格式化右側軸的數字為千分位顯示
                        callback: function(value) { return value.toLocaleString(); } 
                    },
                    title: { display: true, text: '成交量 (張)', color: '#64748b' }, // 💡 座標軸標題改為「張」
                    // 強迫交易量的最大值翻倍，讓柱狀圖維持在畫面的下半部 50%
                    max: Math.max(...numericVolumesIn張) * 2
                },
                x: { 
                    grid: { display: false },
                    ticks: { color: '#94a3b8', maxTicksLimit: 8 } 
                }
            },
            plugins: {
                datalabels: { display: false },
                legend: { display: true, labels: { color: '#94a3b8' } },
                tooltip: {
                    enabled: true,
                    callbacks: {
                        // 💡 提示框優化：當滑鼠移入時，Tooltip 會動態加上個別dataset的正確單位（元 vs 張）
                        label: function(context) {
                            let label = context.dataset.label || '';
                            // 移除原本標籤裡的括號單位，重新漂亮地組合
                            if (context.datasetIndex === 0) {
                                return ` 收盤價: $${context.parsed.y.toLocaleString()} TWD`;
                            } else {
                                return ` 成交張數: ${context.parsed.y.toLocaleString()} 張`;
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

// 更新心型按鈕樣式
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

// 檢查當前股票是否在自選股清單中
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

// 載入所有自選股資料
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

// 渲染自選股表格
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

// 切換至詳細儀表板檢視該股票
function viewFavorite(stockId) {
    showDashboardView();
    document.getElementById('navWatchlist').classList.remove('active');
    document.getElementById('navAiReport').classList.remove('active');
    document.getElementById('navMarketOverview').classList.add('active');
    
    // 清空並重新載入搜尋與資料
    document.getElementById('stockSearch').value = stockId;
    fetchStockData(stockId);
}

// 切換特定行的編輯/檢視模式
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

// 儲存編輯結果
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

// 刪除自選股紀錄
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