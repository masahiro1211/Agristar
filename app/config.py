import os
from dotenv import load_dotenv

# .envファイルから環境変数をロード
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-for-nextfarm'
    SATELLITE_DATA_PATH = os.path.join(os.path.dirname(__file__), 'static/images/ndvi_samples')