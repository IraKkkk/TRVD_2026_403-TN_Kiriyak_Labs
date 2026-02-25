from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

# Налаштування бази даних (файл database.db створиться сам)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///assets.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
db = SQLAlchemy(app)

# Модель Користувача
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    assets = db.relationship('Asset', backref='owner', lazy=True)

# Модель Асета (файл, який завантажують)
class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False) # 2D, 3D, Звуки тощо
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Створення бази даних
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    categories = ['2D Model', '3D Model', 'Sounds', 'Animations', 'Textures']
    return render_template('index.html', categories=categories)

if __name__ == '__main__':
    app.run(debug=True)