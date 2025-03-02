document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');
    const exampleButtons = document.querySelectorAll('.example-button');
    const farmSelector = document.getElementById('farm-selector');
    const dateInput = document.getElementById('chat-date');
    const weatherButton = document.getElementById('weather-button');
    const ndviButton = document.getElementById('ndvi-button');
    const farmingCalendarButton = document.getElementById('calendar-button');
    
    // 現在の日付をデフォルト値として設定
    if (dateInput) {
        const today = new Date();
        dateInput.value = today.toISOString().split('T')[0];
    }
    
    // 質問例ボタンのイベントリスナー
    exampleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const question = this.dataset.question;
            chatInput.value = question;
            chatInput.focus();
        });
    });
    
    // 天気予報ボタン
    if (weatherButton) {
        weatherButton.addEventListener('click', function() {
            const farmId = farmSelector ? farmSelector.value : null;
            getWeatherAdvice(farmId);
        });
    }
    
    // NDVIデータボタン
    if (ndviButton) {
        ndviButton.addEventListener('click', function() {
            const farmId = farmSelector ? farmSelector.value : null;
            const date = dateInput ? dateInput.value : null;
            getNdviAdvice(farmId, date);
        });
    }
    
    // 農作業カレンダーボタン
    if (farmingCalendarButton) {
        farmingCalendarButton.addEventListener('click', function() {
            const farmId = farmSelector ? farmSelector.value : null;
            getFarmingCalendarAdvice(farmId);
        });
    }
    
    // 天気予報アドバイスを取得
    function getWeatherAdvice(farmId) {
        const typingIndicator = addTypingIndicator();
        
        fetch(`/chatbot/weather?farm_id=${farmId || ''}`)
            .then(response => response.json())
            .then(data => {
                typingIndicator.remove();
                addMessage('今後の天気予報に基づいたアドバイスを教えてください', 'user');
                addMessage(data.advice, 'bot');
                chatMessages.scrollTop = chatMessages.scrollHeight;
            })
            .catch(error => {
                console.error('エラー:', error);
                typingIndicator.remove();
                addMessage('申し訳ありません。天気データの取得中にエラーが発生しました。', 'bot');
            });
    }
    
    // NDVIアドバイスを取得
    function getNdviAdvice(farmId, date) {
        if (!farmId) {
            addMessage('農場を選択してください。', 'system');
            return;
        }
        
        const typingIndicator = addTypingIndicator();
        
        fetch(`/chatbot/farm/${farmId}/advice?date=${date || ''}`)
            .then(response => response.json())
            .then(data => {
                typingIndicator.remove();
                addMessage(`農場ID: ${farmId}の現在の状態分析とアドバイスを教えてください${date ? '（' + date + '）' : ''}`, 'user');
                addMessage(data.advice, 'bot');
                chatMessages.scrollTop = chatMessages.scrollHeight;
            })
            .catch(error => {
                console.error('エラー:', error);
                typingIndicator.remove();
                addMessage('申し訳ありません。NDVIデータの取得中にエラーが発生しました。', 'bot');
            });
    }
    
    // 農作業カレンダーアドバイスを取得
    function getFarmingCalendarAdvice(farmId) {
        const typingIndicator = addTypingIndicator();
        
        // 農場に基づいて作物タイプを取得する質問を送信
        const message = farmId 
            ? `農場ID: ${farmId}の今月と来月の推奨農作業を教えてください` 
            : '今月と来月の一般的な農作業スケジュールを教えてください';
        
        addMessage(message, 'user');
        
        // APIリクエストを送信
        fetch('/chatbot/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                question: message,
                farm_id: farmId || null
            })
        })
        .then(response => response.json())
        .then(data => {
            typingIndicator.remove();
            addMessage(data.response, 'bot');
            chatMessages.scrollTop = chatMessages.scrollHeight;
        })
        .catch(error => {
            console.error('エラー:', error);
            typingIndicator.remove();
            addMessage('申し訳ありません。農作業カレンダーの取得中にエラーが発生しました。', 'bot');
        });
    }
    
    // チャットフォームの送信イベント
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const message = chatInput.value.trim();
        if (message === '') return;
        
        // 選択された農場ID
        const farmId = farmSelector ? farmSelector.value : null;
        const date = dateInput ? dateInput.value : null;
        
        // ユーザーメッセージをUIに追加
        addMessage(message, 'user');
        
        // 入力フィールドをクリア
        chatInput.value = '';
        
        // ボットの「入力中...」状態を表示
        const typingIndicator = addTypingIndicator();
        
        // APIリクエストを送信
        fetch('/chatbot/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                question: message,
                farm_id: farmId,
                date: date
            })
        })
        .then(response => response.json())
        .then(data => {
            // 「入力中...」を削除
            typingIndicator.remove();
            
            // ボットの応答をUIに追加
            addMessage(data.response, 'bot');
            
            // 最新のメッセージまでスクロール
            chatMessages.scrollTop = chatMessages.scrollHeight;
        })
        .catch(error => {
            console.error('エラー:', error);
            typingIndicator.remove();
            addMessage('申し訳ありません。エラーが発生しました。後ほど再度お試しください。', 'bot');
        });
    });
    
    // メッセージをチャットUIに追加する関数
    function addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender === 'user' ? 'user-message' : (sender === 'system' ? 'system-message' : 'bot-message')}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // テキスト内の改行を保持
        const formattedText = text.replace(/\n/g, '<br>');
        contentDiv.innerHTML = `<p>${formattedText}</p>`;
        
        messageDiv.appendChild(contentDiv);
        chatMessages.appendChild(messageDiv);
        
        // 最新のメッセージまでスクロール
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        return messageDiv;
    }
    
    // 「入力中...」インジケータを追加する関数
    function addTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message bot-message typing-indicator';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = '<p>入力中...</p>';
        
        typingDiv.appendChild(contentDiv);
        chatMessages.appendChild(typingDiv);
        
        // 最新のメッセージまでスクロール
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        return typingDiv;
    }
});