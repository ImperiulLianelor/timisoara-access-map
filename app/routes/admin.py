from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import current_user, login_required # login_required is good, current_user needed for logging
from app import db
from app.models import User, Location, Review, Photo, AdminLog
from flask_babel import gettext as _
from functools import wraps
# import os # os is now mostly handled by the utility function

# Import the new utility function for deleting images
from app.utils.image_processing import delete_image
from app.utils.image_processing import save_processed_image

admin = Blueprint('admin', __name__)


# Admin-only decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash(_('Access denied. Admin privileges required.'), 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


# Log admin action helper
def log_admin_action(action, target_type=None, target_id=None, details=""):
    log_entry_details = details
    if target_type and target_id:
        log_entry_details = f"{target_type} ID {target_id}: {details}"
    
    admin_log = AdminLog(
        admin_id=current_user.id, # Assumes current_user is available
        action=action,
        details=log_entry_details,
        ip_address=request.remote_addr
    )
    db.session.add(admin_log)
    # db.session.commit() # Commit often done after main operation succeeds


@admin.route('/')
@login_required
@admin_required
def index():
    """Admin dashboard."""
    pending_locations_count = Location.query.filter_by(is_approved=False).count()
    total_locations_count = Location.query.count()
    total_users_count = User.query.count()
    
    recent_logs_list = AdminLog.query.order_by(AdminLog.timestamp.desc()).limit(10).all()
    recent_locations_list = Location.query.order_by(Location.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html', title=_('Admin Dashboard'),
                          pending_locations=pending_locations_count, # Pass the count
                          total_locations=total_locations_count,     # Pass the count
                          total_users=total_users_count,           # Pass the count
                          recent_logs=recent_logs_list,
                          recent_locations=recent_locations_list)


@admin.route('/locations')
@login_required
@admin_required
def locations():
    """Manage all locations."""
    # Add filtering capabilities from request.args if desired for this page
    query = Location.query
    
    location_type_filter = request.args.get('type')
    status_filter = request.args.get('status')
    search_query = request.args.get('q', '').strip()

    if location_type_filter:
        query = query.filter(Location.location_type == location_type_filter)
    if status_filter == 'approved':
        query = query.filter(Location.is_approved == True)
    elif status_filter == 'pending':
        query = query.filter(Location.is_approved == False)
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(db.or_(Location.name.ilike(search_term), Location.address.ilike(search_term)))
        
    all_locations = query.order_by(Location.created_at.desc()).all() # Consider pagination for many locations
    return render_template('admin/locations.html', title=_('Manage Locations'),
                          locations=all_locations)


@admin.route('/locations/pending')
@login_required
@admin_required
def pending_locations():
    """View locations pending approval."""
    pending = Location.query.filter_by(is_approved=False).order_by(Location.created_at.desc()).all()
    return render_template('admin/pending_locations.html', title=_('Pending Locations'),
                          locations=pending)


