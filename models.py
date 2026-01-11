from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

# This is the 'db' object app.py is trying to import
db = SQLAlchemy()

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    topic = db.Column(db.String(50))
    author_id = db.Column(db.String(50), default='anonymous')
    parent_id = db.Column(db.Integer, nullable=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "content": self.content,
            "topic": self.topic,
            "author_id": self.author_id,
            "parent_id": self.parent_id,
            "timestamp": self.timestamp.isoformat() + 'Z'
        }