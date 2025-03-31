from flask import Flask, render_template, request, redirect, url_for, flash, abort, jsonify, Response
from config import Config
from werkzeug.security import check_password_hash
from functools import wraps
from firebase_config import initialize_firebase
import requests
from bs4 import BeautifulSoup
import time
import hashlib
import os
import re
from urllib.parse import urlparse
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config.from_object(Config)

# Initialize Firebase
db = initialize_firebase()

# Create media directory if it doesn't exist
MEDIA_FOLDER = os.path.join(app.static_folder, 'media')
os.makedirs(MEDIA_FOLDER, exist_ok=True)

# --- HTTP Basic Authentication ---
def check_auth(username, password):
    # Get base credentials
    if username == app.config.get("BASIC_AUTH_USERNAME"):
        return check_password_hash(app.config.get("BASIC_AUTH_PASSWORD_HASH"), password)
    
    # Check for additional numbered users (username2, username3, etc.)
    user_num = 2
    while True:
        username_key = f"BASIC_AUTH_USERNAME{user_num}"
        password_hash_key = f"BASIC_AUTH_PASSWORD_HASH{user_num}"
        
        stored_username = app.config.get(username_key)
        stored_hash = app.config.get(password_hash_key)
        
        # If we don't find the next numbered user, we're done checking
        if not stored_username or not stored_hash:
            break
            
        if username == stored_username:
            return check_password_hash(stored_hash, password)
            
        user_num += 1
    
    app.logger.info(f"No matching credentials found for username: {username}")
    return False

def authenticate():
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# --- Routes ---

@app.before_first_request
def create_tables():
    pass

@app.route("/")
@requires_auth
def index():
    # Get categories ordered by position
    categories = Category.query.order_by(Category.position).all()
    return render_template("index.html", categories=categories)

@app.route("/add_category", methods=["POST"])
@requires_auth
def add_category():
    name = request.form.get("name", "").strip()
    if name:
        # Get the highest position
        max_position = 0
        for category in Category.query.all():
            if category.position > max_position:
                max_position = category.position
        category = Category(name=name, position=max_position + 1)
        category.save()
        flash("Category added successfully.", "success")
    else:
        flash("Category name cannot be empty.", "danger")
    return redirect(url_for("index"))

@app.route("/delete_category/<int:category_id>", methods=["POST"])
@requires_auth
def delete_category(category_id):
    category = Category.get(category_id)
    category.delete()
    flash("Category deleted.", "success")
    return redirect(url_for("index"))

def download_media(url):
    """Download media from URL and save to local storage"""
    try:
        # Generate a unique filename based on URL
        url_hash = hashlib.md5(url.encode()).hexdigest()
        ext = os.path.splitext(urlparse(url).path)[1]
        if not ext:
            ext = '.jpg'  # Default to jpg if no extension found
        filename = secure_filename(f"{url_hash}{ext}")
        filepath = os.path.join(MEDIA_FOLDER, filename)
        
        # Only download if file doesn't already exist
        if not os.path.exists(filepath):
            response = requests.get(url, stream=True, timeout=10)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        # Return the local URL for the media
        return url_for('static', filename=f'media/{filename}')
    except Exception as e:
        app.logger.error(f"Error downloading media from {url}: {e}")
        return None

def delete_media(local_url):
    """Delete media file from local storage"""
    try:
        if local_url:
            filepath = os.path.join(app.root_path, 'static', local_url.split('/static/')[1])
            if os.path.exists(filepath):
                os.remove(filepath)
    except Exception as e:
        app.logger.error(f"Error deleting media file {local_url}: {e}")

@app.route("/add_tweet", methods=["POST"])
@requires_auth
def add_tweet():
    tweet_url = request.form.get("tweet_url", "").strip()
    category_id = request.form.get("category_id")
    new_category_name = request.form.get("new_category")
    
    # Decide which category to use
    if new_category_name:
        category = Category.query.filter_by(name=new_category_name).first()
        if not category:
            category = Category(name=new_category_name)
            category.save()
    elif category_id:
        category = Category.get(category_id)
    else:
        flash("No category selected or provided.", "danger")
        return redirect(url_for("index"))
    
    if tweet_url:
        # Delay to avoid overwhelming Twitter's servers.
        time.sleep(2)
        tweet_data = scrape_tweet(tweet_url)
        if tweet_data:
            # Download media files and get local URLs
            local_media_urls = []
            if tweet_data.get("media"):
                for url in tweet_data["media"]:
                    local_url = download_media(url)
                    if local_url:
                        local_media_urls.append(local_url)
            
            auth = request.authorization
            added_by = auth.username if auth else "unknown"
            
            new_tweet = Tweet(
                tweet_text=tweet_data["text"],
                author=tweet_data["author"],
                username=tweet_data["username"],
                timestamp=tweet_data["timestamp"],
                media_urls=",".join(local_media_urls) if local_media_urls else None,
                category=category,
                original_url=tweet_url,
                added_by=added_by
            )
            
            new_tweet.save()
            flash("Tweet added successfully.", "success")
        else:
            flash("Failed to fetch tweet data.", "danger")
    else:
        flash("Tweet URL cannot be empty.", "danger")
    return redirect(url_for("index"))

