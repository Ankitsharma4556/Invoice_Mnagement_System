import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))
import os
wkhtmltopdf_path = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
os.environ['WKHTMLTOPDF_PATH'] = wkhtmltopdf_path
from flask import Flask
from config import config
from models import db
from flask_login import LoginManager
from flask_migrate import Migrate
from logging.config import dictConfig

migrate = Migrate()
login_manager = LoginManager()

def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)

    from routes import blueprint
    app.register_blueprint(blueprint)

    configure_logging(app)

    return app

def configure_logging(app):
    dictConfig({
        'version': 1,
        'formatters': {'default': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        }},
        'handlers': {'wsgi': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://flask.logging.wsgi_errors_stream',
            'formatter': 'default'
        }},
        'root': {
            'level': 'INFO' if app.config['ENV'] == 'production' else 'DEBUG',
            'handlers': ['wsgi']
        }
    })

if __name__ == '__main__':
    app = create_app(os.getenv('FLASK_CONFIG') or 'default')
    with app.app_context():
        db.create_all()
    app.run(debug=True)