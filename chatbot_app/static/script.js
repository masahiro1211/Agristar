document.addEventListener('DOMContentLoaded', function() {
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const chatHistory = document.getElementById('chat-history');

    sendButton.addEventListener('click', function() {
        const message = userInput.value;
        if (message.trim() === '') return; // 空メッセージの場合は送信しない

        // ユーザーのメッセージをチャット履歴に追加
        addUserMessage(message);
        userInput.value = ''; // 入力欄をクリア

        // Flask APIにPOSTリクエストを送信
        fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ user_input: message })
        })
        .then(response => response.json())
        .then(data => {
            // ボットの回答をチャット履歴に追加
            addBotMessage(data.response);
        });
    });

    function addUserMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('user-message');
        messageDiv.textContent = 'あなた: ' + message;
        chatHistory.appendChild(messageDiv);
        scrollToBottom();
    }

    function addBotMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('bot-message');
        messageDiv.textContent = '東大の仕様を知るロボ: ' + message;
        chatHistory.appendChild(messageDiv);
        scrollToBottom();
    }

    function scrollToBottom() {
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }
});