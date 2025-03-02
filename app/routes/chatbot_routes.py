from flask import Blueprint, render_template, request, jsonify, session
import sys
import os
from datetime import datetime

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
    farm_id = data.get('farm_id', None)
    date = data.get('date', None)
    
    # 農場IDがない場合、セッションから取得を試みる
    if not farm_id:
        farms = session.get('farms', [])
        if farms:
            farm_id = farms[0]['id']
    
    # 日付がない場合、現在の日付を使用
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')
    
    # chatbot.py の関数を呼び出し
    response = chatbot.generate_rag_response(question, farm_id, date)
    
    return jsonify({'response': response})

@chatbot_bp.route('/farm/<int:farm_id>/advice', methods=['GET'])
def get_farm_advice(farm_id):
    """特定の農場に対するNDVIデータと農業アドバイスを取得"""
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    # NDVIデータに基づいたアドバイスを生成
    question = "この農場の現在の状態について詳細な分析と今後の管理方法のアドバイスを提供してください"
    advice = chatbot.generate_rag_response(question, farm_id, date)
    
    return jsonify({
        'farm_id': farm_id,
        'date': date,
        'advice': advice
    })

@chatbot_bp.route('/weather', methods=['GET'])
def get_weather_advice():
    """天候に基づく農業アドバイスを取得"""
    lat = request.args.get('lat')
    lng = request.args.get('lng')
    farm_id = request.args.get('farm_id')
    
    # 緯度経度がない場合、農場IDから取得を試みる
    if not (lat and lng) and farm_id:
        farms = session.get('farms', [])
        farm = next((f for f in farms if f['id'] == int(farm_id)), None)
        if farm and farm.get('coordinates'):
            coords = farm['coordinates'][0] if isinstance(farm['coordinates'], list) else farm['coordinates']
            lat = coords.get('lat')
            lng = coords.get('lng')
    
    question = "今後の天候予報に基づいて、農場管理のアドバイスを提供してください"
    advice = chatbot.generate_rag_response(question, farm_id)
    
    return jsonify({
        'farm_id': farm_id,
        'lat': lat,
        'lng': lng,
        'advice': advice
    })