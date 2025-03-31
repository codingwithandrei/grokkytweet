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
import logging
from google.cloud.firestore import FieldPath

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

try:
    # Initialize Firebase
    db = initialize_firebase()
    logger.info("Firebase initialized successfully")
except Exception as e:
    logger.error(f"Error initializing Firebase: {str(e)}")
    db = None

# Define MEDIA_FOLDER for both environments
MEDIA_FOLDER = os.path.join(app.static_folder, 'media')

# Only create media directory in development, not on Vercel
if not os.getenv('VERCEL') and not app.config.get('TESTING'):
    try:
        os.makedirs(MEDIA_FOLDER, exist_ok=True)
    except OSError:
        logger.warning("Could not create media directory - continuing without it")

# --- HTTP Basic Authentication ---
def check_auth(username, password):
    try:
        # Get base credentials for user1
        if username == app.config.get("BASIC_AUTH_USERNAME1"):
            return check_password_hash(app.config.get("BASIC_AUTH_PASSWORD_HASH1"), password)
        
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
        
        logger.info(f"No matching credentials found for username: {username}")
        return False
    except Exception as e:
        logger.error(f"Error in authentication: {str(e)}")
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

@app.route("/")
@requires_auth
def index():
    try:
        # Get categories ordered by position from Firestore
        categories_ref = db.collection('categories').order_by('position').stream()
        categories = []
        
        for cat_doc in categories_ref:
            category = {"id": cat_doc.id, **cat_doc.to_dict(), "tweets": []}
            
            # Get tweets for this category
            tweets_ref = db.collection('tweets').where('category', '==', cat_doc.id).stream()
            category["tweets"] = [{"id": tweet.id, **tweet.to_dict()} for tweet in tweets_ref]
            
            categories.append(category)
            
        return render_template("index.html", categories=categories)
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        return f"An error occurred while loading categories. Please try again. Error: {str(e)}", 500

@app.before_first_request
def create_tables():
    pass

@app.route("/add_category", methods=["POST"])
@requires_auth
def add_category():
    try:
        name = request.form.get("name", "").strip()
        if name:
            # Get the highest position
            max_position = 0
            categories_ref = db.collection('categories').stream()
            for category in categories_ref:
                if category.to_dict().get('position', 0) > max_position:
                    max_position = category.to_dict().get('position', 0)
            category_ref = db.collection('categories').document()
            category_ref.set({
                'name': name,
                'position': max_position + 1
            })
            flash("Category added successfully.", "success")
        else:
            flash("Category name cannot be empty.", "danger")
        return redirect(url_for("index"))
    except Exception as e:
        logger.error(f"Error in add_category route: {str(e)}")
        return "An error occurred while adding category. Please try again.", 500

@app.route("/delete_category/<int:category_id>", methods=["POST"])
@requires_auth
def delete_category(category_id):
    try:
        category_ref = db.collection('categories').document(str(category_id))
        category_ref.delete()
        flash("Category deleted.", "success")
        return redirect(url_for("index"))
    except Exception as e:
        logger.error(f"Error in delete_category route: {str(e)}")
        return "An error occurred while deleting category. Please try again.", 500

def download_media(url):
    """Download media from URL and save to storage"""
    if not url:
        return None

    try:
        # Generate a unique filename
        filename = secure_filename(hashlib.md5(url.encode()).hexdigest())
        
        # If running on Vercel or can't write to filesystem, return original URL
        if os.getenv('VERCEL') or app.config.get('TESTING'):
            return url
            
        # Local development: try to save file to disk
        try:
            local_path = os.path.join(MEDIA_FOLDER, filename)
            if not os.path.exists(local_path):
                response = requests.get(url)
                if response.status_code == 200:
                    with open(local_path, 'wb') as f:
                        f.write(response.content)
                    return f'/static/media/{filename}'
            else:
                return f'/static/media/{filename}'
        except OSError:
            # If we can't write to filesystem, fall back to original URL
            logger.warning(f"Could not save media to disk, using original URL: {url}")
            return url
    except Exception as e:
        logger.error(f"Error in download_media: {str(e)}")
        return url

