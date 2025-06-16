"""
Form and data validation utilities.
"""
from flask import current_app
from flask_babel import lazy_gettext as _l
from wtforms.validators import ValidationError
import re
import os


def validate_location_coordinates(form, field):
    """
    Validate that coordinates are within Timisoara city bounds.
    """
    try:
        value = float(field.data)
        if field.name == 'lat':
            # Validate latitude is within Timisoara bounds
            if not (45.70 <= value <= 45.80):
                raise ValidationError(_l('Latitude must be within Timisoara city limits.'))
        elif field.name == 'lng':
            # Validate longitude is within Timisoara bounds
            if not (21.10 <= value <= 21.35):
                raise ValidationError(_l('Longitude must be within Timisoara city limits.'))
    except (ValueError, TypeError):
        raise ValidationError(_l('Coordinates must be valid decimal numbers.'))


def validate_image_file(form, field):
    """
    Validate uploaded image files.
    - Check file extension
    - Check file size
    """
    if not field.data:
        return
    
    # For multiple file uploads (ListField)
    files = field.data if isinstance(field.data, list) else [field.data]
    
    for file in files:
        if not file or file.filename == '':
            continue
            
        # Check file extension
        ext = os.path.splitext(file.filename)[1].lower()[1:]
        if ext not in current_app.config['ALLOWED_EXTENSIONS']:
            raise ValidationError(_l('Only %(allowed)s files are allowed.', 
                                   allowed=', '.join(current_app.config['ALLOWED_EXTENSIONS'])))
        
        # Check file size (5MB limit by default)
        if len(file.read()) > current_app.config['MAX_CONTENT_LENGTH']:
            file.seek(0)  # Reset file pointer after reading
            raise ValidationError(_l('File size exceeds the %(size)sMB limit.', 
                                   size=current_app.config['MAX_CONTENT_LENGTH']/(1024*1024)))
        
        file.seek(0)  # Reset file pointer after reading


def validate_password_strength(form, field):
    """
    Validate password strength requirements:
    - At least 8 characters
    - Contains at least one digit
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    """
    password = field.data
    
    if len(password) < 8:
        raise ValidationError(_l('Password must be at least 8 characters long.'))
    
    if not re.search(r'\d', password):
        raise ValidationError(_l('Password must contain at least one digit.'))
    
    if not re.search(r'[A-Z]', password):
        raise ValidationError(_l('Password must contain at least one uppercase letter.'))
    
    if not re.search(r'[a-z]', password):
        raise ValidationError(_l('Password must contain at least one lowercase letter.'))


def validate_rating(form, field):
    """
    Validate that a rating is between 1 and 5 stars.
    """
    try:
        rating = int(field.data)
        if not (1 <= rating <= 5):
            raise ValidationError(_l('Rating must be between 1 and 5 stars.'))
    except (ValueError, TypeError):
        raise ValidationError(_l('Rating must be a number between 1 and 5.'))
