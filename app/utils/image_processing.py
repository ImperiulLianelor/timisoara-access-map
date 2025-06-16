"""
Image processing utilities for handling uploaded images.
"""
from flask import current_app
from werkzeug.utils import secure_filename
from PIL import Image, ExifTags # Ensure ExifTags is imported
import os
import uuid
# import io # io is not strictly needed for the FileStorage object from Flask

# Helper function for auto-rotation (can be within this file or imported if in another util)
def auto_rotate_image(image_obj):
    """
    Automatically rotates a Pillow Image object based on its EXIF orientation tag.
    Logs the operations for debugging.
    """
    try:
        exif = image_obj._getexif()
        if exif is None:
            current_app.logger.debug("No EXIF data found in image.")
            return image_obj

        orientation_tag_id = None
        for tag_id, tag_name in ExifTags.TAGS.items():
            if tag_name == 'Orientation':
                orientation_tag_id = tag_id
                break
        
        if orientation_tag_id is None or orientation_tag_id not in exif:
            current_app.logger.debug("EXIF Orientation tag not found.")
            return image_obj

        orientation = exif[orientation_tag_id]
        current_app.logger.debug(f"Image EXIF Orientation Value: {orientation}")

        if orientation == 1: # Normal
            current_app.logger.debug("Image orientation is normal (1). No rotation needed.")
            return image_obj
        elif orientation == 2: # Mirror horizontal
            image_obj = image_obj.transpose(Image.FLIP_LEFT_RIGHT)
            current_app.logger.debug("Applied EXIF Orientation: FLIP_LEFT_RIGHT (2)")
        elif orientation == 3: # Rotate 180
            image_obj = image_obj.rotate(180)
            current_app.logger.debug("Applied EXIF Orientation: ROTATE_180 (3)")
        elif orientation == 4: # Mirror vertical
            image_obj = image_obj.rotate(180).transpose(Image.FLIP_LEFT_RIGHT) # or image_obj.transpose(Image.FLIP_TOP_BOTTOM)
            current_app.logger.debug("Applied EXIF Orientation: ROTATE_180 & FLIP_LEFT_RIGHT (4)")
        elif orientation == 5: # Mirror horizontal and rotate 270 CW (90 CCW)
            image_obj = image_obj.rotate(90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)
            current_app.logger.debug("Applied EXIF Orientation: ROTATE_90_EXPAND & FLIP_LEFT_RIGHT (5)")
        elif orientation == 6: # Rotate 270 CW (90 CCW)
            image_obj = image_obj.rotate(90, expand=True) # Pillow rotates CCW, so 90 for 270 CW
            current_app.logger.debug("Applied EXIF Orientation: ROTATE_90_EXPAND (6)")
        elif orientation == 7: # Mirror horizontal and rotate 90 CW
            image_obj = image_obj.rotate(-90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)
            current_app.logger.debug("Applied EXIF Orientation: ROTATE_270_EXPAND & FLIP_LEFT_RIGHT (7)")
        elif orientation == 8: # Rotate 90 CW
            image_obj = image_obj.rotate(-90, expand=True) # Pillow rotates CCW, so -90 for 90 CW
            current_app.logger.debug("Applied EXIF Orientation: ROTATE_270_EXPAND (8)")
        else:
            current_app.logger.debug(f"Unknown EXIF Orientation value: {orientation}. No rotation applied.")

    except (AttributeError, KeyError, IndexError, TypeError) as e:
        current_app.logger.warning(f"Could not process EXIF orientation due to error: {str(e)}. Proceeding with original image orientation.")
    except Exception as e: # Catch any other unexpected errors during EXIF processing
        current_app.logger.error(f"Unexpected error during EXIF auto-rotation: {str(e)}. Proceeding with original image orientation.")
    
    return image_obj


