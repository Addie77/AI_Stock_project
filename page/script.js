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
    // 網頁 DOM 樹載入完成後，執行初始化的預設載入動作 (台積電 2330)
    fetchStockData('2330'); 
    
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
 * 第二階段：點擊按鈕生成雲端 AI 投顧級技術面深度分析報告
 * ============================================================================
 */
async function fetchAiReport(code) {
    const aiSummary = document.getElementById('aiSummary');
    const aiAdvice = document.getElementById('aiAdvice');
    const btn = document.getElementById('generateAiBtn');

    // 更新 UI 為載入中狀態（Loading State）
    aiSummary.innerText = "🧠 AI 正在研讀 3 個月歷史數據形態，並撰寫報告中...";
    aiAdvice.style.display = 'none'; // 隱藏前次內容
    btn.disabled = true;             // 💡 關鍵：禁用按鈕防止使用者在連線期間重複點擊，造成 API 請求溢出

    try {
        // 發送 HTTP GET 請求至後端第二階段 API (此處會正式調用雲端大語言模型 gemini-2.5-flash)
        const response = await fetch(`http://127.0.0.1:5000/api/generate_ai?code=${code}`);
        const data = await response.json();
        
        // 網路層防禦：若後端回傳錯誤（如 API 金鑰過期），拋出錯誤進入 catch
        if (!response.ok) throw new Error(data.error || "未知的系統錯誤");

        // 【渲染真實報告 1】：動態填入經技術形態學分析後的詳細大篇幅總結
        aiSummary.innerText = data.analysis_summary;
        
        // 【渲染真實報告 2】：動態填入具體的實戰操作、資金配比、支撐與壓力位策略建議
        aiAdvice.innerHTML = `💡 基於歷史走勢之操作建議：<br>${data.advice}`;
        
        // 將建議區塊從 display:none 切換為 block 展開呈現
        aiAdvice.style.display = 'block'; 
        
    } catch (error) {
        console.error("AI Error:", error);
        // 若 AI 生成遭遇任何系統級崩潰，如實向使用者報錯，確保資料真實不造假
        aiSummary.innerText = `❌ 報告生成失敗：${error.message}`;
        aiAdvice.style.display = 'none';
    } finally {
        // 無論連線成功或失敗，最後都必須解除按鈕禁用狀態，恢復可操作性
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