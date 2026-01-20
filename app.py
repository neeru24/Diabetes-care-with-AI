import os
import base64
import io
import logging
import re
import sys
import joblib
import json
import warnings
from datetime import datetime, timezone
from config import Config

warnings.filterwarnings('ignore', category=UserWarning, module='sklearn')

from dotenv import load_dotenv
load_dotenv()

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import seaborn as sns

from flask import Flask, jsonify, render_template, request, make_response, session, redirect, url_for, flash
from flask_cors import CORS
from flask_mail import Mail, Message
from flask_babel import Babel, gettext as _
from flask_login import LoginManager, login_user, current_user, logout_user, login_required
from flask_bcrypt import Bcrypt

from models import db, Post, User, PredictionHistory
import google.generativeai as genai

# ---------------- APP SETUP ----------------

app = Flask(__name__)
app.config.from_object(Config)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///forum.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
with app.app_context():
    db.create_all()

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

CORS(app)

# ---------------- LANGUAGE SETUP ----------------

SUPPORTED_LANGUAGES = {
    'en': 'English',
    'es': 'Español',
    'hi': 'हिन्दी',
    'fr': 'Français',
    'zh': '中文'
}
DEFAULT_LANGUAGE = 'en'

app.config['BABEL_DEFAULT_LOCALE'] = DEFAULT_LANGUAGE
app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'

babel = Babel(app)

def get_locale():
    user_language = request.cookies.get('language')
    if user_language in SUPPORTED_LANGUAGES:
        return user_language
    return request.accept_languages.best_match(SUPPORTED_LANGUAGES.keys()) or DEFAULT_LANGUAGE

babel.init_app(app, locale_selector=get_locale)

@app.context_processor
def inject_i18n_context():
    return {
        'languages': SUPPORTED_LANGUAGES,
        'current_language': get_locale(),
        'current_year': datetime.now().year,
        'current_user': current_user
    }

@app.route('/api/set-language', methods=['POST'])
def set_language():
    data = request.get_json()
    language = data.get('language')
    if language not in SUPPORTED_LANGUAGES:
        return jsonify({'error': 'Unsupported language'}), 400
    response = make_response(jsonify({'success': True}))
    response.set_cookie('language', language, max_age=365*24*60*60, samesite='Lax')
    return response

# ---------------- MAIL ----------------

app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')

mail = Mail(app)

# ---------------- MODEL LOAD ----------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models", "diabetes_model.pkl")
SCALER_PATH = os.path.join(BASE_DIR, "models", "scaler.pkl")

try:
    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
except:
    model = scaler = None

try:
    df = pd.read_csv('diabetes.csv')
except:
    df = None

# ---------------- GEMINI FIX ----------------
# ❌ REMOVED genai.Client()
# ✅ Correct API usage

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def get_gemini_response(prompt):
    try:
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(prompt)
        return response.text
    except:
        return "Gemini service unavailable."

# ---------------- ROUTES ----------------

@app.route('/')
def root():
    return render_template('home.html')

@app.route('/index')
def home():
    return render_template('index.html')

# ---------------- AUTH (ONLY ONE SET) ----------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.form
        user = User.query.filter_by(email=data.get('email')).first()
        if user and bcrypt.check_password_hash(user.password, data.get('password')):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash("Invalid credentials", "danger")
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        hashed = bcrypt.generate_password_hash(request.form.get('password')).decode('utf-8')
        user = User(username=request.form.get('username'),
                    email=request.form.get('email'),
                    password=hashed)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('root'))

@app.route('/dashboard')
@login_required
def dashboard():
    predictions = PredictionHistory.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', predictions=predictions)

# ---------------- PREDICTION ----------------

@app.route('/predict', methods=['POST'])
def predict():
    try:
        features = [float(request.form.get(f, 0)) for f in [
            'Pregnancies','Glucose','BloodPressure','SkinThickness',
            'Insulin','BMI','DiabetesPedigreeFunction','Age'
        ]]
        if model is None or scaler is None:
            return render_template('index.html', prediction_text="Model not available")

        result = model.predict(scaler.transform([features]))[0]
        text = "Diabetic" if result == 1 else "Not Diabetic"
        return render_template('index.html', prediction_text=text)
    except:
        return render_template('index.html', prediction_text="Error")

# ---------------- CHATBOT ----------------

@app.route('/generate', methods=['POST'])
def generate():
    user_input = request.json.get('message')
    reply = get_gemini_response(user_input)
    return jsonify({'reply': reply})

# ---------------- RUN ----------------

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
