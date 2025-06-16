from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import current_user, login_required
from app import db, limiter
from app.models import Location, Photo, Review, User
# werkzeug.utils.secure_filename is used within save_processed_image
from flask_babel import gettext as _
# os and uuid are used within save_processed_image
from datetime import datetime

from app.utils.image_processing import save_processed_image


main = Blueprint('main', __name__)


@main.route('/')
def index():
    """Main page with the map."""
    current_year = datetime.now().year
    return render_template('index.html', title=_('Accessible Timisoara'),
                           map_config=current_app.config.get('MAP_BOUNDS'),
                           current_year=current_year)


@main.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page."""
    if request.method == 'POST':
        # This block handles updates from the "Account Settings" form in profile.html
        # which posts back to this same '/profile' URL.
        original_email = current_user.email
        original_language = current_user.preferred_language

        new_email = request.form.get('email', original_email).strip()
        new_language = request.form.get('preferred_language', original_language)

        profile_updated = False

        if new_email != original_email:
            if not new_email: # Email cannot be empty
                flash(_('Email address cannot be empty.'), 'danger')
            elif User.query.filter(User.email == new_email, User.id != current_user.id).first():
                flash(_('That email address is already in use by another account.'), 'danger')
            else:
                current_user.email = new_email
                profile_updated = True
        
        if new_language != original_language:
            if new_language in current_app.config.get('LANGUAGES', ['ro', 'en']):
                current_user.preferred_language = new_language
                from flask import session # Import session here if not globally available
                session['language'] = new_language # Update session immediately
                profile_updated = True
            else:
                flash(_('Invalid language selected.'), 'danger')
        
        if profile_updated:
            try:
                db.session.commit()
                flash(_('Your account settings have been updated.'), 'success')
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error updating profile for user {current_user.id}: {str(e)}", exc_info=True)
                flash(_('An error occurred while updating your profile.'), 'danger')
        elif not any(f.errors for f in [request.form.get('email_error_field'), request.form.get('language_error_field')] if f): # Crude check if any errors were flashed for these specific fields by a form object if you had one
             # Only flash "no changes" if no other errors specific to these fields were flashed
             if new_email == original_email and new_language == original_language:
                 pass # No changes made, no message needed, or a "No changes detected" message
                 
        return redirect(url_for('main.profile'))

    # GET request part
    user_locations = Location.query.filter_by(user_id=current_user.id).order_by(Location.created_at.desc()).all()
    current_year = datetime.now().year
    return render_template('user/profile.html', title=_('My Profile'),
                           user=current_user, locations=user_locations, current_year=current_year)


@main.route('/submit-location', methods=['GET', 'POST'])
@login_required
@limiter.limit("10/day")
def submit_location():
    """Submit a new accessible location."""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        lat_str = request.form.get('lat')
        lng_str = request.form.get('lng')
        address = request.form.get('address')
        location_type = request.form.get('location_type')

        has_ramp = 'has_ramp' in request.form
        has_accessible_wc = 'has_accessible_wc' in request.form
        has_accessible_parking = 'has_accessible_parking' in request.form
        has_accessible_entrance = 'has_accessible_entrance' in request.form
        has_braille = 'has_braille' in request.form
        has_audio_guidance = 'has_audio_guidance' in request.form
        has_staff_assistance = 'has_staff_assistance' in request.form

        if not all([name, lat_str, lng_str]):
            flash(_('Name, Latitude, and Longitude are required.'), 'danger')
            return redirect(url_for('main.submit_location'))

        try:
            lat = float(lat_str)
            lng = float(lng_str)
        except ValueError:
            flash(_('Invalid Latitude or Longitude format.'), 'danger')
            return redirect(url_for('main.submit_location'))

   

        location = Location(
            name=name,
            description=description,
            lat=lat,
            lng=lng,
            address=address,
            location_type=location_type,
            has_ramp=has_ramp,
            has_accessible_wc=has_accessible_wc,
            has_accessible_parking=has_accessible_parking,
            has_accessible_entrance=has_accessible_entrance,
            has_braille=has_braille,
            has_audio_guidance=has_audio_guidance,
            has_staff_assistance=has_staff_assistance,
            user_id=current_user.id,
            is_approved=current_user.is_admin
        )

        db.session.add(location)
        try:
            db.session.commit()
            current_app.logger.info(f"Location '{location.name}' (ID: {location.id}) saved to DB by user {current_user.id}")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error saving location to DB: {str(e)}", exc_info=True)
            flash(_('An error occurred while saving the location. Please try again.'), 'danger')
            return redirect(url_for('main.submit_location'))

        processed_photo_count = 0
        any_photo_processing_failed = False

        if 'photos' in request.files:
            photo_file_storage_list = request.files.getlist('photos')
            actual_photos_to_process = [pfs for pfs in photo_file_storage_list if pfs and pfs.filename]

            if actual_photos_to_process:
                photo_description = request.form.get('photo_description', '')
                for photo_file_storage_item in actual_photos_to_process:
                    current_app.logger.debug(f"Attempting to process photo: {photo_file_storage_item.filename} for location ID {location.id}")
                    filename = save_processed_image(photo_file_storage_item)
                    
                    if filename:
                        current_app.logger.info(f"Photo '{photo_file_storage_item.filename}' processed into '{filename}' for location ID {location.id}")
                        new_photo = Photo(
                            filename=filename,
                            description=photo_description,
                            location_id=location.id,
                            user_id=current_user.id
                        )
                        db.session.add(new_photo)
                        processed_photo_count += 1
                    else:
                        any_photo_processing_failed = True
                        current_app.logger.warning(f"Failed to process photo: {photo_file_storage_item.filename} for location ID {location.id}")
                
                if processed_photo_count > 0 or (any_photo_processing_failed and actual_photos_to_process):
                    try:
                        db.session.commit()
                        current_app.logger.info(f"{processed_photo_count} photos committed for location ID {location.id}")
                    except Exception as e:
                        db.session.rollback()
                        current_app.logger.error(f"Error saving photos to DB for location ID {location.id}: {str(e)}", exc_info=True)
                        any_photo_processing_failed = True 

        if any_photo_processing_failed:
            flash(_('Location submitted. However, one or more images could not be processed or saved. You can try editing the location to add photos later.'), 'warning')
        else:
            flash(_('Thank you! Your location has been submitted and will be reviewed shortly.'), 'success')
        
        return redirect(url_for('main.index'))
    
    current_year = datetime.now().year
    return render_template('location/submit.html', title=_('Submit Location'), current_year=current_year)


@main.route('/location/<int:location_id>')
def location_details(location_id):
    """View details of a specific location."""
    location = Location.query.get_or_404(location_id)

    can_view_unapproved = False
    if current_user.is_authenticated:
        if current_user.is_admin or location.user_id == current_user.id:
            can_view_unapproved = True

    if not location.is_approved and not can_view_unapproved:
        flash(_('This location is not yet approved or you do not have permission to view it.'), 'warning')
        return redirect(url_for('main.index'))

    reviews = Review.query.filter_by(location_id=location_id).order_by(Review.created_at.desc()).all()
    current_year = datetime.now().year

    return render_template('location/details.html', title=location.name,
                           location=location, reviews=reviews, current_year=current_year)


@main.route('/location/<int:location_id>/review', methods=['POST'])
@login_required
@limiter.limit("5/hour")
def add_review(location_id):
    """Add a review for a location."""
    location = Location.query.get_or_404(location_id)

    if not location.is_approved:
        flash(_('You cannot review a location that has not been approved yet.'), 'warning')
        return redirect(url_for('main.location_details', location_id=location_id))

    content = request.form.get('content')
    rating_str = request.form.get('rating')

    if not content or not rating_str:
        flash(_('Both review text and rating are required.'), 'danger')
        return redirect(url_for('main.location_details', location_id=location_id) + "#reviews") # Stay on page

    try:
        rating = int(rating_str)
        if not (1 <= rating <= 5):
            raise ValueError("Rating out of range 1-5")
    except ValueError:
        flash(_('Invalid rating value. Please select 1 to 5 stars.'), 'danger')
        return redirect(url_for('main.location_details', location_id=location_id) + "#reviews") # Stay on page

    review = Review(
        content=content,
        rating=rating,
        location_id=location_id,
        user_id=current_user.id
    )

    db.session.add(review)
    try:
        db.session.commit()
        flash(_('Your review has been added. Thank you for contributing!'), 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving review for location {location_id} by user {current_user.id}: {str(e)}", exc_info=True)
        flash(_('An error occurred while saving your review. Please try again.'), 'danger')
        
    return redirect(url_for('main.location_details', location_id=location_id) + "#reviews")


@main.route('/dashboard')
@login_required
def dashboard():
    """User dashboard with their contributions and saved locations."""
    user_locations = Location.query.filter_by(user_id=current_user.id).order_by(Location.created_at.desc()).all()
    user_reviews = Review.query.filter_by(user_id=current_user.id).order_by(Review.created_at.desc()).all()
    current_year = datetime.now().year

    return render_template('user/dashboard.html', title=_('My Dashboard'),
                           locations=user_locations, reviews=user_reviews, current_year=current_year)


@main.route('/update-preferences', methods=['POST'])
@login_required
def update_preferences():
    """Update user accessibility preferences."""
    current_user.needs_wheelchair = 'needs_wheelchair' in request.form
    current_user.needs_visual_assistance = 'needs_visual_assistance' in request.form
    current_user.needs_hearing_assistance = 'needs_hearing_assistance' in request.form
    current_user.needs_cognitive_assistance = 'needs_cognitive_assistance' in request.form

    try:
        db.session.commit()
        flash(_('Your accessibility preferences have been updated.'), 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating preferences for user {current_user.id}: {str(e)}", exc_info=True)
        flash(_('An error occurred while updating your preferences.'), 'danger')
        
    return redirect(url_for('main.profile'))


@main.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password."""
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if not current_user.check_password(current_password):
        flash(_('Current password is incorrect.'), 'danger')
        return redirect(url_for('main.profile'))

    # Basic server-side validation for new password
    if not new_password:
        flash(_('New password cannot be empty.'), 'danger')
        return redirect(url_for('main.profile'))
    
    # Example minimum length (you can use validators.py logic here too for consistency)
    MIN_PASSWORD_LENGTH = 8 
    if len(new_password) < MIN_PASSWORD_LENGTH:
        flash(_('New password must be at least %(length)s characters long.', length=MIN_PASSWORD_LENGTH), 'danger')
        return redirect(url_for('main.profile'))
        
    if new_password != confirm_password:
        flash(_('New passwords do not match.'), 'danger')
        return redirect(url_for('main.profile'))



    current_user.set_password(new_password)
    try:
        db.session.commit()
        flash(_('Your password has been updated.'), 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error changing password for user {current_user.id}: {str(e)}", exc_info=True)
        flash(_('An error occurred while updating your password.'), 'danger')
        
    return redirect(url_for('main.profile'))

