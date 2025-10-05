
document.addEventListener('DOMContentLoaded', () => {
    // --- 1. Map Initialization (Leaflet + NASA GIBS) ---
    const map = L.map('map', { dragging: true }).setView([39.04, -77.48], 10);

    // Get yesterday's date for the GIBS layer
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const timeString = yesterday.toISOString().split('T')[0];

    // Manually construct the final URL template
    const gibsUrlTemplate = `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/${timeString}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg`;

    L.tileLayer(gibsUrlTemplate, {
        attribution: 'Imagery &copy; NASA GIBS',
        tileSize: 256,
        maxZoom: 9
    }).addTo(map);

    // --- 2. Chart and Sidebar Logic ---
    let rsiHistoryChart, rsiStockChart;

    function createCharts() {
        const historyCtx = document.getElementById('rsi-history-chart').getContext('2d');
        rsiHistoryChart = new Chart(historyCtx, {
            type: 'line',
            data: { labels: ['-4d', '-3d', '-2d', '-1d', 'Today'], datasets: [{ label: 'RSI History', borderColor: '#FFC107', data: [], fill: true, tension: 0.3 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { min: 0, max: 1 } } }
        });

        const stockCtx = document.getElementById('rsi-stock-chart').getContext('2d');
        rsiStockChart = new Chart(stockCtx, {
            type: 'line',
            data: { labels: ['-4d', '-3d', '-2d', '-1d', 'Today'], datasets: [{ label: 'RSI', yAxisID: 'y-rsi', borderColor: '#FFC107', data: [] }, { label: 'Stock Price (USD)', yAxisID: 'y-stock', borderColor: '#4CAF50', data: [] }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'top' } }, scales: { 'y-rsi': { type: 'linear', position: 'left', min: 0, max: 1 }, 'y-stock': { type: 'linear', position: 'right' } } }
        });
    }

    function updateSidebar(locationData) {
        document.getElementById('location-name').innerText = 'Ashburn, VA';
        document.getElementById('rsi-score').innerText = locationData.rsi.toFixed(2);
        const dummyHistory = [locationData.rsi - 0.1, locationData.rsi - 0.05, locationData.rsi + 0.02, locationData.rsi - 0.01, locationData.rsi].map(v => Math.max(0, Math.min(1, v)));
        const dummyStock = [150, 152, 148, 151, 149];
        rsiHistoryChart.data.datasets[0].data = dummyHistory;
        rsiHistoryChart.update();
        rsiStockChart.data.datasets[0].data = dummyHistory;
        rsiStockChart.data.datasets[1].data = dummyStock;
        rsiStockChart.update();
    }

    function getRsiColor(rsi) {
        if (rsi > 0.75) return '#F44336';
        if (rsi > 0.5) return '#FFC107';
        return '#4CAF50';
    }

    // --- 3. Initial Chart Creation and Data Loading ---
    createCharts();

    fetch('result.json')
        .then(response => response.ok ? response.json() : Promise.reject({ status: response.status }))
        .then(data => {
            const latestData = data[0];
            if (!latestData) return;

            L.circleMarker([39.0438, -77.4874], {
                radius: 8, color: getRsiColor(latestData.rsi), weight: 2, fillColor: getRsiColor(latestData.rsi), fillOpacity: 0.8
            }).addTo(map).bindPopup(`<b>Ashburn, VA</b><br>RSI: ${latestData.rsi.toFixed(2)}`).openPopup();

            updateSidebar(latestData);
        })
        .catch(e => {
            console.error('Failed to load or process result.json:', e);
            document.getElementById('location-name').innerText = 'Error';
            document.getElementById('rsi-score').innerText = 'N/A';
        });
});
