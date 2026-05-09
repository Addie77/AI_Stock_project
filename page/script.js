/**
 * 全域變數定義
 */
let stockChart; // 用來儲存 Chart.js 的實例，確保在更新資料前可以銷毀舊圖表，避免重複渲染

/**
 * 當網頁 DOM 結構載入完成後執行的初始化動作
 */
document.addEventListener('DOMContentLoaded', function() {
    // 1. 頁面啟動時，自動抓取預設股票 (台積電 2330) 的資料
    fetchStockData('2330'); 

    // 2. 獲取搜尋輸入框元件
    const searchInput = document.getElementById('stockSearch');
    
    // 3. 監聽搜尋框的按鍵事件
    searchInput.addEventListener('keypress', function(e) {
        // 如果使用者按下 Enter 鍵
        if (e.key === 'Enter') {
            const code = e.target.value.trim(); // 取得輸入值並去除空白
            if (code) {
                fetchStockData(code); // 執行 API 抓取函式
            }
        }
    });
});

/**
 * 核心功能：從 Flask 後端 (Port 5000) 抓取分析資料
 * @param {string} code - 股票代碼 (例如: 2330)
 */
async function fetchStockData(code) {
    // 取得用於顯示 AI 報告內容的 HTML 標籤
    const aiSummary = document.getElementById('aiSummary');
    const aiAdvice = document.getElementById('aiAdvice');
    
    // 在發送請求前，先顯示「載入中」提示
    if (aiSummary) aiSummary.innerText = "Gemini AI 正在分析數據中...";
    if (aiAdvice) aiAdvice.innerText = "";

    try {
        // 發送異步請求 (Fetch) 到後端 API
        // 注意：這裡使用完整的 URL 以解決跨網域 (CORS) 連線問題
        const response = await fetch(`http://127.0.0.1:5000/api/analyze?code=${code}`);
        
        // 解析後端回傳的 JSON 格式資料
        const data = await response.json();

        // 如果 HTTP 狀態碼不是 200~299，代表後端報錯 (如 404 或 429)
        if (!response.ok) {
            throw new Error(data.error || "連線出錯");
        }

        // 成功取得資料後，呼叫更新 UI 儀表板的函式
        updateDashboard(code, data);

    } catch (error) {
        // 錯誤處理：印出詳細錯誤到 Console 並彈出警告視窗
        console.error("Error:", error);
        alert("分析出錯: " + error.message);
        
        // 若發生錯誤，修改介面提示文字
        if (aiSummary) aiSummary.innerText = "暫時無法取得分析資料。";
    }
}

/**
 * 更新網頁 UI 儀表板各項元件
 * @param {string} code - 股票代碼
 * @param {object} data - 後端回傳的分析資料結果
 */
function updateDashboard(code, data) {
    // 獲取 Canvas 繪圖上下文
    const ctx = document.getElementById('stockChart').getContext('2d');
    
    // 如果舊圖表已存在，必須銷毀它，否則滑鼠移過時會閃爍
    if (stockChart) stockChart.destroy();

    // 1. 更新頂部顯示的股票名稱與代碼
    document.getElementById('displayName').innerText = `${data.name} (${code})`;
    
    // 2. 更新圖表標題
    document.getElementById('chartTitle').innerText = `${data.name} 價格趨勢與 AI 預測`;

    // 3. 更新市場情感長條圖
    const score = data.sentiment_score; // 情感分數 (0-100)
    document.getElementById('sentFill').style.width = score + '%'; // 修改 CSS 寬度
    document.getElementById('sentVal').innerText = `${score} / 100`; // 顯示文字分數

    // 4. 更新明日上漲機率圓環圖 (SVG 操控)
    // 利用控制 stroke-dasharray 來達成圓環進度條效果
    document.getElementById('probCircle').style.strokeDasharray = `${score}, 100`;
    document.getElementById('probText').textContent = `${score}%`;

    // 5. 更新右側 AI 分析文字區塊
    document.getElementById('aiSummary').innerText = data.analysis_summary;
    document.getElementById('aiAdvice').innerText = "💡 專家建議：" + data.advice;

    // 6. 重新渲染 Chart.js 折線圖
    renderChart(ctx, data.current_price, data.prediction_price);
}

/**
 * 使用 Chart.js 繪製價格趨勢折線圖
 * @param {CanvasRenderingContext2D} ctx - 畫布上下文
 * @param {number} realPrice - 真實的今日收盤價
 * @param {Array} predPrices - AI 預測的三天價格陣列 [D1, D2, D3]
 */
function renderChart(ctx, realPrice, predPrices) {
    // X 軸標籤
    const labels = ['今日', '預測 D1', '預測 D2', '預測 D3'];
    
    // 整理數據點：將今日價格與未來三天價格合併成一個陣列
    const dataPoints = [realPrice, ...predPrices];

    // 創建新圖表實例
    stockChart = new Chart(ctx, {
        type: 'line', // 圖表類型：折線圖
        data: {
            labels: labels,
            datasets: [{
                label: '股價預測 (TWD)',
                data: dataPoints,
                borderColor: '#38bdf8', // 線條顏色 (天藍色)
                backgroundColor: 'rgba(56, 189, 248, 0.2)', // 填滿區域顏色
                borderWidth: 3,
                // 不同點的背景顏色：今日用藍色，預測點用黃色
                pointBackgroundColor: ['#38bdf8', '#fbbf24', '#fbbf24', '#fbbf24'],
                fill: true, // 是否填滿線條下方區域
                tension: 0.4 // 線條彎曲程度 (貝茲曲線)
            }]
        },
        options: {
            responsive: true, // 自動縮放
            maintainAspectRatio: false, // 允許自定義高度
            scales: {
                y: { 
                    grid: { color: '#334155' }, // Y 軸網格線顏色
                    ticks: { color: '#94a3b8' } // Y 軸文字顏色
                },
                x: { 
                    grid: { display: false }, // 不顯示 X 軸垂直網格線
                    ticks: { color: '#94a3b8' } // X 軸文字顏色
                }
            }
        }
    });
}