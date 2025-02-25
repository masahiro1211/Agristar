document.addEventListener('DOMContentLoaded', function() {
    // 地図初期化
    const map = L.map('map').setView([36.2048, 138.2529], 5); // 日本の中心あたり

    // 地図レイヤー
    const baseLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    // NDVIヒートマップレイヤー - 初期は空
    let ndviLayer = null;

    // 現在選択されているデータタイプ
    let currentLayer = 'ndvi';

    // 現在表示している日付
    let currentDate = document.getElementById('current-date').textContent;

    // 日付選択機能の初期化
    initDatePicker();

    // 凡例スタイル（NDVIに基づく色の取得）
    function getNdviColor(ndvi) {
        if (ndvi > 0.8) return '#1a9850';
        if (ndvi > 0.6) return '#a6d96a';
        if (ndvi > 0.4) return '#fee08b';
        if (ndvi > 0.2) return '#fc8d59';
        return '#d73027';
    }

    // ヒートマップレイヤーの作成
    function createNdviLayer(data) {
        // 既存のレイヤーがあれば削除
        if (ndviLayer) {
            map.removeLayer(ndviLayer);
        }
        
        // ポイントマーカーを作成
        const markers = [];
        
        data.forEach(point => {
            const color = getNdviColor(point.ndvi);
            const marker = L.circleMarker([point.lat, point.lng], {
                radius: 8,
                fillColor: color,
                color: '#fff',
                weight: 1,
                opacity: 1,
                fillOpacity: 0.8
            });
            
            // ポップアップ情報
            marker.bindPopup(`
                <strong>位置:</strong> ${point.lat.toFixed(4)}, ${point.lng.toFixed(4)}<br>
                <strong>NDVI値:</strong> ${point.ndvi.toFixed(2)}<br>
                <strong>生育状態:</strong> ${getNdviLabel(point.ndvi)}
            `);
            
            markers.push(marker);
        });
        
        // レイヤーグループを作成
        ndviLayer = L.layerGroup(markers).addTo(map);
        
        // 日付表示を更新
        document.getElementById('current-date').textContent = data.date || currentDate;
    }

    // NDVI値のラベルを取得
    function getNdviLabel(ndvi) {
        if (ndvi > 0.8) return '生育最良';
        if (ndvi > 0.6) return '生育良好';
        if (ndvi > 0.4) return '生育普通';
        if (ndvi > 0.2) return '生育注意';
        return '生育不良';
    }

    // レイヤー選択の処理
    document.querySelectorAll('input[name="layer"]').forEach(radio => {
        radio.addEventListener('change', function() {
            currentLayer = this.value;
            loadLayerData(currentDate);
        });
    });

    // 日付選択機能の初期化
    function initDatePicker() {
        // カレンダーボタンのクリックイベント
        document.getElementById('calendar-toggle').addEventListener('click', function() {
            const datePicker = document.getElementById('date-picker');
            datePicker.classList.toggle('hidden');
            
            // 初めて開いたときに日付データを読み込む
            if (!datePicker.classList.contains('hidden') && datePicker.querySelector('.date-option') === null) {
                fetchAvailableDates();
            }
        });
    }

    // 利用可能な日付データを取得
    function fetchAvailableDates() {
        fetch('/map/dates')
            .then(response => response.json())
            .then(dates => {
                const availableDatesContainer = document.getElementById('available-dates');
                availableDatesContainer.innerHTML = '';
                
                dates.forEach(date => {
                    const dateOption = document.createElement('div');
                    dateOption.className = 'date-option';
                    dateOption.dataset.date = date;
                    
                    // 日付表示のフォーマット変換 (YYYYMMDD -> YYYY/MM/DD)
                    const formattedDate = `${date.slice(0, 4)}/${date.slice(4, 6)}/${date.slice(6, 8)}`;
                    dateOption.textContent = formattedDate;
                    
                    // 現在選択中の日付をハイライト
                    if (date === currentDate) {
                        dateOption.classList.add('active');
                    }
                    
                    // クリックイベント
                    dateOption.addEventListener('click', function() {
                        const selectedDate = this.dataset.date;
                        loadLayerData(selectedDate);
                        
                        // アクティブクラスの更新
                        document.querySelectorAll('.date-option').forEach(opt => {
                            opt.classList.remove('active');
                        });
                        this.classList.add('active');
                        
                        // 日付ピッカーを閉じる
                        document.getElementById('date-picker').classList.add('hidden');
                    });
                    
                    availableDatesContainer.appendChild(dateOption);
                });
            })
            .catch(error => {
                console.error('日付データの取得に失敗しました:', error);
            });
    }

    // レイヤーデータの読み込み
    function loadLayerData(date) {
        let endpoint;
        
        if (date === 'latest' || !date) {
            endpoint = '/map/data/latest';
        } else {
            endpoint = `/map/data/by-date/${date}`;
        }
        
        fetch(endpoint)
            .then(response => response.json())
            .then(data => {
                currentDate = data.date;
                createNdviLayer(data.data);
            })
            .catch(error => {
                console.error('データの取得に失敗しました:', error);
            });
    }

    // AIチャットボタンの処理
    document.getElementById('chat-button').addEventListener('click', function() {
        window.location.href = '/chatbot';
    });

    // 操作説明の非表示ボタン
    document.getElementById('hide-instructions').addEventListener('click', function() {
        document.getElementById('map-instructions').style.display = 'none';
    });

    // 初期データの読み込み
    loadLayerData('latest');
});