from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)

# --- КОНФІГУРАЦІЯ ---
app.config['SECRET_KEY'] = 'your-secret-key-123' # Потрібно для роботи сесій
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///assets.db'
app.config['UPLOAD_FOLDER'] = 'uploads'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' # Куди перенаправляти неавторизованих

# ---------------------------------------------------------
# 1. ШАР ДОСТУПУ ДО ДАНИХ (MODELS)
# ---------------------------------------------------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    assets = db.relationship('Asset', backref='owner', lazy=True)

class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------------------------------------------------
# 2. DTO (Data Transfer Objects)
# ---------------------------------------------------------

class AssetDTO:
    def __init__(self, asset):
        self.id = asset.id
        self.name = asset.filename
        self.category = asset.category
        self.date = asset.upload_date.strftime("%Y-%m-%d %H:%M")

# ---------------------------------------------------------
# 3. СЕРВІСНИЙ ШАР (BUSINESS LOGIC)
# ---------------------------------------------------------

class AuthService:
    @staticmethod
    def register(username, password):
        if User.query.filter_by(username=username).first():
            return False
        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, password_hash=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        return True

    @staticmethod
    def login(username, password):
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return True
        return False

class AssetService:
    @staticmethod
    def get_user_assets(user_id):
        assets = Asset.query.filter_by(user_id=user_id).all()
        return [AssetDTO(a) for a in assets]

    @staticmethod
    def save_new_asset(file, category, user_id):
        if file and category:
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            new_asset = Asset(filename=filename, category=category, user_id=user_id)
            db.session.add(new_asset)
            db.session.commit()
            return AssetDTO(new_asset)
        return None

# ---------------------------------------------------------
# 4. КОНТРОЛЕРИ (ROUTES)
# ---------------------------------------------------------

@app.route('/')
@login_required # Тепер головна сторінка тільки для залогінених
def index():
    categories = ['2D Model', '3D Model', 'Sounds', 'Animations', 'Textures']
    assets = AssetService.get_user_assets(user_id=current_user.id)
    return render_template('index.html', categories=categories, assets=assets, user=current_user)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if AuthService.register(request.form.get('username'), request.form.get('password')):
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if AuthService.login(request.form.get('username'), request.form.get('password')):
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    file = request.files.get('asset_file')
    category = request.form.get('category')
    result = AssetService.save_new_asset(file, category, current_user.id)
    return redirect(url_for('index'))

# Створення бази
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)