@admin.route('/location/<int:location_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_location(location_id):
    """Approve a location."""
    location = Location.query.get_or_404(location_id)
    location.is_approved = True
    log_admin_action(
        action="location_approved", # Consistent action names
        target_type="Location", target_id=location.id,
        details=f"Approved location: {location.name}"
    )
    try:
        db.session.commit()
        flash(_('Location has been approved.'), 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error approving location {location_id}: {str(e)}", exc_info=True)
        flash(_('Error approving location.'), 'danger')
    return redirect(request.referrer or url_for('admin.pending_locations'))


@admin.route('/location/<int:location_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_location(location_id):
    """Reject and delete a location."""
    location = Location.query.get_or_404(location_id)
    location_name_for_log = location.name # Store before potential deletion issues

    # Delete associated photos from filesystem
    for photo in location.photos:
        if not delete_image(photo.filename): # Use utility, checks if deletion failed
            # Log failure but proceed with DB deletion as per original logic
             current_app.logger.warning(f"Filesystem deletion failed for {photo.filename} during rejection of location {location_id}, but DB record will be removed.")
    
    # The Photo and Review records will be cascade deleted by the DB
    # due to 'cascade="all, delete-orphan"' in Location model relationships.
    
    log_admin_action(
        action="location_rejected_deleted",
        target_type="Location", target_id=location.id,
        details=f"Rejected and deleted location: {location_name_for_log}"
    )
    try:
        db.session.delete(location)
        db.session.commit()
        flash(_('Location has been rejected and deleted.'), 'warning')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error rejecting/deleting location {location_id}: {str(e)}", exc_info=True)
        flash(_('Error rejecting location.'), 'danger')

    # Determine where to redirect based on where admin came from
    if 'pending' in request.referrer if request.referrer else '':
        return redirect(url_for('admin.pending_locations'))
    return redirect(url_for('admin.locations'))


@admin.route('/location/<int:location_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_location(location_id):
    """Edit a location's details."""
    location = Location.query.get_or_404(location_id)
    
    if request.method == 'POST':
        location.name = request.form.get('name', location.name)
        location.description = request.form.get('description', location.description)
        location.address = request.form.get('address', location.address)
        location.location_type = request.form.get('location_type', location.location_type)
        
        lat_str = request.form.get('lat')
        lng_str = request.form.get('lng')
        if lat_str and lng_str:
            try:
                location.lat = float(lat_str)
                location.lng = float(lng_str)
            except ValueError:
                flash(_('Invalid latitude or longitude format provided.'), 'danger')
                return render_template('admin/edit_locations.html', title=_('Edit Location'), location=location) # Re-render with error

        location.has_ramp = 'has_ramp' in request.form
        location.has_accessible_wc = 'has_accessible_wc' in request.form
        location.has_accessible_parking = 'has_accessible_parking' in request.form
        location.has_accessible_entrance = 'has_accessible_entrance' in request.form
        location.has_braille = 'has_braille' in request.form
        location.has_audio_guidance = 'has_audio_guidance' in request.form
        location.has_staff_assistance = 'has_staff_assistance' in request.form
        
        # Handle approval status change
        location.is_approved = 'is_approved' in request.form

        # If admin uploads new photos during edit (add this block if form has 'photos' input)
        if 'photos' in request.files:
            photo_file_storage_list = request.files.getlist('photos')
            actual_photos_to_process = [pfs for pfs in photo_file_storage_list if pfs and pfs.filename]
            if actual_photos_to_process:
                photo_description = request.form.get('photo_description', '')
                for photo_file_storage_item in actual_photos_to_process:
                    filename = save_processed_image(photo_file_storage_item) # Use the utility
                    if filename:
                        new_photo = Photo(
                            filename=filename,
                            description=photo_description,
                            location_id=location.id,
                            user_id=current_user.id # Or decide if admin edits mean admin is "uploader"
                        )
                        db.session.add(new_photo)
                    else:
                        flash(_('One or more new photos could not be processed.'), 'warning')
        
        log_admin_action(
            action="location_edited",
            target_type="Location", target_id=location.id,
            details=f"Edited location: {location.name}"
        )
        try:
            db.session.commit()
            flash(_('Location has been updated.'), 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error editing location {location_id}: {str(e)}", exc_info=True)
            flash(_('Error updating location.'), 'danger')
        return redirect(url_for('admin.locations'))
    
    return render_template('admin/edit_locations.html', title=_('Edit Location'),
                          location=location)


@admin.route('/users')
@login_required
@admin_required
def users():
    """Manage all users."""
    # Add filtering capabilities from request.args
    query = User.query
    status_filter = request.args.get('status')
    search_query = request.args.get('q', '').strip()

    if status_filter == 'active':
        query = query.filter(User.is_active == True)
    elif status_filter == 'inactive':
        query = query.filter(User.is_active == False)
    elif status_filter == 'admin':
        query = query.filter(User.is_admin == True)
    
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(db.or_(User.username.ilike(search_term), User.email.ilike(search_term)))

    all_users = query.order_by(User.username).all() # Consider pagination for many users
    return render_template('admin/users.html', title=_('Manage Users'),
                          users=all_users)


@admin.route('/user/<int:user_id>/toggle_admin', methods=['POST'])
@login_required
@admin_required
def toggle_admin(user_id):
    """Toggle admin status for a user."""
    if user_id == current_user.id:
        flash(_('You cannot change your own admin status.'), 'danger')
        return redirect(url_for('admin.users'))
    
    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin
    
    action_taken = "admin_role_granted" if user.is_admin else "admin_role_revoked"
    log_admin_action(
        action=action_taken, 
        target_type="User", target_id=user.id,
        details=f"Admin status for user '{user.username}' set to {user.is_admin}"
    )
    try:
        db.session.commit()
        flash(_('Admin status for user %(username)s has been updated to %(status)s.', username=user.username, status=user.is_admin), 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error toggling admin status for user {user_id}: {str(e)}", exc_info=True)
        flash(_('Error updating admin status.'), 'danger')
    return redirect(url_for('admin.users'))


@admin.route('/user/<int:user_id>/toggle_active', methods=['POST'])
@login_required
@admin_required
def toggle_active(user_id):
    """Toggle active status for a user."""
    if user_id == current_user.id and not User.query.get(user_id).is_active : # Prevent deactivating self
        flash(_('You cannot deactivate your own account.'), 'danger')
        return redirect(url_for('admin.users'))
    
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active

    action_taken = "user_activated" if user.is_active else "user_deactivated"
    log_admin_action(
        action=action_taken,
        target_type="User", target_id=user.id,
        details=f"Active status for user '{user.username}' set to {user.is_active}"
    )
    try:
        db.session.commit()
        status_text = _('activated') if user.is_active else _('deactivated')
        flash(_('User account %(username)s has been %(status)s.', username=user.username, status=status_text), 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error toggling active status for user {user_id}: {str(e)}", exc_info=True)
        flash(_('Error updating user active status.'), 'danger')
    return redirect(url_for('admin.users'))


@admin.route('/reviews')
@login_required
@admin_required
def reviews():
    """Manage all reviews."""
    # Add filtering/pagination if needed
    all_reviews = Review.query.order_by(Review.created_at.desc()).all()
    return render_template('admin/reviews.html', title=_('Manage Reviews'),
                          reviews=all_reviews)


@admin.route('/review/<int:review_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_review(review_id):
    """Delete a review."""
    review = Review.query.get_or_404(review_id)
    location_id_for_log = review.location_id # Store before deletion

    log_admin_action(
        action="review_deleted", 
        target_type="Review", target_id=review.id,
        details=f"Deleted review for location ID: {location_id_for_log}"
    )
    try:
        db.session.delete(review)
        db.session.commit()
        flash(_('Review has been deleted.'), 'warning')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting review {review_id}: {str(e)}", exc_info=True)
        flash(_('Error deleting review.'), 'danger')
    return redirect(request.referrer or url_for('admin.reviews'))


@admin.route('/logs')
@login_required
@admin_required
def logs():
    """View admin action logs."""
    # Add filtering by admin user, action type, date range as in your template
    page = request.args.get('page', 1, type=int)
    query = AdminLog.query

    action_filter = request.args.get('action')
    admin_id_filter = request.args.get('admin_id', type=int)
    start_date_filter = request.args.get('start_date')
    end_date_filter = request.args.get('end_date')

    if action_filter:
        query = query.filter(AdminLog.action == action_filter)
    if admin_id_filter:
        query = query.filter(AdminLog.admin_id == admin_id_filter)
    if start_date_filter:
        try:
            start_dt = datetime.strptime(start_date_filter, '%Y-%m-%d')
            query = query.filter(AdminLog.timestamp >= start_dt)
        except ValueError:
            flash(_("Invalid start date format. Please use YYYY-MM-DD."), "danger")
    if end_date_filter:
        try:
            end_dt = datetime.strptime(end_date_filter, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            query = query.filter(AdminLog.timestamp <= end_dt)
        except ValueError:
            flash(_("Invalid end date format. Please use YYYY-MM-DD."), "danger")
            
    # For admin filter dropdown in template
    admin_users = User.query.filter_by(is_admin=True).order_by(User.username).all()

    pagination = query.order_by(AdminLog.timestamp.desc()).paginate(
        page=page, per_page=current_app.config.get('ITEMS_PER_PAGE', 20), error_out=False
    )
    logs_list = pagination.items
    return render_template('admin/logs.html', title=_('Admin Logs'), logs=logs_list, admins=admin_users, pagination=pagination)


@admin.route('/photo/<int:photo_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_photo(photo_id):
    """Delete a photo."""
    photo = Photo.query.get_or_404(photo_id)
    location_id_for_log = photo.location_id
    filename_for_log = photo.filename

    # Use the utility function from app.utils.image_processing
    if delete_image(photo.filename): # This handles file deletion from filesystem
        current_app.logger.info(f"Successfully deleted image file {filename_for_log} from filesystem.")
    else:
        # Log failure but proceed with DB deletion for consistency, or decide on stricter error handling
        current_app.logger.warning(f"Filesystem deletion failed or file not found for {filename_for_log}. DB record will still be removed.")
    
    log_admin_action(
        action="photo_deleted", 
        target_type="Photo", target_id=photo.id,
        details=f"Deleted photo '{filename_for_log}' for location ID: {location_id_for_log}"
    )
    try:
        db.session.delete(photo)
        db.session.commit()
        flash(_('Photo has been deleted.'), 'warning')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting photo record {photo_id} from DB: {str(e)}", exc_info=True)
        flash(_('Error deleting photo record from database.'), 'danger')
    
    # Redirect to where the admin was, likely location edit or locations list
    return redirect(request.referrer or url_for('admin.locations'))