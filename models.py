from extensions import db
from datetime import datetime

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)
    tweets = db.relationship('Tweet', backref='category', cascade="all, delete-orphan", lazy=True)

    def __repr__(self):
        return f'<Category {self.name}>'

class Tweet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tweet_text = db.Column(db.Text, nullable=True)
    author = db.Column(db.String(120), nullable=True)
    username = db.Column(db.String(120), nullable=True)
    timestamp = db.Column(db.String(120), nullable=True)
    media_urls = db.Column(db.Text, nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    original_url = db.Column(db.String(500), nullable=False)
    added_by = db.Column(db.String(50), nullable=False)  # Store who added the tweet
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Tweet {self.id}>'