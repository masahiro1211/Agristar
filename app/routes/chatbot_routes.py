from flask import Blueprint, render_template, request, jsonify
import sys
import os

# 親ディレクトリにある chatbot.py を import できるようにする
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import chatbot

chatbot_bp = Blueprint('chatbot', __name__, url_prefix='/chatbot')

@chatbot_bp.route('/')
def chatbot_view():
    return render_template('chatbot.html', title='AIアグリアドバイザー')

@chatbot_bp.route('/ask', methods=['POST'])
def ask_question():
    data = request.json
    question = data.get('question', '')
    field_id = data.get('field_id', None)
    date = data.get('date', None)
    
    # chatbot.py の関数を呼び出し
    response = chatbot.generate_rag_response(question)
    
    return jsonify({'response': response})