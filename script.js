let stockChart; // 用來儲存圖表實例，以便銷毀重建

document.addEventListener('DOMContentLoaded', function() {
    // 初始載入 (預設台積電)
    fetchStockData('2330');

    // 綁定搜尋框事件
    const searchInput = document.getElementById('stockSearch');
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            const code = e.target.value.trim();
            if (code) {
                fetchStockData(code);
            }
        }
    });
});

// 模擬 API 抓取 (未來可換成 fetch)
async function fetchStockData(code) {
    console.log(`正在搜尋股票代碼: ${code}`);
    
    // 這裡模擬不同代碼的數據變化
    const isTsmc = code === '2330';
    const mockData = {
        name: isTsmc ? '台積電' : `股票 ${code}`,
        history: Array.from({length: 5}, () => Math.floor(Math.random() * 500) + 100),
        prediction: Array.from({length: 3}, () => Math.floor(Math.random() * 500) + 100),
        sentiment: Math.floor(Math.random() * 100),
        probability: Math.floor(Math.random() * 100)
    };

    updateDashboard(code, mockData);
}

function updateDashboard(code, data) {
    const ctx = document.getElementById('stockChart').getContext('2d');

    // 關鍵：如果圖表已存在，必須先銷毀，否則會重疊
    if (stockChart) {
        stockChart.destroy();
    }

    // 更新標題
    document.querySelector('.chart-card h3').innerText = `${data.name} (${code}) 趨勢與 AI 預測`;

    // 重新繪製圖表
    stockChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['週一', '週二', '週三', '週四', '週五', '預測 D+1', '預測 D+2', '預測 D+3'],
            datasets: [{
                label: '實際價格',
                data: [...data.history, null, null, null],
                borderColor: '#38bdf8',
                tension: 0.4
            }, {
                label: 'AI 預測',
                data: [null, null, null, null, data.history[4], ...data.prediction],
                borderColor: '#fbbf24',
                borderDash: [6, 4],
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { labels: { color: '#f8fafc' } } },
            scales: {
                y: { grid: { color: '#334155' }, ticks: { color: '#94a3b8' } },
                x: { grid: { display: false }, ticks: { color: '#94a3b8' } }
            }
        }
    });

    // 更新指標動畫
    document.getElementById('sentFill').style.width = data.sentiment + '%';
    document.getElementById('sentVal').innerText = `${data.sentiment} / 100`;
    document.getElementById('probCircle').style.strokeDasharray = `${data.probability}, 100`;
    document.getElementById('probText').textContent = `${data.probability}%`;
}