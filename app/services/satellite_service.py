import os
import json
from datetime import datetime, timedelta
from flask import current_app
import random
import cv2
import numpy as np
import matplotlib.pyplot as plt
from skimage import exposure
import scipy.ndimage
import pandas as pd
from sentinelhub import SHConfig, BBox, CRS, bbox_to_dimensions, SentinelHubRequest, DataCollection, MimeType
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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

# Sentinel Hubのアクセス情報を設定
config = SHConfig()
config.sh_client_id = os.getenv("SH_CLIENT_ID")
config.sh_client_secret = os.getenv("SH_CLIENT_SECRET")
config.sh_token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
config.sh_base_url = "https://sh.dataspace.copernicus.eu"
config.save("cdse")

def create_bbox_and_size(coords, resolution):
    """
    バウンディングボックスを作成し、その寸法を計算します。

    パラメータ:
    coords (tuple): WGS84形式の座標 (min_lon, min_lat, max_lon, max_lat)。
    resolution (int): メートル単位の解像度。

    戻り値:
    tuple: バウンディングボックスとその寸法。
    """
    aoi_bbox = BBox(bbox=coords, crs=CRS.WGS84)
    aoi_size = bbox_to_dimensions(aoi_bbox, resolution=resolution)

    # 最大ピクセル数のチェック
    max_pixels = 2500
    if aoi_size[0] > max_pixels or aoi_size[1] > max_pixels:
        raise ValueError(f"バウンディングボックスの幅または高さが許可されている最大値（{max_pixels}ピクセル）を超えています。")

    return aoi_bbox, aoi_size

def create_evalscript():
    """
    SentinelHubRequest用のevalscriptを作成します。

    戻り値:
    str: NIR、Red、Green、Blueバンドを取得するためのevalscript。
    """
    return """
    //VERSION=3
    function setup() {
        return {
            input: [{
                bands: ["B08", "B04", "B03", "B02"]
            }],
            output: {
                bands: 4
            }
        };
    }
    function evaluatePixel(sample) {
        return [
            sample.B08,  // NIR
            sample.B04,  // Red
            sample.B03,  // Green
            sample.B02   // Blue
        ];
    }
    """

def create_sentinel_request(aoi_bbox, aoi_size, config):
    """
    EVIデータ用のSentinelHubRequestを作成します。

    パラメータ:
    aoi_bbox (BBox): 関心領域のバウンディングボックス。
    aoi_size (tuple): バウンディングボックスの寸法。
    config (SHConfig): Sentinel Hubの設定。

    戻り値:
    SentinelHubRequest: Sentinel Hub用に設定されたリクエスト。
    """
    evalscript = create_evalscript()
    return SentinelHubRequest(
        evalscript=evalscript,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=DataCollection.SENTINEL2_L2A.define_from(
                    name="s2",
                    service_url="https://sh.dataspace.copernicus.eu"
                ),
                time_interval=('2020-08-10', '2020-08-15')
            )
        ],
        responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
        bbox=aoi_bbox,
        size=aoi_size,
        config=config
    )

def process_image_data(evi_images):
    """
    画像データを処理してNDVI、EVI、FAPAR、Allplusを計算します。

    パラメータ:
    evi_images (list): SentinelHubRequestから返された画像のリスト。

    戻り値:
    tuple: 処理されたNDVI、EVI、FAPAR、Allplus、およびRGB画像。
    """
    if not evi_images:
        raise ValueError("データが返されませんでした。日付範囲またはバウンディングボックスの設定を確認してください。")

    image = evi_images[0]

    nir, red, green, blue = [image[:, :, i].astype(float) for i in range(4)]

    ndvi = (nir - red) / (nir + red + 1e-10)

    scale_factor = 10000.0
    nir_scaled, red_scaled, green_scaled, blue_scaled = [band / scale_factor for band in (nir, red, green, blue)]

    G, C1, C2, L = 2.5, 6.0, 7.5, 1.0
    evi = G * (nir_scaled - red_scaled) / (nir_scaled + C1 * red_scaled - C2 * blue_scaled + L + 1e-10)

    fapar = 1.24 * ndvi - 0.168
    fapar_clipped = np.clip(fapar, 0, 1)

    Allplus = fapar_clipped + evi * 40 + ndvi

    image_rgb = image[:, :, [1, 2, 3]].astype(np.uint8)

    return ndvi, evi, fapar_clipped, Allplus, image_rgb

