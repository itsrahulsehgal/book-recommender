from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import openai
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///D:/book-recommendation/instance/books.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key' 
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

openai.api_key = os.getenv('OPENAI_API_KEY')

# Database models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    preferences = db.relationship('Preference', backref='user', lazy=True)

class Preference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    genre = db.Column(db.String(50))
    author = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    author = db.Column(db.String(80), nullable=False)
    genre = db.Column(db.String(50), nullable=False)

def add_sample_books():
    sample_books = [
        {'title': 'Book1', 'author': 'Author1', 'genre': 'Fiction'},
        {'title': 'Book2', 'author': 'Author2', 'genre': 'Mystery'},
    ]

    for book_data in sample_books:
        existing_book = Book.query.filter_by(title=book_data['title']).first()
        if not existing_book:
            book = Book(title=book_data['title'], author=book_data['author'], genre=book_data['genre'])
            db.session.add(book)

    db.session.commit()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the username already exists
        existing_user = User.query.filter_by(username=username).first()

        if existing_user:
            flash('Username already exists. Please choose a different one.', 'error')
            return redirect(url_for('register'))

        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            login_user(user)
            return redirect(url_for('set_preferences'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html')

#logout route under development 
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

def update_user_preferences(user, genre, author):
    # Check if the user already has preferences
    if user.preferences:
        # If preferences exist, update them
        user.preferences[0].genre = genre
        user.preferences[0].author = author
    else:
        # If no preferences exist, create a new Preference
        preference = Preference(genre=genre, author=author, user_id=user.id)
        db.session.add(preference)

    db.session.commit()

def fetch_and_render_recommendations(user):
    recommendations = get_book_recommendations(user)
    print("Recommendations:", recommendations) 
    return render_template('recommendations.html', recommendations=recommendations)

@app.route('/set_preferences', methods=['GET', 'POST'])
@login_required
def set_preferences():
    user = current_user

    if request.method == 'POST':
        genre = request.form['genre']
        author = request.form['author']
        update_user_preferences(user, genre, author)
        return fetch_and_render_recommendations(user)

    return render_template('preferences.html', user=user)

def get_book_recommendations(user):
    print("Inside get_book_recommendations function")

    user_preferences = [f"{preference.genre} by {preference.author}" for preference in user.preferences]
    prompt = f"Based on my preferences in {', '.join(user_preferences)}, recommend me a book."

    try:
        response = openai.Completion.create(
            model="gpt-3.5-turbo-instruct",
            prompt=prompt,
            max_tokens=300,  
            n=3,  
        )

        print("GPT-3 Response:", response)

        recommended_books = response['choices'][0]['text'].strip().split('\n')
        recommendations = [
            {
                'title': book,
                'author': preference.author,
                'genre': preference.genre
            } for book, preference in zip(recommended_books, user.preferences)
        ]

        return recommendations

    except Exception as e:
        print(f"Error in GPT-3 request: {str(e)}")
        return []

if __name__ == '__main__':
    app.run(debug=True)
