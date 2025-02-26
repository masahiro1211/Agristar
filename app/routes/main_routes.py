from flask import Blueprint, render_template, jsonify, request, redirect, url_for, session
from app.services.satellite_service import get_latest_ndvi_data, get_ndvi_data_by_date, validate_farm_area, get_farm_ndvi_image
from datetime import datetime, timedelta

main = Blueprint('main', __name__)

@main.route('/')
def index():
    # 登録済み農場があるかチェック
    farms = session.get('farms', [])
    return render_template('index.html', title='Agristar - スマート農業の未来', farms=farms)

@main.route('/farm/register', methods=['GET', 'POST'])
def register_farm():
    if request.method == 'POST':
        # POSTリクエストから農場データを取得
        farm_data = request.json
        
        # 農場の座標を検証
        validation = validate_farm_area(farm_data.get('coordinates'))
        if not validation['valid']:
            return jsonify({'success': False, 'error': validation['message']})
        
        # セッションから既存の農場リストを取得
        farms = session.get('farms', [])
        
        # 新しい農場IDを生成
        farm_id = len(farms) + 1
        
        # 新しい農場データを作成
        new_farm = {
            'id': farm_id,
            'name': farm_data.get('name'),
            'coordinates': farm_data.get('coordinates'),  # 4か所の座標を保存
            'bbox': validation['bbox'],  # バウンディングボックスを保存
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
    
    # リクエストから日付を取得
    data = request.json
    date_str = data.get('date')
    
    # 日付が指定されていない場合は最近5日間を使用
    if date_str:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        end_date = date_obj.strftime('%Y-%m-%d')
        start_date = (date_obj - timedelta(days=5)).strftime('%Y-%m-%d')
        date_range = (start_date, end_date)
    else:
        date_range = None
    
    # NDVI画像を取得
    result = get_farm_ndvi_image(farm['coordinates'], date_range)
    
    if not result['success']:
        return jsonify({'success': False, 'error': result['message']})
    
    # 結果を返す
    ndvi_result = {
        'farm_id': farm_id,
        'farm_name': farm['name'],
        'average_ndvi': result['data']['ndvi_stats']['mean'],
        'min_ndvi': result['data']['ndvi_stats']['min'],
        'max_ndvi': result['data']['ndvi_stats']['max'],
        'median_ndvi': result['data']['ndvi_stats']['median'],
        'ndvi_image': result['data']['ndvi_image'],
        'rgb_image': result['data']['rgb_image'],
        'date': date_str or datetime.now().strftime('%Y-%m-%d'),
        'start_date': result['data']['start_date'], # 開始日を追加
        'end_date': result['data']['end_date'] 
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