def plot_maps(ndvi, evi, fapar_clipped, Allplus, image_rgb):
    """
    元画像と計算されたマップ（NDVI、EVI、FAPAR、Allplus）をプロットします。

    パラメータ:
    ndvi (ndarray): NDVIマップ。
    evi (ndarray): EVIマップ。
    fapar_clipped (ndarray): FAPARマップ。
    Allplus (ndarray): Allplusマップ。
    image_rgb (ndarray): 可視化用のRGB画像。
    """
    fig, axes = plt.subplots(1, 5, figsize=(30, 6))

    bright_image = image_rgb.astype(np.float32) * (3.5 / 255)
    bright_image = np.clip(bright_image, 0, 1)
    axes[0].imshow(bright_image)
    axes[0].set_title("Original Image (B04,B03,B02) (Brightened)")
    axes[0].axis("off")

    ndvi_img = axes[1].imshow(ndvi, cmap='RdYlGn')
    axes[1].set_title("NDVI Map")
    axes[1].axis("off")
    plt.colorbar(ndvi_img, ax=axes[1], fraction=0.046, pad=0.04, label="NDVI Value")

    evi_img = axes[2].imshow(evi, cmap='RdYlGn')
    axes[2].set_title("EVI Map")
    axes[2].axis("off")
    plt.colorbar(evi_img, ax=axes[2], fraction=0.046, pad=0.04, label="EVI Value")

    fapar_img = axes[3].imshow(fapar_clipped, cmap='RdYlGn')
    axes[3].set_title("FAPAR Map")
    axes[3].axis("off")
    plt.colorbar(fapar_img, ax=axes[3], fraction=0.046, pad=0.04, label="FAPAR Value (0 - 1)")

    allplus_img = axes[4].imshow(Allplus, cmap='RdYlGn')
    axes[4].set_title("Allplus Map")
    axes[4].axis("off")
    plt.colorbar(allplus_img, ax=axes[4], fraction=0.046, pad=0.04, label="Allplus Value")

    plt.tight_layout()
    plt.show()

def get_farm_bbox(coordinates):
    """
    農場の座標から最小のバウンディングボックスを計算します。
    
    パラメータ:
    coordinates (list): 農場の座標リスト [{lat, lng}, ...]
    
    戻り値:
    tuple: WGS84形式の座標 (min_lon, min_lat, max_lon, max_lat)
    """
    lats = [coord['lat'] for coord in coordinates]
    lngs = [coord['lng'] for coord in coordinates]
    
    min_lat = min(lats)
    max_lat = max(lats)
    min_lng = min(lngs)
    max_lng = max(lngs)
    
    # バウンディングボックスを少し広げる（10%）
    lat_padding = (max_lat - min_lat) * 0.1
    lng_padding = (max_lng - min_lng) * 0.1
    
    return (
        min_lng - lng_padding,  # min_lon
        min_lat - lat_padding,  # min_lat
        max_lng + lng_padding,  # max_lon
        max_lat + lat_padding   # max_lat
    )

def validate_farm_area(coordinates, max_resolution=10):
    """
    農場の面積が処理可能かどうかを検証します。
    
    パラメータ:
    coordinates (list): 農場の座標リスト [{lat, lng}, ...]
    max_resolution (int): 最大解像度（メートル単位）
    
    戻り値:
    dict: 検証結果 {'valid': bool, 'message': str, 'bbox': tuple, 'size': tuple}
    """
    try:
        bbox = get_farm_bbox(coordinates)
        
        # バウンディングボックスのサイズを計算
        try:
            aoi_bbox, aoi_size = create_bbox_and_size(bbox, max_resolution)
            
            # 最大ピクセル数のチェック
            max_pixels = 2500
            if aoi_size[0] > max_pixels or aoi_size[1] > max_pixels:
                return {
                    'valid': False,
                    'message': f"選択された農場の面積が大きすぎます。より小さい範囲を選択してください。（最大 {max_pixels}x{max_pixels} ピクセル）",
                    'bbox': bbox,
                    'size': aoi_size
                }
            
            return {
                'valid': True,
                'message': "農場の面積は処理可能です。",
                'bbox': bbox,
                'size': aoi_size
            }
        except ValueError as e:
            return {
                'valid': False,
                'message': str(e),
                'bbox': bbox,
                'size': None
            }
    except Exception as e:
        return {
            'valid': False,
            'message': f"エラーが発生しました: {str(e)}",
            'bbox': None,
            'size': None
        }

