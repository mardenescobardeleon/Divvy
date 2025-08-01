from flask import Flask
from flask_cors import CORS
from .routes.party import party_bp
from .extensions import db
from .routes.receipt import receipt_bp


def create_app():
    app = Flask(__name__)
    CORS(app)

    app.config['SECRET_KEY'] = 'super-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///divvy.db'

    db.init_app(app)

    from .routes.auth import auth_bp
    from .routes.friends import friends_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(friends_bp, url_prefix='/friends')
    app.register_blueprint(party_bp, url_prefix='/party')
    app.register_blueprint(receipt_bp, url_prefix='/receipt')

    with app.app_context():
        db.create_all()

    return app
