import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os
from flask import Flask, render_template, request, jsonify, session, g
from langchain_core.vectorstores import InMemoryVectorStore
import bs4
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing_extensions import List, TypedDict
from langgraph.graph import MessagesState, StateGraph, END
from langchain_core.tools import tool
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langgraph.prebuilt.tool_node import ToolNode
from langgraph.prebuilt import tools_condition
from langchain_core.messages import SystemMessage
import json
from datetime import datetime, timedelta
import sqlite3
import numpy as np

# NDVIマッピングモジュールをインポート
from app.services.ndvi_mapping import NDVI_MAPPING, evaluate_ndvi_health, analyze_ndvi_trend, get_current_season

app = Flask(__name__)

# .envファイルを読み込む
load_dotenv()

# 環境変数からAPIキーを取得
google_api_key = os.getenv("GOOGLE_API_KEY")

# Geminiモデルの設定
genai.configure(api_key=google_api_key)
model = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp")
embedding_model = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
vector_store = InMemoryVectorStore(embedding_model)

# 農業関連のナレッジベース読み込み
loader = WebBaseLoader(
    web_paths=("https://www.sciencedirect.com/science/article/abs/pii/S0034425719304717",),
    bs_kwargs=dict(
        parse_only=bs4.SoupStrainer(
            class_=("post-content", "post-title", "post-header")
        )
    ),
)
docs = loader.load()

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
all_splits = text_splitter.split_documents(docs)
_ = vector_store.add_documents(documents=all_splits)
graph_builder = StateGraph(MessagesState)

@tool(response_format="content_and_artifact")
def retrieve(query: str):
    """Retrieve information related to a query."""
    retrieved_docs = vector_store.similarity_search(query, k=5)
    serialized = "\n\n".join(
        (f"Source: {doc.metadata}\n" f"Content: {doc.page_content}")
        for doc in retrieved_docs
    )
    return serialized, retrieved_docs