def get_farm_ndvi_image(coordinates, date_range=None):
    """
    農場のNDVI画像を取得します。
    
    パラメータ:
    coordinates (list): 農場の座標リスト [{lat, lng}, ...]
    date_range (tuple): 日付範囲 (start_date, end_date)
    
    戻り値:
    dict: 処理結果
    """
    try:
        # バウンディングボックスを計算
        bbox = get_farm_bbox(coordinates)
        
        # 解像度を設定（メートル単位）
        resolution = 10
        
        # バウンディングボックスとサイズを計算
        aoi_bbox, aoi_size = create_bbox_and_size(bbox, resolution)
        
        # 日付範囲が指定されていない場合は最近5日間を使用
        if not date_range:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
            date_range = (start_date, end_date)
        
        # Sentinel Hubリクエストを作成
        evalscript = create_evalscript()
        request = SentinelHubRequest(
            evalscript=evalscript,
            input_data=[
                SentinelHubRequest.input_data(
                    data_collection=DataCollection.SENTINEL2_L2A.define_from(
                        name="s2",
                        service_url="https://sh.dataspace.copernicus.eu"
                    ),
                    time_interval=date_range,
                    maxcc=0.2  # クラウドカバー率の最大値（20%以下のデータのみを使用）
                )
            ],
            responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
            bbox=aoi_bbox,
            size=aoi_size,
            config=config
        )
        
        # データを取得
        images = request.get_data()
        
        if not images:
            return {
                'success': False,
                'message': "指定された日付範囲で利用可能な画像がありません。",
                'data': None
            }
        
        # 画像データを処理
        ndvi, evi, fapar, allplus, rgb = process_image_data(images)
        
        # NDVIの統計情報を計算
        ndvi_valid = ndvi[~np.isnan(ndvi)]  # NaN値を除外
        if len(ndvi_valid) > 0:
            ndvi_stats = {
                'min': float(np.nanmin(ndvi)),
                'max': float(np.nanmax(ndvi)),
                'mean': float(np.nanmean(ndvi)),
                'median': float(np.nanmedian(ndvi))
            }
        else:
            ndvi_stats = {
                'message': "利用可能なデータが存在しません。"
            }
        
        # NDVIデータをBase64エンコード
        ndvi_normalized = (np.clip(ndvi, -1, 1) + 1) / 2 * 255  # -1〜1の範囲を0〜255に正規化
        ndvi_img = np.uint8(ndvi_normalized)
        
        # カラーマップを適用
        cmap = plt.get_cmap('RdYlGn')
        ndvi_colored = cmap(ndvi_img / 255.0) * 255
        ndvi_colored = ndvi_colored.astype(np.uint8)
        
        # 画像をエンコード
        import io
        import base64
        from PIL import Image
        
        # NDVI画像
        ndvi_pil = Image.fromarray(ndvi_colored)
        ndvi_buffer = io.BytesIO()
        ndvi_pil.save(ndvi_buffer, format='PNG')
        ndvi_base64 = base64.b64encode(ndvi_buffer.getvalue()).decode('utf-8')
        
        # RGB画像
        rgb_normalized = np.clip(rgb * 3.5, 0, 255).astype(np.uint8)  # 明るさ調整
        rgb_pil = Image.fromarray(rgb_normalized)
        rgb_buffer = io.BytesIO()
        rgb_pil.save(rgb_buffer, format='PNG')
        rgb_base64 = base64.b64encode(rgb_buffer.getvalue()).decode('utf-8')
        
        return {
            'success': True,
            'message': "NDVI画像を取得しました。",
            'data': {
                'ndvi_stats': ndvi_stats,
                'ndvi_image': ndvi_base64,
                'rgb_image': rgb_base64,
                'bbox': bbox,
                'date_range': date_range,
                'start_date': date_range[0] if date_range else datetime.now().strftime('%Y-%m-%d'), # 開始日を追加
                'end_date': date_range[1] if date_range else datetime.now().strftime('%Y-%m-%d')   # 終了日を追加 (image_date を end_date に変更)
            }
        }
    except Exception as e:
        import traceback
        return {
            'success': False,
            'message': f"エラーが発生しました: {str(e)}",
            'error_details': traceback.format_exc(),
            'data': None
        }

if __name__ == "__main__":
    aoi_coords_wgs84 = (141.05090, 38.437358, 151.090760, 45.468906)  # 左上と右下の座標
    resolution = 10  # 解像度10m
    aoi_bbox, aoi_size = create_bbox_and_size(aoi_coords_wgs84, resolution)
    request_evi = create_sentinel_request(aoi_bbox, aoi_size, config)
    evi_images = request_evi.get_data()

    ndvi, evi, fapar_clipped, Allplus, image_rgb = process_image_data(evi_images)
    plot_maps(ndvi, evi, fapar_clipped, Allplus, image_rgb)
