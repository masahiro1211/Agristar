document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');
    const exampleButtons = document.querySelectorAll('.example-button');
    
    // 質問例ボタンのイベントリスナー
    exampleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const question = this.dataset.question;
            chatInput.value = question;
            chatInput.focus();
        });
    });
    
    // チャットフォームの送信イベント
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const message = chatInput.value.trim();
        if (message === '') return;
        
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
                question: message
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
        messageDiv.className = `message ${sender === 'user' ? 'user-message' : 'bot-message'}`;
        
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