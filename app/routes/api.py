from flask import Blueprint, jsonify, request, current_app
from flask_login import current_user
from app import db, limiter
from app.models import Location, Photo, Review, User
from sqlalchemy import or_, and_
from datetime import datetime

api = Blueprint('api', __name__)


@api.route('/locations')
@limiter.limit("60/minute")
def get_locations():
    """Get all approved locations with optional filtering."""
    # Get filter parameters
    wheelchair = request.args.get('wheelchair') == 'true'
    visual = request.args.get('visual') == 'true'
    hearing = request.args.get('hearing') == 'true'
    cognitive = request.args.get('cognitive') == 'true'
    location_types = request.args.getlist('type')
    
    # Start with base query for approved locations
    query = Location.query.filter(Location.is_approved == True)
    
    # Apply filters
    if wheelchair:
        query = query.filter(
            or_(
                Location.has_ramp == True,
                Location.has_accessible_entrance == True,
                Location.has_accessible_parking == True
            )
        )
    
    if visual:
        query = query.filter(
            or_(
                Location.has_braille == True,
                Location.has_audio_guidance == True
            )
        )
    
    if hearing:
        query = query.filter(Location.has_audio_guidance == True)
    
    if cognitive:
        query = query.filter(Location.has_staff_assistance == True)
    
    if location_types:
        query = query.filter(Location.location_type.in_(location_types))
    
    # Get locations
    locations = query.all()
    
    # Prepare response
    result = []
    for location in locations:
        result.append({
            'id': location.id,
            'name': location.name,
            'lat': location.lat,
            'lng': location.lng,
            'address': location.address,
            'has_ramp': location.has_ramp,
            'has_accessible_wc': location.has_accessible_wc,
            'has_accessible_parking': location.has_accessible_parking,
            'has_accessible_entrance': location.has_accessible_entrance,
            'has_braille': location.has_braille,
            'has_audio_guidance': location.has_audio_guidance,
            'has_staff_assistance': location.has_staff_assistance,
            'location_type': location.location_type,
            'is_approved': location.is_approved
        })
    
    return jsonify({
        'status': 'success',
        'count': len(result),
        'locations': result
    })


@api.route('/locations/<int:location_id>')
def get_location(location_id):
    """Get details for a specific location."""
    location = Location.query.get_or_404(location_id)
    
    # Check if user can view non-approved locations
    if not location.is_approved and not current_user.is_authenticated:
        return jsonify({
            'status': 'error', 
            'message': 'Location not approved'
        }), 403
    
    # Get photos
    photos = []
    for photo in location.photos:
        photos.append({
            'id': photo.id,
            'filename': photo.filename,
            'description': photo.description
        })
    
    # Get reviews
    reviews = []
    for review in location.reviews:
        author = User.query.get(review.user_id)
        reviews.append({
            'id': review.id,
            'content': review.content,
            'rating': review.rating,
            'created_at': review.created_at.isoformat(),
            'author_id': review.user_id,
            'author_name': author.username if author else 'Unknown'
        })
    
    # Get creator info
    creator = User.query.get(location.user_id)
    
    # Build response
    response = {
        'status': 'success',
        'location': {
            'id': location.id,
            'name': location.name,
            'description': location.description,
            'lat': location.lat,
            'lng': location.lng,
            'address': location.address,
            'has_ramp': location.has_ramp,
            'has_accessible_wc': location.has_accessible_wc,
            'has_accessible_parking': location.has_accessible_parking,
            'has_accessible_entrance': location.has_accessible_entrance,
            'has_braille': location.has_braille,
            'has_audio_guidance': location.has_audio_guidance,
            'has_staff_assistance': location.has_staff_assistance,
            'location_type': location.location_type,
            'is_approved': location.is_approved,
            'created_at': location.created_at.isoformat(),
            'creator': creator.username if creator else 'Unknown',
            'photos': photos,
            'reviews': reviews
        }
    }
    
    return jsonify(response)


@api.route('/search')
@limiter.limit("30/minute")
def search_locations():
    """Search for locations by name, description, or address."""
    query = request.args.get('q', '')
    
    if len(query) < 3:
        return jsonify({
            'status': 'error',
            'message': 'Search query must be at least 3 characters'
        }), 400
    
    # Prepare search pattern
    search_pattern = f"%{query}%"
    
    # Perform search query
    locations = Location.query.filter(
        and_(
            Location.is_approved == True,
            or_(
                Location.name.ilike(search_pattern),
                Location.description.ilike(search_pattern),
                Location.address.ilike(search_pattern)
            )
        )
    ).limit(10).all()
    
    # Prepare results
    results = []
    for location in locations:
        results.append({
            'id': location.id,
            'name': location.name,
            'address': location.address,
            'lat': location.lat,
            'lng': location.lng,
            'location_type': location.location_type
        })
    
    return jsonify({
        'status': 'success',
        'results': results
    })


