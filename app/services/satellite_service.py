import os
import json
from datetime import datetime, timedelta
from flask import current_app
import random

# 暫定的な実装 - 後で実際の衛星データ処理に置き換え
def get_latest_ndvi_data():
    """最新のNDVIデータを取得する暫定実装"""
    # 日本全体をカバーする範囲を定義
    japan_bounds = {
        "north": 45.8,  # 北海道の北端
        "south": 24.0,  # 沖縄の南端
        "east": 146.0,  # 小笠原諸島の東端
        "west": 122.0   # 与那国島の西端
    }
    
    # 暫定的なNDVIデータを生成
    grid_size = 50
    lat_step = (japan_bounds["north"] - japan_bounds["south"]) / grid_size
    lng_step = (japan_bounds["east"] - japan_bounds["west"]) / grid_size
    
    ndvi_data = []
    for i in range(grid_size):
        for j in range(grid_size):
            lat = japan_bounds["south"] + i * lat_step
            lng = japan_bounds["west"] + j * lng_step
            
            # 日本の陸地っぽい場所だけにデータを生成（簡易的な判定）
            if is_likely_land(lat, lng):
                # 0.0 から 1.0 の範囲でランダムなNDVI値を生成
                ndvi_value = random.uniform(0.0, 1.0)
                ndvi_data.append({
                    "lat": lat,
                    "lng": lng,
                    "ndvi": ndvi_value
                })
    
    return {
        "date": get_available_dates()[0],
        "data": ndvi_data
    }

def get_ndvi_data_by_date(date_str):
    """指定された日付のNDVIデータを取得する暫定実装"""
    # 基本データを取得して日付だけ変更
    data = get_latest_ndvi_data()
    data["date"] = date_str
    
    # 日付が古いほど値を少し変える（ランダム変動を加える）
    latest_date = datetime.strptime(get_available_dates()[0], "%Y%m%d")
    target_date = datetime.strptime(date_str, "%Y%m%d")
    days_diff = (latest_date - target_date).days
    
    # 日付の差に応じてデータを少し変化させる
    for point in data["data"]:
        # 最大10%の変動を加える（古いほど変動大）
        variation = random.uniform(-0.1, 0.1) * (days_diff / 30)
        point["ndvi"] = max(0.0, min(1.0, point["ndvi"] + variation))
    
    return data

def get_available_dates():
    """利用可能な衛星画像の日付リストを取得する暫定実装"""
    # 現在から過去30日間で、5日ごとにデータがあると仮定
    today = datetime.now()
    dates = []
    
    for i in range(0, 31, 5):
        date = today - timedelta(days=i)
        dates.append(date.strftime("%Y%m%d"))
    
    return dates

def is_likely_land(lat, lng):
    """簡易的な日本の陸地判定（実際の実装では地理データを使用）"""
    # 非常に簡易的な判定ロジック
    # 北海道
    if 41.0 <= lat <= 45.8 and 140.0 <= lng <= 146.0:
        return random.random() < 0.6
    # 本州
    elif 33.0 <= lat <= 41.0 and 130.0 <= lng <= 142.0:
        return random.random() < 0.7
    # 四国・九州
    elif 30.0 <= lat <= 34.5 and 129.0 <= lng <= 135.0:
        return random.random() < 0.6
    # 沖縄
    elif 24.0 <= lat <= 27.0 and 122.0 <= lng <= 129.0:
        return random.random() < 0.3
    else:
        return random.random() < 0.1  # 海の部分はほとんどデータなし