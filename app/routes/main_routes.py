from flask import Blueprint, render_template, jsonify, request, redirect, url_for, session
from app.services.satellite_service import get_latest_ndvi_data, get_ndvi_data_by_date

main = Blueprint('main', __name__)

@main.route('/')
def index():
    # 登録済み農場があるかチェック
    farms = session.get('farms', [])
    return render_template('index.html', title='NEXTファーム - スマート農業の未来', farms=farms)

@main.route('/farm/register', methods=['GET', 'POST'])
def register_farm():
    if request.method == 'POST':
        # POSTリクエストから農場データを取得
        farm_data = request.json
        
        # セッションから既存の農場リストを取得
        farms = session.get('farms', [])
        
        # 新しい農場IDを生成
        farm_id = len(farms) + 1
        
        # 新しい農場データを作成
        new_farm = {
            'id': farm_id,
            'name': farm_data.get('name'),
            'coordinates': farm_data.get('coordinates'),  # 4か所の座標を保存
            'created_at': farm_data.get('created_at')
        }
        
        # 農場リストに追加
        farms.append(new_farm)
        
        # セッションを更新
        session['farms'] = farms
        
        return jsonify({'success': True, 'farm_id': farm_id})
    
    # GETリクエストの場合は地図画面を表示
    return render_template('farm_register.html', title='農場登録')

@main.route('/farm/<int:farm_id>')
def view_farm(farm_id):
    # セッションから農場データを取得
    farms = session.get('farms', [])
    
    # 指定されたIDの農場を検索
    farm = next((f for f in farms if f['id'] == farm_id), None)
    
    if not farm:
        # 農場が見つからない場合はトップページにリダイレクト
        return redirect(url_for('main.index'))
    
    # 農場データを表示
    return render_template('farm_view.html', title=f'農場: {farm["name"]}', farm=farm)

@main.route('/farm/<int:farm_id>/ndvi', methods=['POST'])
def calculate_ndvi(farm_id):
    # セッションから農場データを取得
    farms = session.get('farms', [])
    farm = next((f for f in farms if f['id'] == farm_id), None)
    
    if not farm:
        return jsonify({'success': False, 'error': '農場が見つかりません'})
    
    # 実際のアプリケーションでは、ここでNDVI計算を行う
    # 今回はダミーデータを返す
    ndvi_result = {
        'farm_id': farm_id,
        'farm_name': farm['name'],
        'average_ndvi': 0.65,  # ダミー値
        'min_ndvi': 0.32,      # ダミー値
        'max_ndvi': 0.89,      # ダミー値
        'date': '2023-06-15'   # ダミー値
    }
    
    return jsonify({'success': True, 'result': ndvi_result})

@main.route('/farm/delete/<int:farm_id>', methods=['POST'])
def delete_farm(farm_id):
    # セッションから農場データを取得
    farms = session.get('farms', [])
    
    # 指定されたIDの農場を削除
    farms = [farm for farm in farms if farm['id'] != farm_id]
    
    # セッションを更新
    session['farms'] = farms
    
    return jsonify({'success': True})