# NDVIデータを取得するツール
@tool
def get_farm_ndvi_data(farm_id: str = None, date: str = None):
    """
    農場のNDVIデータを取得する
    
    Parameters:
    farm_id (str): 農場ID（指定がない場合は最新の農場）
    date (str): 日付（指定がない場合は最新データ）
    
    Returns:
    dict: NDVIデータと分析結果
    """
    try:
        from flask import current_app, g
        from datetime import datetime, timedelta
        from app.services.satellite_service import get_farm_ndvi_image, validate_farm_area
        import sqlite3
        import os
        import json
        
        # データベース接続（なければ作成）
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'farms.db')
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # テーブルがなければ作成
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS farm_ndvi_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farm_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            min_ndvi REAL,
            max_ndvi REAL,
            mean_ndvi REAL,
            median_ndvi REAL,
            crop_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        conn.commit()
        
        # アプリケーションコンテキストでセッションから農場データを取得
        with current_app.app_context():
            # まずセッションから農場を取得
            farms = session.get('farms', [])
            
            # 指定されたIDの農場を検索、なければ最初の農場を使用
            if farm_id:
                farm = next((f for f in farms if f['id'] == int(farm_id)), None)
            else:
                farm = farms[0] if farms else None
        
        # 農場がない場合
        if not farm:
            return {"error": "農場データが見つかりません。農場を登録してください。"}
        
        # 日付が指定されていない場合は最新の日付
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # 日付範囲の設定（指定された日付から5日間）
        end_date = datetime.strptime(date, '%Y-%m-%d')
        start_date = end_date - timedelta(days=5)
        date_range = (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
        
        # satellite_serviceを使用してNDVIデータを取得
        ndvi_result = get_farm_ndvi_image(farm['coordinates'], date_range)
        
        if not ndvi_result['success']:
            return {"error": f"NDVIデータの取得に失敗しました: {ndvi_result['message']}"}
        
        # 履歴データをデータベースから取得
        cursor.execute(
            "SELECT date, mean_ndvi as value FROM farm_ndvi_history WHERE farm_id = ? ORDER BY date ASC LIMIT 10",
            (farm['id'],)
        )
        history_records = cursor.fetchall()
        
        # 履歴データを整形
        history = [{"date": record['date'], "value": record['value']} for record in history_records]
        
        # NDVIデータを整形
        ndvi_data = {
            "farm_id": farm['id'],
            "farm_name": farm['name'],
            "date": end_date.strftime('%Y-%m-%d'),
            "ndvi_stats": {
                "min": ndvi_result['data']['ndvi_stats']['min'],
                "max": ndvi_result['data']['ndvi_stats']['max'],
                "mean": ndvi_result['data']['ndvi_stats']['mean'],
                "median": ndvi_result['data']['ndvi_stats']['median']
            },
            "images": {
                "ndvi": ndvi_result['data']['ndvi_image'],
                "rgb": ndvi_result['data']['rgb_image']
            },
            "date_range": {
                "start": ndvi_result['data']['start_date'],
                "end": ndvi_result['data']['end_date']
            },
            "history": history,
            # 作物タイプは現在のデータモデルには含まれていないため、デフォルト値または設定から取得
            "crop_type": farm.get('crop_type', "rice"),
        }
        
        # 新しいNDVIデータを履歴に保存（同じ日付のデータがなければ）
        cursor.execute(
            "SELECT id FROM farm_ndvi_history WHERE farm_id = ? AND date = ?",
            (farm['id'], end_date.strftime('%Y-%m-%d'))
        )
        existing_record = cursor.fetchone()
        
        if not existing_record:
            cursor.execute(
                "INSERT INTO farm_ndvi_history (farm_id, date, min_ndvi, max_ndvi, mean_ndvi, median_ndvi, crop_type) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    farm['id'],
                    end_date.strftime('%Y-%m-%d'),
                    ndvi_data['ndvi_stats']['min'],
                    ndvi_data['ndvi_stats']['max'],
                    ndvi_data['ndvi_stats']['mean'],
                    ndvi_data['ndvi_stats']['median'],
                    ndvi_data['crop_type']
                )
            )
            conn.commit()
        
        # 健康状態の評価
        health_status = evaluate_ndvi_health(ndvi_data["ndvi_stats"]["mean"])
        trend = analyze_ndvi_trend(ndvi_data["history"])
        season = get_current_season()
        
        # レコメンデーションの追加
        recommendations = NDVI_MAPPING["recommendations"][health_status]
        
        # 作物固有のアドバイス
        crop_advice = NDVI_MAPPING["crops"].get(ndvi_data["crop_type"], {}).get(health_status, "")
        
        # 季節に応じたアドバイス
        seasonal_advice = NDVI_MAPPING["seasonal"][season][health_status]
        
        # 結果をまとめる
        result = {
            **ndvi_data,
            "analysis": {
                "health_status": health_status,
                "trend": trend,
                "recommendations": recommendations,
                "crop_specific_advice": crop_advice,
                "seasonal_advice": seasonal_advice
            }
        }
        
        # データベース接続を閉じる
        conn.close()
        
        return result
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return {"error": f"NDVIデータの取得に失敗しました: {str(e)}", "details": error_details}