def save_processed_image(file_storage, directory=None, max_width=1200, quality=85):
    """
    Process (rotates, resizes, converts) and save an uploaded image.
    
    Args:
        file_storage: The uploaded FileStorage object from Flask (e.g., request.files['photo'])
        directory: Optional custom directory (defaults to app's UPLOAD_FOLDER)
        max_width: Maximum width for the image (default 1200px)
        quality: JPEG compression quality (default 85)
        
    Returns:
        str: The saved filename or None if failed
    """
    if not file_storage or file_storage.filename == '':
        current_app.logger.info("No file or filename provided to save_uploaded_image.")
        return None
    
    original_filename = secure_filename(file_storage.filename)
    
    # Basic check for allowed extensions (can be more robust)
    allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg'})
    if not ('.' in original_filename and original_filename.rsplit('.', 1)[1].lower() in allowed_extensions):
        current_app.logger.warning(f"File type not allowed for '{original_filename}'. Allowed: {allowed_extensions}")
        return None

    try:
        img = Image.open(file_storage.stream)
        current_app.logger.debug(f"Successfully opened image stream for '{original_filename}'. Original mode: {img.mode}, size: {img.size}")

        # 1. Auto-rotate based on EXIF
        img = auto_rotate_image(img) # Call the auto-rotation helper

        # 2. Convert to RGB if it has an alpha channel or is palette-based
        # This ensures consistency and prepares for JPEG saving if applicable.
        if img.mode in ('RGBA', 'LA', 'P'):
            current_app.logger.debug(f"Image '{original_filename}' mode is {img.mode}. Attempting conversion to RGB.")
            # For P mode (palette-based) with transparency, convert to RGBA first to preserve transparency data for masking.
            if img.mode == 'P' and 'transparency' in img.info:
                img = img.convert('RGBA')
            
            if img.mode == 'RGBA' or img.mode == 'LA':
                # Create a white background image for pasting
                background = Image.new('RGB', img.size, (255, 255, 255))
                # Determine the alpha channel index
                # RGBA: R=0, G=1, B=2, A=3
                # LA: L=0, A=1
                alpha_channel_index = img.mode.index('A') # Gets the index of 'A' in 'RGBA' or 'LA'
                
                # Ensure the image actually has that many channels (robustness)
                if len(img.split()) > alpha_channel_index:
                    mask = img.split()[alpha_channel_index]
                    background.paste(img, (0, 0), mask=mask) # Ensure (0,0) for paste position
                    img = background
                    current_app.logger.debug(f"Converted '{original_filename}' from {img.mode if 'mode' in locals() and img.mode else 'previous mode'} to RGB using alpha mask.")
                else: # Should not happen if mode is RGBA/LA, but good to handle
                    img = img.convert('RGB')
                    current_app.logger.debug(f"Converted '{original_filename}' from {img.mode if 'mode' in locals() and img.mode else 'previous mode'} to RGB directly (alpha channel not found in split).")
            else: # If P mode without detectable transparency, or other modes we want to force to RGB
                img = img.convert('RGB')
                current_app.logger.debug(f"Converted '{original_filename}' from {img.mode} to RGB.")
        
        # 3. Resize if too large (maintaining aspect ratio)
        if img.width > max_width:
            current_app.logger.debug(f"Image '{original_filename}' width {img.width}px > max_width {max_width}px. Resizing.")
            ratio = max_width / float(img.width)
            new_height = int(float(img.height) * ratio)
            try:
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                current_app.logger.debug(f"Resized '{original_filename}' to {max_width}x{new_height}")
            except Exception as resize_err:
                current_app.logger.error(f"Error during resizing '{original_filename}': {str(resize_err)}")
                return None # Critical error during resize

        # Generate unique filename
        ext = original_filename.rsplit('.', 1)[1].lower()
        new_filename = f"{uuid.uuid4().hex}.{ext}"
        
        upload_path_root = directory or current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_path_root, exist_ok=True)
        file_path = os.path.join(upload_path_root, new_filename)
        
        # 4. Save the processed image
        # For JPEGs, 'quality' and 'optimize' are relevant.
        # For PNGs, 'optimize' is relevant; 'quality' is typically for palettized PNGs (mode P).
        save_options = {'optimize': True}
        if ext in ['jpg', 'jpeg']:
            save_options['quality'] = quality
        elif ext == 'png':
            # For PNG, 'quality' is not standard, but 'compress_level' (0-9) can be used.
            # Optimize is generally good.
            pass 

        img.save(file_path, **save_options)
        current_app.logger.info(f"Successfully processed and saved image as '{file_path}'")
        
        return new_filename
        
    except Exception as e:
        current_app.logger.error(f"General error processing image '{original_filename}': {str(e)}", exc_info=True) # Add exc_info for traceback
        return None


