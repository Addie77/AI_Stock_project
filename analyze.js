let myChart; // 儲存圖表

async function startSearch() {
    const code = document.getElementById('stockSearch').value;
    if (!code) return alert("請輸入代碼");

    // 顯示載入狀態
    document.getElementById('ai-report-content').innerText = "Gemini 正在分析中，請稍候...";
    
    try {
        // 1. 向 Python 後端請求分析
        // 請檢查 script.js 裡面的這一行
const response = await fetch(`http://127.0.0.1:5000/api/analyze?code=${code}`);
        const data = await response.json();

        if (data.error) {
            alert("搜尋不到該股票");
            return;
        }

        // 2. 更新網頁文字與標籤
        document.getElementById('ai-report-content').innerText = data.analysis_summary;
        document.getElementById('ai-score-val').innerText = data.sentiment_score;
        
        const tag = document.getElementById('ai-status-tag');
        tag.innerText = data.sentiment_tag;
        tag.className = data.sentiment_score >= 50 ? "tag positive" : "tag negative";

        // 3. 更新情緒條動畫
        document.getElementById('sentFill').style.width = data.sentiment_score + '%';

        // 4. 更新 Chart.js 圖表 (預測線)
        updateChart(data.prediction_price);

    } catch (error) {
        console.error("連線後端失敗:", error);
        alert("後端伺服器未啟動，請執行 python app.py");
    }
}

// 監聽 Enter 鍵
document.getElementById('stockSearch').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') startSearch();
});