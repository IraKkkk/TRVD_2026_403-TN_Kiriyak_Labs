from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
import re
import os
from functools import wraps

app = Flask(__name__, static_folder='static')
CORS(app)

# --- КОНФІГУРАЦІЯ ---
app.config['SECRET_KEY'] = 'university-ahub-secure-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///assets.db'

db = SQLAlchemy(app)

# --- МОДЕЛІ ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False) # Email або Login
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='Student') # Ролі: Student, Admin
    assets = db.relationship('Asset', backref='owner', lazy=True)

class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), default='Document') # Document, Source Code, Model
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# --- ВАЛІДАЦІЯ ПАРОЛЯ (Security Requirement) ---
def is_password_strong(password):
    if len(password) < 8: return False
    if not re.search("[a-z]", password): return False
    if not re.search("[A-Z]", password): return False
    if not re.search("[0-9]", password): return False
    if not re.search("[!@#$%^&*]", password): return False
    return True

# --- MIDDLEWARE (JWT Verification) ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Токен відсутній!'}), 401
        try:
            token_clean = token.split(" ")[1]
            data = jwt.decode(token_clean, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.get(data['user_id'])
        except:
            return jsonify({'message': 'Сесія закінчилася, увійдіть знову'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

# --- API ЕНДПОІНТИ ---
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not is_password_strong(password):
        return jsonify({'message': 'Пароль занадто слабкий! Мінімум 8 символів, цифра та спецсимвол.'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'message': 'Користувач вже існує'}), 400

    hashed_pw = generate_password_hash(password)
    new_user = User(username=username, password_hash=hashed_pw)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'Реєстрація успішна! Ви можете увійти.'}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data.get('username')).first()
    if user and check_password_hash(user.password_hash, data.get('password')):
        token = jwt.encode({
            'user_id': user.id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=60)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        return jsonify({'token': token})
    return jsonify({'message': 'Невірні облікові дані'}), 401

@app.route('/api/my-assets', methods=['GET'])
@token_required
def get_assets(current_user):
    assets = [{"id": a.id, "name": a.filename, "cat": a.category} for a in current_user.assets]
    return jsonify({'assets': assets, 'user': current_user.username})

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)