def create_thumbnail(source_filename, size=(200, 200), directory=None):
    """
    Create a thumbnail version of an existing image.
    
    Args:
        source_filename: The original image filename (should be in the upload_path)
        size: Thumbnail dimensions as (width, height) tuple
        directory: Optional custom directory (defaults to app's UPLOAD_FOLDER)
        
    Returns:
        str: The thumbnail filename or None if failed
    """
    try:
        upload_path_root = directory or current_app.config['UPLOAD_FOLDER']
        source_path = os.path.join(upload_path_root, source_filename)
        
        if not os.path.exists(source_path):
            current_app.logger.error(f"Source file for thumbnail not found: {source_path}")
            return None

        name, ext = os.path.splitext(source_filename)
        thumb_filename = f"{name}_thumb{ext}"
        thumb_path = os.path.join(upload_path_root, thumb_filename)
        
        img = Image.open(source_path)
        
        # Preserve aspect ratio with thumbnail
        img.thumbnail(size, Image.Resampling.LANCZOS)
        
        # If original was RGBA (e.g. PNG with transparency), thumbnail might still be.
        # If saving thumb as JPEG, ensure it's RGB.
        if ext.lower() in ['jpg', 'jpeg'] and img.mode != 'RGB':
             if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                alpha_channel_index = img.mode.index('A')
                if len(img.split()) > alpha_channel_index:
                    mask = img.split()[alpha_channel_index]
                    background.paste(img, (0,0), mask=mask)
                    img = background
                else:
                    img = img.convert('RGB')
             else:
                img = img.convert('RGB')

        save_options = {'optimize': True}
        if ext.lower() in ['jpg', 'jpeg']:
             save_options['quality'] = 80 # Slightly lower quality for thumbnails often acceptable

        img.save(thumb_path, **save_options)
        current_app.logger.info(f"Created thumbnail: {thumb_path}")
        
        return thumb_filename
    except Exception as e:
        current_app.logger.error(f"Error creating thumbnail for '{source_filename}': {str(e)}", exc_info=True)
        return None


def delete_image(filename, directory=None):
    """
    Delete an image file and its thumbnail if it exists.
    
    Args:
        filename: The image filename to delete
        directory: Optional custom directory (defaults to app's UPLOAD_FOLDER)
        
    Returns:
        bool: True if deletion was successful or file didn't exist, False if an error occurred.
    """
    deleted_main = False
    deleted_thumb = False
    upload_path_root = directory or current_app.config['UPLOAD_FOLDER']
    
    try:
        file_path = os.path.join(upload_path_root, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            current_app.logger.info(f"Deleted image file: {file_path}")
            deleted_main = True
        else:
            current_app.logger.warning(f"Attempted to delete main image, but not found: {file_path}")
            deleted_main = True # Considered success if not found

        name, ext = os.path.splitext(filename)
        thumb_filename = f"{name}_thumb{ext}"
        thumb_path = os.path.join(upload_path_root, thumb_filename)
        
        if os.path.exists(thumb_path):
            os.remove(thumb_path)
            current_app.logger.info(f"Deleted thumbnail file: {thumb_path}")
            deleted_thumb = True
        else:
            # No warning needed if thumb just doesn't exist
            deleted_thumb = True # Considered success if not found

        return deleted_main and deleted_thumb
    except Exception as e:
        current_app.logger.error(f"Error deleting image '{filename}' or its thumbnail: {str(e)}", exc_info=True)
        return False