@app.route("/delete_tweet/<int:tweet_id>", methods=["POST"])
@requires_auth
def delete_tweet(tweet_id):
    tweet = Tweet.get(tweet_id)
    
    # Delete associated media files
    if tweet.media_urls:
        for url in tweet.media_urls.split(','):
            delete_media(url)
    
    tweet.delete()
    flash("Tweet deleted successfully.", "success")
    return redirect(url_for("index"))

@app.route("/update_category_order", methods=["POST"])
@requires_auth
def update_category_order():
    order = request.json.get("order", [])
    if order:
        try:
            # Update each category's position
            for position, category_id in enumerate(order):
                category = Category.get(int(category_id))
                if category:
                    category.position = position
                    category.save()
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    return jsonify({"success": False, "error": "No order provided"}), 400

def scrape_tweet(url):
    headers = {
        "User-Agent": "WhatsApp/2.24.1.84",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0"
    }
    try:
        app.logger.info(f"Attempting to fetch tweet from URL: {url}")
        
        # First try to get the tweet page directly
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try to find the tweet text
        tweet_text = None
        text_selectors = [
            ('div', {'data-testid': 'tweetText'}),
            ('div', {'class': 'tweet-text'}),
            ('div', {'class': 'js-tweet-text-container'}),
            ('div', {'class': 'css-901oao'}),
            ('meta', {'property': 'og:description'})
        ]
        
        for tag, attrs in text_selectors:
            element = soup.find(tag, attrs)
            if element:
                tweet_text = element.get('content', element.text).strip()
                if tweet_text:
                    break
        
        if not tweet_text:
            tweet_text = "Tweet text not found."
        
        # Try to find the author and username
        author = "Unknown"
        username = ""
        author_selectors = [
            ('div', {'data-testid': 'User-Name'}),
            ('div', {'class': 'username'}),
            ('meta', {'property': 'og:title'}),
            ('div', {'class': 'css-901oao'})
        ]
        
        for tag, attrs in author_selectors:
            element = soup.find(tag, attrs)
            if element:
                author_text = element.get('content', element.text).strip()
                if '@' in author_text:
                    parts = author_text.split(' @')
                    author = parts[0]
                    username = parts[1] if len(parts) > 1 else ""
                else:
                    author = author_text
                break
        
        # Try to find the timestamp
        timestamp = "Unknown"
        timestamp_selectors = [
            ('time', {}),
            ('span', {'class': 'timestamp'}),
            ('meta', {'property': 'article:published_time'}),
            ('time', {'datetime': True})
        ]
        
        for tag, attrs in timestamp_selectors:
            element = soup.find(tag, attrs)
            if element:
                timestamp = element.get('datetime', element.text).strip()
                if timestamp:
                    break
        
        # Try to find media
        media = []
        media_selectors = [
            ('img', {'data-testid': 'tweetPhoto'}),  # Primary tweet photos
            ('div', {'data-testid': 'tweetPhoto'}, 'img'),  # Tweet photos in containers
            ('img', {'class': 'css-9pa8cd'}),  # Modern Twitter image class
            ('div', {'class': 'AdaptiveMedia-container'}, 'img'),  # Legacy Twitter image container
        ]
        
        def is_valid_media_url(url):
            invalid_patterns = [
                'profile_images',
                '/profile/',
                'twimg.com/profile',
                'default_profile',
                'avatar',
                'emoji',
                '.svg',
                'favicon',
                'logo'
            ]
            return url and not any(pattern in url.lower() for pattern in invalid_patterns)
        
        # First try direct media in tweet
        for selector in media_selectors:
            if len(selector) == 2:
                tag, attrs = selector
                elements = soup.find_all(tag, attrs)
                for element in elements:
                    src = element.get('src', '')
                    if is_valid_media_url(src):
                        if src.startswith('//'):
                            src = 'https:' + src
                        media.append(src)
            else:
                tag, attrs, child_tag = selector
                elements = soup.find_all(tag, attrs)
                for element in elements:
                    child = element.find(child_tag)
                    if child:
                        src = child.get('src', '')
                        if is_valid_media_url(src):
                            if src.startswith('//'):
                                src = 'https:' + src
                            media.append(src)
        
        # If no media found in direct elements, try meta tags
        if not media:
            meta_selectors = [
                ('meta', {'property': 'og:image'}),
                ('meta', {'property': 'twitter:image'})
            ]
            
            for tag, attrs in meta_selectors:
                element = soup.find(tag, attrs)
                if element:
                    src = element.get('content', '')
                    if is_valid_media_url(src):
                        if src.startswith('//'):
                            src = 'https:' + src
                        media.append(src)
        
        # Remove duplicates while preserving order
        media = list(dict.fromkeys(media))
        
        result = {
            "text": tweet_text,
            "author": author,
            "username": username,
            "timestamp": timestamp,
            "media": media
        }
        
        app.logger.info("Successfully extracted tweet data:")
        app.logger.info(f"Author: {author}")
        app.logger.info(f"Username: {username}")
        app.logger.info(f"Timestamp: {timestamp}")
        app.logger.info(f"Media URLs: {media}")
        
        return result
        
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Network error while fetching tweet: {e}")
        return None
    except Exception as e:
        app.logger.error(f"Unexpected error while scraping tweet: {e}")
        return None

if __name__ == "__main__":
    app.run(debug=True)