# 追加ツール：気象データを取得するツール
@tool
def get_weather_forecast(lat: float = None, lng: float = None):
    """
    指定された緯度経度の天気予報を取得する
    
    Parameters:
    lat (float): 緯度
    lng (float): 経度
    
    Returns:
    dict: 天気予報データ
    """
    try:
        import requests
        from datetime import datetime, timedelta
        import os
        
        # APIキーを.envから取得
        api_key = os.getenv("WEATHER_API_KEY")
        
        # APIキーがない場合はモックデータを返す
        if not api_key:
            # 現在の日付を取得
            today = datetime.now()
            
            # 今後5日間の日付を生成
            forecast_dates = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(5)]
            
            # モックデータを返す
            return {
                "location": {
                    "name": "東京",
                    "lat": lat or 35.6895,
                    "lng": lng or 139.6917
                },
                "current": {
                    "date": today.strftime("%Y-%m-%d"),
                    "temp_c": 22,
                    "condition": "晴れ",
                    "humidity": 65,
                    "wind_kph": 10,
                    "precip_mm": 0
                },
                "forecast": [
                    {
                        "date": forecast_dates[0],
                        "max_temp_c": 24,
                        "min_temp_c": 18,
                        "condition": "晴れ",
                        "humidity": 60,
                        "wind_kph": 12,
                        "precip_mm": 0,
                        "chance_of_rain": 10
                    },
                    {
                        "date": forecast_dates[1],
                        "max_temp_c": 25,
                        "min_temp_c": 19,
                        "condition": "晴れ時々曇り",
                        "humidity": 65,
                        "wind_kph": 10,
                        "precip_mm": 0.5,
                        "chance_of_rain": 30
                    },
                    {
                        "date": forecast_dates[2],
                        "max_temp_c": 23,
                        "min_temp_c": 19,
                        "condition": "小雨",
                        "humidity": 75,
                        "wind_kph": 15,
                        "precip_mm": 5.2,
                        "chance_of_rain": 80
                    },
                    {
                        "date": forecast_dates[3],
                        "max_temp_c": 22,
                        "min_temp_c": 17,
                        "condition": "曇り",
                        "humidity": 70,
                        "wind_kph": 12,
                        "precip_mm": 1.0,
                        "chance_of_rain": 40
                    },
                    {
                        "date": forecast_dates[4],
                        "max_temp_c": 24,
                        "min_temp_c": 18,
                        "condition": "晴れ",
                        "humidity": 65,
                        "wind_kph": 8,
                        "precip_mm": 0,
                        "chance_of_rain": 5
                    }
                ],
                "agricultural_notes": {
                    "irrigation_needed": "3日後に雨が予測されているため、翌日までは灌水が必要です。",
                    "disease_risk": "3日後の降雨で病害発生リスクが高まる可能性があります。予防的な防除を検討してください。",
                    "working_conditions": "今日と明日は屋外作業に適した気象条件です。"
                }
            }
        
        # 実際のAPI呼び出し（WeatherAPIを使用する例）
        base_url = "http://api.weatherapi.com/v1"
        forecast_endpoint = f"{base_url}/forecast.json"
        
        params = {
            "key": api_key,
            "q": f"{lat},{lng}" if lat and lng else "Tokyo",
            "days": 5,
            "aqi": "yes",
            "alerts": "yes"
        }
        
        response = requests.get(forecast_endpoint, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            # レスポンスを整形
            formatted_data = {
                "location": {
                    "name": data["location"]["name"],
                    "lat": data["location"]["lat"],
                    "lng": data["location"]["lon"]
                },
                "current": {
                    "date": data["location"]["localtime"].split()[0],
                    "temp_c": data["current"]["temp_c"],
                    "condition": data["current"]["condition"]["text"],
                    "humidity": data["current"]["humidity"],
                    "wind_kph": data["current"]["wind_kph"],
                    "precip_mm": data["current"]["precip_mm"]
                },
                "forecast": []
            }
            
            # 5日間の予報データを整形
            for day in data["forecast"]["forecastday"]:
                formatted_data["forecast"].append({
                    "date": day["date"],
                    "max_temp_c": day["day"]["maxtemp_c"],
                    "min_temp_c": day["day"]["mintemp_c"],
                    "condition": day["day"]["condition"]["text"],
                    "humidity": day["day"].get("avghumidity", 0),  # avghumidityがない場合はデフォルト値を使用
                    "wind_kph": day["day"].get("maxwind_kph", 0),  # maxwind_kphがない場合はデフォルト値を使用
                    "precip_mm": day["day"].get("totalprecip_mm", 0),  # totalprecip_mmがない場合はデフォルト値を使用
                    "chance_of_rain": day["day"].get("daily_chance_of_rain", 0)  # daily_chance_of_rainがない場合はデフォルト値を使用
                })
            
            # 農業に関するメモを作成
            rain_days = [i for i, day in enumerate(formatted_data["forecast"]) if day["precip_mm"] > 1.0]
            
            irrigation_needed = "今後5日間は十分な降水が予測されています。" if rain_days else "今後5日間は降水量が少ないため、灌水が必要です。"
            
            if rain_days:
                disease_risk = f"{rain_days[0]+1}日後の降雨で病害発生リスクが高まる可能性があります。予防的な防除を検討してください。"
            else:
                disease_risk = "今後5日間は降水量が少ないため、病害発生リスクは低めです。"
            
            working_conditions = "今日は屋外作業に適した気象条件です。" if formatted_data["current"]["precip_mm"] < 1.0 else "雨天のため屋外作業は控えめにしてください。"
            
            formatted_data["agricultural_notes"] = {
                "irrigation_needed": irrigation_needed,
                "disease_risk": disease_risk,
                "working_conditions": working_conditions
            }
            
            return formatted_data
        else:
            # エラーメッセージにレスポンスの内容も含める
            error_message = f"天気データの取得に失敗しました。ステータスコード: {response.status_code}"
            try:
                error_details = response.json()
                error_message += f", 詳細: {error_details}"
            except:
                pass
            return {"error": error_message}
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return {"error": f"天気予報データの取得中にエラーが発生しました: {str(e)}", "details": error_details}

# 追加ツール：農作業カレンダーを取得するツール
@tool
def get_farming_calendar(crop_type: str = None, region: str = None):
    """
    特定の作物と地域の農作業カレンダーを取得する
    
    Parameters:
    crop_type (str): 作物の種類（rice, wheat, soybean, vegetables）
    region (str): 地域（北海道, 東北, 関東, 中部, 関西, 中国四国, 九州）
    
    Returns:
    dict: 農作業カレンダーのデータ
    """
    try:
        # 作物カレンダーのデータ
        calendars = {
            "rice": {
                "北海道": {
                    "1月": ["休耕期", "来年の生産計画を立てる"],
                    "2月": ["休耕期", "種子の準備"],
                    "3月": ["休耕期", "苗床の準備"],
                    "4月": ["苗床準備", "育苗開始"],
                    "5月": ["田植え", "肥料散布"],
                    "6月": ["水管理", "除草"],
                    "7月": ["水管理", "病害虫防除"],
                    "8月": ["水管理", "出穂期の管理"],
                    "9月": ["落水", "刈り取り準備"],
                    "10月": ["収穫", "乾燥・調製"],
                    "11月": ["稲わら処理", "土壌改良"],
                    "12月": ["休耕期", "機械メンテナンス"]
                },
                "東北": {
                    "1月": ["休耕期", "生産計画策定"],
                    "2月": ["休耕期", "種子消毒"],
                    "3月": ["育苗準備", "温湯種子消毒"],
                    "4月": ["育苗", "本田準備"],
                    "5月": ["田植え", "初期水管理"],
                    "6月": ["除草", "中干し"],
                    "7月": ["水管理", "病害虫防除"],
                    "8月": ["出穂期管理", "水管理"],
                    "9月": ["落水", "刈り取り準備"],
                    "10月": ["収穫", "乾燥調製"],
                    "11月": ["稲わら処理", "土づくり"],
                    "12月": ["休耕期", "農業機械整備"]
                },
                "関東": {
                    "1月": ["休耕期", "計画策定"],
                    "2月": ["休耕期", "種子準備"],
                    "3月": ["育苗準備", "種まき"],
                    "4月": ["育苗管理", "本田準備"],
                    "5月": ["田植え", "水管理"],
                    "6月": ["除草", "中干し"],
                    "7月": ["水管理", "病害虫防除"],
                    "8月": ["出穂・開花", "水管理"],
                    "9月": ["落水", "収穫準備"],
                    "10月": ["収穫", "乾燥調製"],
                    "11月": ["わら処理", "土づくり"],
                    "12月": ["休耕期", "次年度準備"]
                }
            },
            "wheat": {
                "北海道": {
                    "1月": ["雪害対策", "排水対策"],
                    "2月": ["雪害対策", "排水対策"],
                    "3月": ["融雪対策", "追肥"],
                    "4月": ["追肥", "病害虫防除"],
                    "5月": ["病害虫防除", "生育調査"],
                    "6月": ["穂肥", "赤かび病防除"],
                    "7月": ["収穫準備", "収穫"],
                    "8月": ["収穫", "わら処理"],
                    "9月": ["土づくり", "は種準備"],
                    "10月": ["は種", "基肥"],
                    "11月": ["越冬準備", "排水対策"],
                    "12月": ["越冬管理", "積雪対策"]
                }
            },
            "vegetables": {
                "関東": {
                    "1月": ["ハウス栽培", "霜対策"],
                    "2月": ["育苗", "土壌準備"],
                    "3月": ["春野菜の植付け", "土壌改良"],
                    "4月": ["春野菜の管理", "追肥"],
                    "5月": ["病害虫防除", "収穫開始"],
                    "6月": ["梅雨対策", "夏野菜の植付け"],
                    "7月": ["夏野菜の管理", "高温対策"],
                    "8月": ["かん水", "秋野菜の準備"],
                    "9月": ["秋野菜の植付け", "台風対策"],
                    "10月": ["秋野菜の管理", "収穫"],
                    "11月": ["晩秋野菜の収穫", "土づくり"],
                    "12月": ["冬野菜の管理", "霜対策"]
                }
            },
            "soybean": {
                "東北": {
                    "1月": ["休耕期", "計画策定"],
                    "2月": ["休耕期", "種子選別"],
                    "3月": ["休耕期", "土壌診断"],
                    "4月": ["圃場準備", "土壌改良"],
                    "5月": ["圃場準備", "播種準備"],
                    "6月": ["播種", "初期管理"],
                    "7月": ["中耕・培土", "病害虫防除"],
                    "8月": ["開花期管理", "病害虫防除"],
                    "9月": ["莢伸長期管理", "排水対策"],
                    "10月": ["収穫準備", "収穫"],
                    "11月": ["収穫", "乾燥調製"],
                    "12月": ["休耕期", "土づくり"]
                }
            }
        }
        
        # デフォルト値を設定
        if not crop_type:
            crop_type = "rice"
        if not region:
            region = "関東"
        
        # 指定された作物と地域のカレンダーを取得
        if crop_type in calendars:
            if region in calendars[crop_type]:
                calendar_data = calendars[crop_type][region]
            else:
                # 地域が見つからない場合は最初の地域を使用
                first_region = next(iter(calendars[crop_type]))
                calendar_data = calendars[crop_type][first_region]
                region = first_region
        else:
            # 作物が見つからない場合はコメのカレンダーを使用
            calendar_data = calendars["rice"]["関東"]
            crop_type = "rice"
            region = "関東"
        
        # 現在の月に基づいて今月と次月の作業を特定
        current_month = datetime.now().month
        current_month_str = f"{current_month}月"
        next_month = current_month + 1 if current_month < 12 else 1
        next_month_str = f"{next_month}月"
        
        # 結果の整形
        result = {
            "crop_type": crop_type,
            "region": region,
            "calendar": calendar_data,
            "current_tasks": calendar_data.get(current_month_str, ["データなし"]),
            "next_month_tasks": calendar_data.get(next_month_str, ["データなし"]),
            "season_tips": {}
        }
        
        # 季節に応じたヒントを追加
        season = get_current_season()
        if season == "spring":
            result["season_tips"] = {
                "rice": "苗の健全な生育を促すため、育苗期の温度管理に注意してください。昼夜の温度差が大きい場合は保温対策を。",
                "wheat": "春の追肥のタイミングは茎立ち期直前が最適です。窒素過多に注意して施肥量を調整してください。",
                "vegetables": "春野菜の定植後は急な低温に注意。不織布などで保護する準備をしておきましょう。",
                "soybean": "播種前の土壌水分と地温の確認が重要です。地温が15℃以上になってから播種すると発芽が良好になります。"
            }
        elif season == "summer":
            result["season_tips"] = {
                "rice": "高温期の水管理が重要です。特に開花期には深水管理を行い、受精障害を防止しましょう。",
                "wheat": "収穫時期の雨に注意。刈り遅れると品質低下を招きます。天候予報を確認して適期収穫に努めてください。",
                "vegetables": "夏野菜の収穫適期を逃さないように注意。朝夕の涼しい時間帯に収穫すると鮮度が保たれます。",
                "soybean": "開花期・莢形成期の水分ストレスは収量に大きく影響します。土壌水分をチェックし、必要に応じて灌水してください。"
            }
        elif season == "autumn":
            result["season_tips"] = {
                "rice": "収穫時期の判断は籾の黄化率で行います。適期収穫で高品質米を目指しましょう。",
                "wheat": "播種適期は地域によって異なります。適期内播種で越冬前に十分な生育量を確保しましょう。",
                "vegetables": "秋野菜の定植後は害虫対策が重要です。防虫ネットの活用や早期発見・早期防除を心がけてください。",
                "soybean": "収穫時の豆の水分含量は適正値（15%程度）を目安にしてください。刈り遅れると品質低下につながります。"
            }
        else:  # winter
            result["season_tips"] = {
                "rice": "休閑期の土づくりが翌年の収量・品質に影響します。土壌診断に基づいた土壌改良を計画的に。",
                "wheat": "積雪地域では雪腐病対策が重要です。根雪前の防除を忘れずに実施してください。",
                "vegetables": "ハウス栽培では温度管理と換気のバランスに注意。日中の温度上昇と夜間の冷え込みに対応した管理を。",
                "soybean": "次期作に向けた土壌分析と施肥設計を行う時期です。土壌診断結果に基づいた土づくりを計画しましょう。"
            }
        
        # 作物固有のヒントを追加
        result["crop_specific_tip"] = result["season_tips"].get(crop_type, "データなし")
        
        return result
    
    except Exception as e:
        return {"error": f"農作業カレンダーの取得中にエラーが発生しました: {str(e)}"}

# Step 1: Generate an AIMessage that may include a tool-call to be sent.
def query_or_respond(state: MessagesState):
    """Generate tool call for retrieval or respond."""
    llm_with_tools = model.bind_tools([retrieve, get_farm_ndvi_data, get_weather_forecast, get_farming_calendar])
    response = llm_with_tools.invoke(state["messages"])
    # MessagesState appends messages to state instead of overwriting
    return {"messages": [response]}

# Step 2: Execute the tools.
tools = ToolNode([retrieve, get_farm_ndvi_data, get_weather_forecast, get_farming_calendar])

# Step 3: Generate a response using the retrieved content.
def generate(state: MessagesState):
    """Generate answer."""
    # Get generated ToolMessages
    recent_tool_messages = []
    for message in reversed(state["messages"]):
        if message.type == "tool":
            recent_tool_messages.append(message)
        else:
            break
    tool_messages = recent_tool_messages[::-1]

    # Format into prompt
    docs_content = "\n\n".join(doc.content for doc in tool_messages)
    system_message_content = (
        "あなたは農業アドバイザーAIです。以下の情報を元に、農家の質問に丁寧に応答してください。"
        "NDVIデータに基づいて具体的なアドバイスを提供してください。"
        "回答は日本語で、農業の専門知識と衛星データの分析結果を組み合わせて行ってください。"
        "応答は簡潔かつ実用的なものにし、可能な限り数値データを含めてください。"
        "\n\n"
        f"{docs_content}"
    )
    conversation_messages = [
        message
        for message in state["messages"]
        if message.type in ("human", "system")
        or (message.type == "ai" and not message.tool_calls)
    ]
    prompt = [SystemMessage(system_message_content)] + conversation_messages

    # Run
    response = model.invoke(prompt)
    return {"messages": [response]}

from langgraph.graph import END
from langgraph.prebuilt import ToolNode, tools_condition

graph_builder.add_node(query_or_respond)
graph_builder.add_node(tools)
graph_builder.add_node(generate)

graph_builder.set_entry_point("query_or_respond")
graph_builder.add_conditional_edges(
    "query_or_respond",
    tools_condition, # 分岐条件を判断する関数
    {END: "generate", "tools": "tools"},
)
graph_builder.add_edge("tools", "generate")
graph_builder.add_edge("generate", END)

graph = graph_builder.compile()
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
graph = graph_builder.compile(checkpointer=memory)

# Specify an ID for the thread
config = {"configurable": {"thread_id": "abd153"}}

def generate_rag_response(user_input, farm_id=None, date=None):
    """
    RAGを用いた回答生成関数
    Graphを使用して回答を生成する
    
    Parameters:
    user_input (str): ユーザーの質問
    farm_id (str): 農場ID（オプション）
    date (str): 日付（オプション）
    
    Returns:
    str: 生成された回答
    """
    try:
        from flask import session, current_app
        import json
        from app.services.satellite_service import get_farm_ndvi_image
        
        # NDVIに関する質問であればフラグを設定
        is_ndvi_query = any(keyword in user_input.lower() for keyword in 
                         ['ndvi', '植生指数', '生育状況', '健康状態', '畑の状態', '作物の状態', 
                          '畑', '田んぼ', '農場', '作物', '生育', '肥料', '農薬', '栄養', '収穫'])
        
        # 天気予報に関する質問
        is_weather_query = any(keyword in user_input.lower() for keyword in 
                           ['天気', '気象', '雨', '晴れ', '気温', '湿度', '予報'])
        
        # 農場管理に関する質問
        is_management_query = any(keyword in user_input.lower() for keyword in 
                              ['管理', '施肥', '灌水', '病害虫', '除草', '間引き', '収穫時期'])
        
        # ユーザークエリの拡張
        enhanced_query = user_input
        
        # 農場データを取得してコンテキストに追加
        farm_context = ""
        with current_app.app_context():
            farms = session.get('farms', [])
            
            # 指定されたIDの農場を検索、なければ最初の農場を使用
            if farm_id:
                farm = next((f for f in farms if f['id'] == int(farm_id)), None)
            else:
                farm = farms[0] if farms else None
            
            if farm:
                farm_context = f"対象の農場: {farm['name']} (ID: {farm['id']})"
                if 'coordinates' in farm:
                    location = farm['coordinates'][0] if isinstance(farm['coordinates'], list) else farm['coordinates']
                    farm_context += f", 位置情報: 緯度 {location.get('lat', '不明')}, 経度 {location.get('lng', '不明')}"
        
        # NDVI関連の質問に対応する入力の修正
        if is_ndvi_query:
            if farm_id:
                enhanced_query += f" (農場ID: {farm_id})"
            if date:
                enhanced_query += f" (日付: {date})"
            enhanced_query += f"\n\n{farm_context}"
        
        # 会話履歴を使用して応答を生成
        # thread_idを使って会話の状態を維持
        thread_id = session.get('thread_id', f"user_{session.get('user_id', 'anonymous')}_{datetime.now().strftime('%Y%m%d%H%M%S')}")
        session['thread_id'] = thread_id
        
        config = {"configurable": {"thread_id": thread_id}}
        
        # 新しいメッセージを追加
        new_message = {"role": "user", "content": enhanced_query}
        
        # MemorySaverを使って会話履歴を取得・更新
        try:
            # 既存の会話履歴を取得
            thread_config = {"configurable": {"thread_id": thread_id}}
            current_state = memory.get(thread_id)
            
            if current_state:
                # 既存の会話履歴に新しいメッセージを追加
                current_messages = current_state["messages"]
                current_messages.append(new_message)
                response = graph.invoke({"messages": current_messages}, config=thread_config)
            else:
                # 新しい会話を開始
                response = graph.invoke({"messages": [new_message]}, config=thread_config)
        except Exception as e:
            # 会話履歴の取得に失敗した場合は新しい会話を開始
            print(f"会話履歴の取得に失敗しました: {str(e)}")
            response = graph.invoke({"messages": [new_message]}, config=thread_config)
        
        # 最後のAIメッセージを取得
        ai_message = response["messages"][-1].content
        
        return ai_message
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f"申し訳ありません。応答の生成中にエラーが発生しました: {str(e)}"