def delete_media(local_url):
    """Delete media file from storage"""
    if not local_url:
        return
        
    # If running on Vercel or testing, no need to delete
    if os.getenv('VERCEL') or app.config.get('TESTING'):
        return
        
    try:
        # Local development: try to delete from disk
        if local_url.startswith('/static/media/'):
            filename = local_url.split('/')[-1]
            file_path = os.path.join(MEDIA_FOLDER, filename)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    logger.warning(f"Could not delete media file: {file_path}")
    except Exception as e:
        logger.error(f"Error in delete_media: {str(e)}")

@app.route("/add_tweet", methods=["POST"])
@requires_auth
def add_tweet():
    try:
        tweet_url = request.form.get("tweet_url", "").strip()
        category_id = request.form.get("category_id")
        new_category_name = request.form.get("new_category")
        
        # Decide which category to use
        if new_category_name:
            category_ref = db.collection('categories').where('name', '==', new_category_name).stream()
            category = next(category_ref, None)
            if not category:
                category_ref = db.collection('categories').document()
                category_ref.set({
                    'name': new_category_name,
                    'position': 0
                })
                category = category_ref
        elif category_id:
            category_ref = db.collection('categories').document(str(category_id))
            category = category_ref.get()
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
                
                tweet_ref = db.collection('tweets').document()
                tweet_ref.set({
                    'tweet_text': tweet_data["text"],
                    'author': tweet_data["author"],
                    'username': tweet_data["username"],
                    'timestamp': tweet_data["timestamp"],
                    'media_urls': ",".join(local_media_urls) if local_media_urls else None,
                    'category': category.id,
                    'original_url': tweet_url,
                    'added_by': added_by
                })
                
                flash("Tweet added successfully.", "success")
            else:
                flash("Failed to fetch tweet data.", "danger")
        else:
            flash("Tweet URL cannot be empty.", "danger")
        return redirect(url_for("index"))
    except Exception as e:
        logger.error(f"Error in add_tweet route: {str(e)}")
        return "An error occurred while adding tweet. Please try again.", 500

@app.route("/delete_tweet/<int:tweet_id>", methods=["POST"])
@requires_auth
def delete_tweet(tweet_id):
    try:
        tweet_ref = db.collection('tweets').document(str(tweet_id))
        tweet = tweet_ref.get()
        
        # Delete associated media files
        if tweet.to_dict().get('media_urls'):
            for url in tweet.to_dict().get('media_urls').split(','):
                delete_media(url)
        
        tweet_ref.delete()
        flash("Tweet deleted successfully.", "success")
        return redirect(url_for("index"))
    except Exception as e:
        logger.error(f"Error in delete_tweet route: {str(e)}")
        return "An error occurred while deleting tweet. Please try again.", 500

@app.route("/update_category_order", methods=["POST"])
@requires_auth
def update_category_order():
    try:
        order = request.json.get("order", [])
        if order:
            # Update each category's position
            for position, category_id in enumerate(order):
                category_ref = db.collection('categories').document(str(category_id))
                category_ref.update({
                    'position': position
                })
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "No order provided"}), 400
    except Exception as e:
        logger.error(f"Error in update_category_order route: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

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
        logger.info(f"Attempting to fetch tweet from URL: {url}")
        
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
        
        logger.info("Successfully extracted tweet data:")
        logger.info(f"Author: {author}")
        logger.info(f"Username: {username}")
        logger.info(f"Timestamp: {timestamp}")
        logger.info(f"Media URLs: {media}")
        
        return result
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while fetching tweet: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error while scraping tweet: {e}")
        return None

if __name__ == "__main__":
    app.run(debug=True)