@api.route('/submit-location', methods=['POST'])
@limiter.limit("5/hour")
def submit_location_api():
    """API endpoint to submit a new location."""
    if not current_user.is_authenticated:
        return jsonify({
            'status': 'error',
            'message': 'Authentication required'
        }), 401
    
    # Get JSON data
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['name', 'lat', 'lng']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'status': 'error',
                'message': f'Missing required field: {field}'
            }), 400
    
    # Create new location
    location = Location(
        name=data['name'],
        description=data.get('description', ''),
        lat=float(data['lat']),
        lng=float(data['lng']),
        address=data.get('address', ''),
        location_type=data.get('location_type', ''),
        has_ramp=data.get('has_ramp', False),
        has_accessible_wc=data.get('has_accessible_wc', False),
        has_accessible_parking=data.get('has_accessible_parking', False),
        has_accessible_entrance=data.get('has_accessible_entrance', False),
        has_braille=data.get('has_braille', False),
        has_audio_guidance=data.get('has_audio_guidance', False),
        has_staff_assistance=data.get('has_staff_assistance', False),
        user_id=current_user.id,
        is_approved=current_user.is_admin  # Auto-approve if admin
    )
    
    db.session.add(location)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Location submitted successfully',
        'location_id': location.id
    })


@api.route('/add-review/<int:location_id>', methods=['POST'])
@limiter.limit("10/hour")
def add_review_api(location_id):
    """API endpoint to add a review to a location."""
    if not current_user.is_authenticated:
        return jsonify({
            'status': 'error',
            'message': 'Authentication required'
        }), 401
    
    location = Location.query.get_or_404(location_id)
    
    # Only allow reviews for approved locations
    if not location.is_approved:
        return jsonify({
            'status': 'error',
            'message': 'Cannot review unapproved locations'
        }), 403
    
    # Get JSON data
    data = request.get_json()
    
    # Validate required fields
    if 'content' not in data or 'rating' not in data:
        return jsonify({
            'status': 'error',
            'message': 'Missing required fields: content, rating'
        }), 400
    
    # Validate rating
    try:
        rating = int(data['rating'])
        if rating < 1 or rating > 5:
            raise ValueError('Rating must be between 1 and 5')
    except ValueError:
        return jsonify({
            'status': 'error',
            'message': 'Rating must be an integer between 1 and 5'
        }), 400
    
    # Create new review
    review = Review(
        content=data['content'],
        rating=rating,
        location_id=location_id,
        user_id=current_user.id
    )
    
    db.session.add(review)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Review added successfully',
        'review_id': review.id
    })


@api.route('/reports')
def get_statistics():
    """Get general statistics about the application."""
    if not current_user.is_authenticated:
        return jsonify({
            'status': 'error',
            'message': 'Authentication required'
        }), 401
    
    # Get basic statistics
    total_locations = Location.query.filter_by(is_approved=True).count()
    total_unapproved = Location.query.filter_by(is_approved=False).count()
    total_users = User.query.count()
    total_reviews = Review.query.count()
    
    # Get accessibility statistics
    wheelchair_accessible = Location.query.filter_by(is_approved=True).filter(
        or_(
            Location.has_ramp == True,
            Location.has_accessible_entrance == True
        )
    ).count()
    
    visual_accessible = Location.query.filter_by(is_approved=True).filter(
        or_(
            Location.has_braille == True,
            Location.has_audio_guidance == True
        )
    ).count()
    
    # Calculate percentages
    if total_locations > 0:
        wheelchair_percentage = round((wheelchair_accessible / total_locations) * 100)
        visual_percentage = round((visual_accessible / total_locations) * 100)
    else:
        wheelchair_percentage = 0
        visual_percentage = 0
    
    return jsonify({
        'status': 'success',
        'statistics': {
            'total_locations': total_locations,
            'pending_approval': total_unapproved,
            'total_users': total_users,
            'total_reviews': total_reviews,
            'wheelchair_accessible': wheelchair_accessible,
            'wheelchair_percentage': wheelchair_percentage,
            'visual_accessible': visual_accessible,
            'visual_percentage': visual_percentage
        }
    })
