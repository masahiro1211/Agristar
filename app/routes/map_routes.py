from flask import Blueprint, render_template, jsonify, request
from app.services.satellite_service import get_latest_ndvi_data, get_ndvi_data_by_date, get_available_dates

map_bp = Blueprint('map', __name__, url_prefix='/map')

@map_bp.route('/')
def map_view():
    # 最新の衛星画像取得日
    latest_date = get_available_dates()[0] if get_available_dates() else "データなし"
    return render_template('map.html', title='生育状況マップ', latest_date=latest_date)

@map_bp.route('/data/latest')
def get_latest_data():
    # 最新のNDVIデータを返す
    data = get_latest_ndvi_data()
    return jsonify(data)

@map_bp.route('/data/by-date/<date_str>')
def get_data_by_date(date_str):
    # 指定日のNDVIデータを返す
    data = get_ndvi_data_by_date(date_str)
    return jsonify(data)

@map_bp.route('/dates')
def available_dates():
    # 利用可能な日付リストを返す
    dates = get_available_dates()
    return jsonify(dates)