**衛星データから画像を読み込み、NDVIや時系列予測を行うアプリケーションです。**<br>
仮想環境を構築したのちに以下のコマンドを実施してください<br>
python -m venv venv <br>
source venv/bin/activate # macOS, Linux <br>
venv\Scripts\activate # Windows <br>
pip install -r backend/requirements.txt <br>
.envファイルを作成し、その中に <br>
GOOGLE_API_KEY="" <br>
SH_CLIENT_ID="" <br>
SH_CLIENT_SECRET="" <br>
を入力してください

**以下がこのプログラムの構成内容です**
nextfarm/<br>
├── app/<br>
│   ├── __init__.py<br>
│   ├── config.py<br>
│   ├── models/<br>
│   │   └── __init__.py<br>
│   ├── routes/<br>
│   │   ├── __init__.py<br>
│   │   ├── main_routes.py<br>
│   │   ├── map_routes.py<br>
│   │   └── chatbot_routes.py<br>
│   ├── services/<br>
│   │   ├── __init__.py<br>
│   │   └── satellite_service.py<br>
│   ├── static/<br>
│   │   ├── css/<br>
│   │   │   ├── main.css<br>
│   │   │   └── map.css<br>
│   │   ├── js/<br>
│   │   │   ├── main.js<br>
│   │   │   ├── map.js<br>
│   │   │   └── chatbot.js<br>
│   │   └── images/<br>
│   ├── templates/<br>
│   │   ├── base.html<br>
│   │   ├── index.html<br>
│   │   ├── map.html<br>
│   │   └── chatbot.html<br>
├── chatbot.py  # 既存のチャットボット実装<br>
├── run.py<br>
└── requirements.txt<br>
