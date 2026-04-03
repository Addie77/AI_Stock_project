const ctx = document.getElementById('stockChart').getContext('2d');

new Chart(ctx, {
    type: 'line',
    data: {
        labels: ['週一', '週二', '週三', '週四', '週五', '預測1', '預測2'],
        datasets: [{
            label: '實際股價',
            data: [600, 610, 605, 620, 630, null, null],
            borderColor: '#38bdf8',
            tension: 0.3
        }, {
            label: 'AI 預測路徑',
            data: [null, null, null, null, 630, 645, 650], // 從最後一個點銜接
            borderColor: '#fbbf24',
            borderDash: [5, 5],
            tension: 0.3
        }]
    },
    options: {
        responsive: true,
        plugins: { legend: { labels: { color: '#f8fafc' } } },
        scales: {
            y: { grid: { color: '#334155' }, ticks: { color: '#9ca3af' } },
            x: { grid: { display: false }, ticks: { color: '#9ca3af' } }
        }
    }
});