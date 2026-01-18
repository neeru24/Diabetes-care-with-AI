from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone

# Initialize the database
db = SQLAlchemy()

# ----------------------------
# 1. NEW: User Model (For Auth)
# ----------------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    
    # Relationships
    # Link to predictions (One User -> Many Predictions)
    predictions = db.relationship('Prediction', backref='author', lazy=True)
    
    # (Optional) Future-proofing: You can link posts to users later
    # posts = db.relationship('Post', backref='writer', lazy=True)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"

# ----------------------------
# 2. NEW: Prediction Model (For History)
# ----------------------------
class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Store the input data to show in history
    glucose = db.Column(db.Integer, nullable=False)
    bmi = db.Column(db.Float, nullable=False)
    age = db.Column(db.Integer, nullable=False)
    
    # Store the result ("Diabetic" / "Not Diabetic")
    result = db.Column(db.String(20), nullable=False)
    
    # Date of prediction
    date_posted = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Foreign Key: Links this prediction to a specific User
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Prediction('{self.result}', '{self.date_posted}')"

# ----------------------------
# 3. EXISTING: Post Model (Forum)
# ----------------------------
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    topic = db.Column(db.String(50))
    # Note: Currently author_id is a String (e.g., 'anonymous'). 
    # In a future L2 update, we can change this to a ForeignKey linking to User.id
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