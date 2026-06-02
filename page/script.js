/**
 * ============================================================================
 * 全域變數定義 (Global Variables)
 * ============================================================================
 */
let stockChart;          // 儲存 Chart.js 的圖表實例（Instance），以便後續銷毀並重建圖表
let currentStockCode = '2330'; // 追蹤當前使用者選取、瀏覽的股票代碼，預設為台積電

/**
 * ============================================================================
 * 網頁初始化與事件監聽 (Initialization & Event Listeners)
 * ============================================================================
 */
document.addEventListener('DOMContentLoaded', () => {
    // 💡 關鍵優化：從瀏覽器儲存中讀取上次瀏覽的代碼，若無則預設 2330
    const savedCode = localStorage.getItem('lastStockCode') || '2330';
    fetchStockData(savedCode); 
    
    // 監聽搜尋框的按鍵事件
    document.getElementById('stockSearch').addEventListener('keypress', (e) => {
        // 當使用者在搜尋框內按下 'Enter' 鍵時，觸發新股票的資料讀取流
        if (e.key === 'Enter') {
            fetchStockData(e.target.value.trim());
        }
    });

    // 監聽「生成 AI 智能建議報告」按鈕的點擊事件
    document.getElementById('generateAiBtn').addEventListener('click', () => {
        // 傳入目前全域追蹤的股票代碼，向後端第二階段 API 請求大語言模型分析
        fetchAiReport(currentStockCode);
    });

    /**
     * 💡 互動功能：點擊左側「AI 報告」選單自動平滑跳轉至對應區塊
     */
    document.getElementById('navAiReport').addEventListener('click', () => {
        const aiSection = document.getElementById('aiReportSection');
        if (aiSection) {
            // 使用原生 Web API 進行平滑（Smooth）垂直滾動，並對齊區塊頂端
            aiSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        
        // 動態切換側邊欄的 CSS 高亮樣式 (Active Class Tab)
        document.getElementById('navMarketOverview').classList.remove('active');
        document.getElementById('navAiReport').classList.add('active');
    });

    /**
     * 💡 互動功能：點擊左側「市場總覽」回到網頁最頂端
     */
    document.getElementById('navMarketOverview').addEventListener('click', () => {
        // 平滑滾動回瀏覽器視窗最頂部 (Y 軸 0 的位置)
        window.scrollTo({ top: 0, behavior: 'smooth' });
        
        // 動態切換側邊欄高亮
        document.getElementById('navAiReport').classList.remove('active');
        document.getElementById('navMarketOverview').classList.add('active');
    });
});

/**
 * ============================================================================
 * 第一階段：抓取基礎資料 (歷史價格、本地端 FinBERT 情感分數)
 * ============================================================================
 */
async function fetchStockData(code) {
    // 同步更新當前全域控制的股票代碼，確保第二階段按鈕能拿到正確的代碼
    currentStockCode = code;
    // 💡 關鍵：將代碼寫入瀏覽器本地儲存，防止頁面重整後丟失進度
    localStorage.setItem('lastStockCode', code);
    
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
        
        // 【更新 UI 元素 4】：調用繪圖引擎，渲染 3 個月真實歷史價格曲線
        renderChart(data.history_dates, data.history_prices);
        
    } catch (error) {
        // 錯誤控制安全機制：如遇網路斷線或無此股票，如實呈現在網頁畫面上
        console.error("Fetch Error:", error);
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

        // 💡 智慧判斷：如果後端回傳已完成 (快取命中)，直接更新 UI 並跳過輪詢
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
            <!-- 方框 1：新聞消息面總評 (採用天藍色調) -->
            <div style="background: rgba(56, 189, 248, 0.08); border-left: 5px solid #38bdf8; padding: 18px; margin-bottom: 20px; border-radius: 8px;">
                <div style="color: #38bdf8; font-weight: 800; font-size: 1.1em; margin-bottom: 8px; display: flex; align-items: center;">
                    <span style="margin-right: 8px;">📰</span> 新聞消息面深度總評
                </div>
                <div style="color: #e2e8f0; line-height: 1.7; font-size: 0.95em;">
                    ${finalSyncResult.ai_summary}
                </div>
            </div>
            
            <!-- 方框 2：技術面實戰建議 (採用翡翠綠色調) -->
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
 * 數據視覺化核心：Chart.js 長週期圖表渲染引擎
 * ============================================================================
 */
function renderChart(dates, prices) {
    // 取得 HTML 畫布的 2D 繪圖上下文 (Context)
    const ctx = document.getElementById('stockChart').getContext('2d');
    
    // 💡 關鍵記憶體優化：如果舊圖表實例存在，必須先將其徹底銷毀（Destroy），否則滑鼠移入時圖表會重疊閃爍
    if (stockChart) stockChart.destroy();

    // 實例化全新 Line Chart
    stockChart = new Chart(ctx, {
        type: 'line', // 指定圖表類型為折線圖
        data: {
            labels: dates, // 橫軸 (X軸)：帶入後端傳來的 3 個月真實交易日期陣列
            datasets: [{
                label: '歷史收盤價 (TWD)',
                data: prices,  // 縱軸 (Y軸)：帶入後端傳來的 3 個月真實收盤價陣列
                borderColor: '#38bdf8', // 線條顏色設定（科技天藍色）
                backgroundColor: 'rgba(56, 189, 248, 0.05)', // 折線下方漸層填滿區塊的色彩與透明度
                borderWidth: 2.5, // 曲線寬度
                fill: true,       // 啟用下方區塊填滿
                tension: 0.15,    // 微幅降低貝茲曲線彎曲率，防止在大量資料點時線條出現反折失真
                pointRadius: 0,   // 💡 長週期最佳化：平常隱藏資料點上的小圓點，讓整條三個月的線條維持乾淨專業
                pointHoverRadius: 6, // 當滑鼠指針移入該資料點時，小圓點才放大顯現
                pointHoverBackgroundColor: '#4ade80' // 指針移入點顏色改為科技綠
            }]
        },
        plugins: [ChartDataLabels], // 掛載 Datalabels 外掛（避免全域環境找不到外掛時報錯）
        options: {
            responsive: true,          // 啟用自適應寬度，圖表會隨著外層 container 自動撐滿
            maintainAspectRatio: false, // 💡 關鍵：配合 CSS 容器，不強制維持長寬比，確保高度固定 400px
            interaction: { 
                mode: 'index',         // 滑鼠只要對齊垂直線，就會直接觸發該日期節點的焦點
                intersect: false       // 指針不需要百分之百精確指到點上就能觸發提示，優化使用者體驗
            },
            scales: {
                y: { 
                    beginAtZero: false, // 💡 核心設定：股價絕對不能從 0 開始畫，否則數百元的股價波動會被壓縮成一條平線
                    grid: { color: '#334155' }, // 橫向格線色彩（深灰色）
                    ticks: { color: '#94a3b8' }  // 縱軸刻度文字色彩
                },
                x: { 
                    grid: { display: false },    // 關閉橫軸的垂直格線，保持視覺乾淨
                    ticks: { 
                        color: '#94a3b8',
                        maxTicksLimit: 8         // 💡 長週期最佳化：強迫 X 軸最多只抽樣顯示 8 個日期標籤，防止 60 幾天的文字疊在一起變黑底
                    } 
                }
            },
            plugins: {
                datalabels: { 
                    display: false // 💡 長週期最佳化：全面關閉點上的浮動數字，因為 60 幾個字重疊會完全無法閱讀
                },
                legend: { 
                    display: true, // 顯示上方圖例
                    labels: { color: '#94a3b8' } 
                },
                tooltip: {
                    enabled: true, // 啟用懸浮提示框 (Tooltip)
                    callbacks: {
                        // 當滑鼠停在某個節點上時，客製化呈現具備千分位標點與 TWD 單位的精準實價
                        label: function(context) { 
                            return ` 收盤價: $${context.parsed.y.toLocaleString()} TWD`; 
                        }
                    }
                }
            }
        }
    });
}
