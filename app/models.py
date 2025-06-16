from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login_manager


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Accessibility preferences
    needs_wheelchair = db.Column(db.Boolean, default=False)
    needs_visual_assistance = db.Column(db.Boolean, default=False)
    needs_hearing_assistance = db.Column(db.Boolean, default=False)
    needs_cognitive_assistance = db.Column(db.Boolean, default=False)
    preferred_language = db.Column(db.String(2), default='ro')  # 'ro' or 'en'
    
    # Relationships
    locations = db.relationship('Location', backref='author', lazy='dynamic')
    reviews = db.relationship('Review', backref='author', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))


class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    address = db.Column(db.String(200))
    
    # Accessibility features
    has_ramp = db.Column(db.Boolean, default=False)
    has_accessible_wc = db.Column(db.Boolean, default=False)
    has_accessible_parking = db.Column(db.Boolean, default=False)
    has_accessible_entrance = db.Column(db.Boolean, default=False)
    has_braille = db.Column(db.Boolean, default=False)
    has_audio_guidance = db.Column(db.Boolean, default=False)
    has_staff_assistance = db.Column(db.Boolean, default=False)
    
    # Status and meta
    is_approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Type of location
    location_type = db.Column(db.String(50))  # restaurant, museum, public building, etc.
    
    # Relationships
    photos = db.relationship('Photo', backref='location', lazy='dynamic', cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='location', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Location {self.name} @ {self.lat}, {self.lng}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'lat': self.lat,
            'lng': self.lng,
            'address': self.address,
            'accessibility': {
                'ramp': self.has_ramp,
                'accessible_wc': self.has_accessible_wc,
                'accessible_parking': self.has_accessible_parking,
                'accessible_entrance': self.has_accessible_entrance,
                'braille': self.has_braille,
                'audio_guidance': self.has_audio_guidance,
                'staff_assistance': self.has_staff_assistance
            },
            'location_type': self.location_type,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(128), nullable=False)
    description = db.Column(db.String(200))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f'<Photo {self.filename}>'


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f'<Review {self.id} by User {self.user_id} for Location {self.location_id}>'


# Administrative action logging
class AdminLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    admin = db.relationship('User', backref='admin_logs')
    
    def __repr__(self):
        return f'<AdminLog {self.action} by {self.admin_id} at {self.timestamp}>'
