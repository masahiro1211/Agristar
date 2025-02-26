document.addEventListener('DOMContentLoaded', function() {
         // 地図初期化
         const map = L.map('map').setView([36.2048, 138.2529], 5); // 日本の中心あたり
     
         // 地図レイヤー
         const baseLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
             attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
         }).addTo(map);
     
         // 農場データを取得してマーカー表示
         fetch('/map/farms') // 新しいエンドポイント
             .then(response => response.json())
             .then(farms => {
                farms.forEach(farm => {
                    let coord;
                    if (Array.isArray(farm.coordinates) && farm.coordinates.length > 0) {
                        // coordinates が配列の場合、最初の要素を使用
                        coord = farm.coordinates[0];
                    } else if (farm.coordinates && typeof farm.coordinates === 'object' && farm.coordinates.lat && farm.coordinates.lng) {
                        // coordinates がオブジェクトで lat, lng を持つ場合
                        coord = farm.coordinates;
                    }
    
                    if (coord) {
                        L.marker([coord.lat, coord.lng])
                            .addTo(map)
                            .bindPopup(`<strong>${farm.name}</strong> <br><a href="/farm/${farm.id}">詳細を見る</a>`); // ポップアップにリンクを追加
                    }
                });
            　})        
            .catch(error => {
                console.error('農場データの取得に失敗しました:', error);
            });
    // AIチャットボタンの処理
    document.getElementById('chat-button').addEventListener('click', function() {
        window.location.href = '/chatbot';
    });

    // 操作説明の非表示ボタン
    document.getElementById('hide-instructions').addEventListener('click', function() {
        document.getElementById('map-instructions').style.display = 'none';
    });

    // 初期データの読み込み
    //loadLayerData('latest');
});