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

aoi_coords_wgs84 = (141.05090, 38.437358, 141.090760, 38.468906) # 左上と右下の座標
resolution = 10  # 解像度10m

# バウンディングボックスを作成
aoi_bbox = BBox(bbox=aoi_coords_wgs84, crs=CRS.WGS84)
aoi_size = bbox_to_dimensions(aoi_bbox, resolution=resolution)

# evalscriptの設定（B08: 近赤外, B04: 赤, B03: 緑, B02: 青）
evalscript_evi = """
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

# SentinelHubRequestの作成
request_evi = SentinelHubRequest(
    evalscript=evalscript_evi,
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

# 画像を取得
evi_images = request_evi.get_data()

print(f"Returned data is of type = {type(evi_images)} and length {len(evi_images)}.")
if len(evi_images) > 0:
    print(f"Single element in the list is of type {type(evi_images[-1])} and has shape {evi_images[-1].shape}")

if not evi_images:
    raise ValueError("No data returned. Check your date range or bounding box settings.")

# 先頭の画像を取得
image = evi_images[0]
print(f"Image type: {image.dtype}, shape: {image.shape}")

if image.shape[2] != 4:
    raise ValueError(f"Expected 4 bands (B08, B04, B03, B02), but got {image.shape[2]} bands.")

# バンド割り当て
nir   = image[:, :, 0].astype(float)  # B08 (NIR)
red   = image[:, :, 1].astype(float)  # B04 (Red)
green = image[:, :, 2].astype(float)  # B03 (Green)
blue  = image[:, :, 3].astype(float)  # B02 (Blue)

# NDVIの計算
ndvi = (nir - red) / (nir + red + 1e-10)

# EVIの計算（B08のNIRを使用）
scale_factor = 10000.0
nir_scaled   = image[:, :, 0].astype(float) / scale_factor  # B08 (NIR)
red_scaled   = image[:, :, 1].astype(float) / scale_factor  # B04 (Red)
green_scaled = image[:, :, 2].astype(float) / scale_factor  # B03 (Green)
blue_scaled  = image[:, :, 3].astype(float) / scale_factor  # B02 (Blue)

G  = 2.5  # ゲイン係数
C1 = 6.0  # 赤バンド補正係数
C2 = 7.5  # 青バンド補正係数
L  = 1.0  # 土壌補正係数

evi = G * (nir_scaled - red_scaled) / (nir_scaled + C1 * red_scaled - C2 * blue_scaled + L + 1e-10)

# RGB画像の作成（可視化用：赤: B04, 緑: B03, 青: B02）
image_rgb = image[:, :, [1, 2, 3]].astype(np.uint8)

# 画像を明るく表示するための関数（元のコードと同じ内容）
def plot_image(image, factor=1.0, clip_range=(0, 1)):
    image_float = image.astype(np.float32) * factor
    image_float = np.clip(image_float, clip_range[0], clip_range[1])
    plt.figure(figsize=(8, 6))
    plt.imshow(image_float)
    plt.axis('off')
    plt.show()

# FAPARの計算（0～1に収まるようにクリップ）
fapar = 1.24 * ndvi - 0.168
fapar_clipped = np.clip(fapar, 0, 1)

# Allplusの計算
Allplus = fapar_clipped + evi * 40 + ndvi

# 5つのマップを並べて表示するためのサブプロット作成
fig, axes = plt.subplots(1, 5, figsize=(30, 6))

# 元画像 (image) を明るくして表示（plot_image関数の処理をサブプロット用にインラインで実行）
bright_image = image_rgb.astype(np.float32) * (3.5 / 255)
bright_image = np.clip(bright_image, 0, 1)
axes[0].imshow(bright_image)
axes[0].set_title("Original Image (B04,B03,B02) (Brightened)")
axes[0].axis("off")

# NDVIマップの表示
ndvi_img = axes[1].imshow(ndvi, cmap='RdYlGn')
axes[1].set_title("NDVI Map")
axes[1].axis("off")
plt.colorbar(ndvi_img, ax=axes[1], fraction=0.046, pad=0.04, label="NDVI Value")

# EVIマップの表示
evi_img = axes[2].imshow(evi, cmap='RdYlGn')
axes[2].set_title("EVI Map")
axes[2].axis("off")
plt.colorbar(evi_img, ax=axes[2], fraction=0.046, pad=0.04, label="EVI Value")

# FAPARマップの表示
fapar_img = axes[3].imshow(fapar_clipped, cmap='RdYlGn')
axes[3].set_title("FAPAR Map")
axes[3].axis("off")
plt.colorbar(fapar_img, ax=axes[3], fraction=0.046, pad=0.04, label="FAPAR Value (0 - 1)")

# Allplusマップの表示
allplus_img = axes[4].imshow(Allplus, cmap='RdYlGn')
axes[4].set_title("Allplus Map")
axes[4].axis("off")
plt.colorbar(allplus_img, ax=axes[4], fraction=0.046, pad=0.04, label="Allplus Value")

plt.tight_layout()
plt.show()
