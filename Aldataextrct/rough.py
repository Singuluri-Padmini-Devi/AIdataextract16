from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from werkzeug.utils import secure_filename
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length
import pytesseract
from PIL import Image
import os
import json
import fitz
import pdfplumber
import csv
import nltk
from nltk.tokenize import word_tokenize

nltk.download('punkt')

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'your_secret_key'  # Change this to a random secret key for security

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User data and authentication management
users = {}

class User(UserMixin):
    def __init__(self, username):
        self.username = username

    def get_id(self):
        return self.username

@login_manager.user_loader
def load_user(username):
    return User(username) if username in users else None

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=25)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6, max=35)])
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=25)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6, max=35)])
    submit = SubmitField('Register')

# Configuration
UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'tiff', 'jfif', 'webp', 'bmp', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_image(image_path):
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image, config='--psm 6')
        return text
    except Exception as e:
        return str(e)

def extract_text_pymupdf(pdf_path):
    text = ''
    try:
        pdf_document = fitz.open(pdf_path)
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            page_text = page.get_text()
            if page_text:
                text += page_text + "\n"
    except Exception as e:
        return f"Error extracting text with PyMuPDF: {e}"
    return text

def extract_text_and_tables_pdfplumber(pdf_path):
    text = ''
    tables = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                page_tables = page.extract_tables()
                for table in page_tables:
                    tables.append(table)
    except Exception as e:
        return f"Error extracting text and tables with pdfplumber: {e}", []
    return text, tables

def save_tables_as_csv(tables, filename):
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            for table in tables:
                for row in table:
                    writer.writerow(row)
                writer.writerow([])
    except Exception as e:
        return f"Error saving tables to CSV: {e}"

def extract_text_from_pdf(pdf_path):
    text_pymupdf = extract_text_pymupdf(pdf_path)
    text_pdfplumber, tables = extract_text_and_tables_pdfplumber(pdf_path)
    combined_text = f"--- PyMuPDF Extraction ---\n{text_pymupdf.strip()}\n\n--- pdfplumber Extraction ---\n{text_pdfplumber.strip()}"
    if not combined_text.strip():
        combined_text = "No text extracted from the PDF."
    return combined_text, tables

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        if filename.lower().endswith('.pdf'):
            combined_text, tables = extract_text_from_pdf(file_path)
            csv_filename = os.path.splitext(filename)[0] + '_tables.csv'
            csv_file_path = os.path.join(app.config['UPLOAD_FOLDER'], csv_filename)
            save_tables_as_csv(tables, csv_file_path)
            return jsonify({
                'text': combined_text,
                'csv': csv_filename
            })
        else:
            text = extract_text_from_image(file_path)
            tokens = word_tokenize(text)
            json_output = json.dumps({'text': text, 'tokens': tokens}, indent=4)
            return jsonify({
                'text': text,
                'json': json_output
            })
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        if username in users and users[username] == password:
            user = User(username)
            login_user(user)
            return redirect(url_for('index'))
        return render_template('login.html', form=form, error='Invalid username or password')
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        if username in users:
            return render_template('register.html', form=form, error='Username already exists')
        users[username] = password
        user = User(username)
        login_user(user)
        return redirect(url_for('index'))
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
