from flask import Flask

def create_app():
    app = Flask(__name__)
    
    # 設定の読み込み
    from app.config import Config
    app.config.from_object(Config)
    
    # ルートの登録
    from app.routes.main_routes import main
    from app.routes.map_routes import map_bp
    from app.routes.chatbot_routes import chatbot_bp
    
    app.register_blueprint(main)
    app.register_blueprint(map_bp)
    app.register_blueprint(chatbot_bp)
    
    return app