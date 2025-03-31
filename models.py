from datetime import datetime
from firebase_config import initialize_firebase

db = initialize_firebase()

class Category:
    collection_name = 'categories'
    
    def __init__(self, name, position=0, id=None):
        self.name = name
        self.position = position
        self.id = id
    
    @staticmethod
    def create(name, position=0):
        doc_ref = db.collection(Category.collection_name).document()
        doc_ref.set({
            'name': name,
            'position': position
        })
        return Category(name=name, position=position, id=doc_ref.id)
    
    @staticmethod
    def get_all():
        docs = db.collection(Category.collection_name).order_by('position').stream()
        return [Category(
            name=doc.get('name'),
            position=doc.get('position'),
            id=doc.id
        ) for doc in docs]
    
    @staticmethod
    def get_by_id(id):
        doc = db.collection(Category.collection_name).document(id).get()
        if doc.exists:
            return Category(
                name=doc.get('name'),
                position=doc.get('position'),
                id=doc.id
            )
        return None
    
    def delete(self):
        if self.id:
            db.collection(self.collection_name).document(self.id).delete()

class Tweet:
    collection_name = 'tweets'
    
    def __init__(self, tweet_text, author, username, timestamp, category_id,
                 media_urls=None, original_url=None, added_by=None, id=None):
        self.tweet_text = tweet_text
        self.author = author
        self.username = username
        self.timestamp = timestamp
        self.category_id = category_id
        self.media_urls = media_urls or []
        self.original_url = original_url
        self.added_by = added_by
        self.id = id
    
    @staticmethod
    def create(tweet_text, author, username, timestamp, category_id,
               media_urls=None, original_url=None, added_by=None):
        doc_ref = db.collection(Tweet.collection_name).document()
        doc_ref.set({
            'tweet_text': tweet_text,
            'author': author,
            'username': username,
            'timestamp': timestamp,
            'category_id': category_id,
            'media_urls': media_urls or [],
            'original_url': original_url,
            'added_by': added_by,
            'created_at': datetime.utcnow()
        })
        return Tweet(
            tweet_text=tweet_text,
            author=author,
            username=username,
            timestamp=timestamp,
            category_id=category_id,
            media_urls=media_urls,
            original_url=original_url,
            added_by=added_by,
            id=doc_ref.id
        )
    
    @staticmethod
    def get_by_category(category_id):
        docs = db.collection(Tweet.collection_name)\
                .where('category_id', '==', category_id)\
                .order_by('created_at', direction='DESCENDING')\
                .stream()
        return [Tweet(
            tweet_text=doc.get('tweet_text'),
            author=doc.get('author'),
            username=doc.get('username'),
            timestamp=doc.get('timestamp'),
            category_id=doc.get('category_id'),
            media_urls=doc.get('media_urls', []),
            original_url=doc.get('original_url'),
            added_by=doc.get('added_by'),
            id=doc.id
        ) for doc in docs]
    
    def delete(self):
        if self.id:
            db.collection(self.collection_name).document(self.id).delete()