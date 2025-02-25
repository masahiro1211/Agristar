病害虫予測プログラムです。<br>

仮想環境を構築したのちに以下のコマンドを実施してください<br>
python -m venv venv <br>
source venv/bin/activate # macOS, Linux <br>
venv\Scripts\activate # Windows <br>
pip install -r backend/requirements.txt <br>

**以下がこのプログラムの構成内容です**
nextfarm/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── models/
│   │   └── __init__.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── main_routes.py
│   │   ├── map_routes.py
│   │   └── chatbot_routes.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── satellite_service.py
│   ├── static/
│   │   ├── css/
│   │   │   ├── main.css
│   │   │   └── map.css
│   │   ├── js/
│   │   │   ├── main.js
│   │   │   ├── map.js
│   │   │   └── chatbot.js
│   │   └── images/
│   │       ├── logo.png
│   │       └── ndvi_samples/
│   │           ├── sample_ndvi_latest.png
│   │           ├── sample_ndvi_20240220.png
│   │           └── sample_ndvi_20240210.png
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── map.html
│   │   └── chatbot.html
│   └── utils/
│       ├── __init__.py
│       └── helpers.py
├── chatbot.py  # 既存のチャットボット実装
├── run.py
└── requirements.txt