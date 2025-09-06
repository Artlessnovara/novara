import os
from werkzeug.utils import secure_filename
from flask import current_app
from models import PlatformSetting, ChatRoom, ChatRoomMember, User
from extensions import db
from sqlalchemy import or_, and_
from sqlalchemy.orm import aliased

def save_chat_file(file):
    """
    Saves a file uploaded in the chat.
    Validates file type and returns the saved path and original filename.
    """
    allowed_extensions = {'pdf', 'doc', 'docx', 'png', 'jpg', 'jpeg', 'gif', 'mp3', 'wav', 'ogg', 'webm'}
    original_filename = secure_filename(file.filename)

    if '.' not in original_filename or original_filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        return None, None # Invalid file type

    random_hex = os.urandom(8).hex()
    _, f_ext = os.path.splitext(original_filename)
    new_filename = random_hex + f_ext

    filepath = os.path.join(current_app.root_path, 'static/chat_files', new_filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    try:
        file.save(filepath)
    except Exception as e:
        print(f"Error saving file: {e}")
        return None, None

    # Return the path relative to the static folder and the original filename
    return os.path.join('chat_files', new_filename), original_filename

BANNED_WORDS = {'profanity', 'badword', 'censorthis'} # Example list

def save_chat_room_cover_image(file):
    """Saves a cover image for a chat room."""
    allowed_extensions = {'png', 'jpg', 'jpeg'}
    max_size = 2 * 1024 * 1024 # 2MB

    filename = secure_filename(file.filename)
    if '.' not in filename or filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        return None

    # Check file size
    file.seek(0, os.SEEK_END)
    file_length = file.tell()
    if file_length > max_size:
        return None
    file.seek(0) # Reset file pointer

    random_hex = os.urandom(8).hex()
    _, f_ext = os.path.splitext(filename)
    new_filename = random_hex + f_ext

    upload_folder = os.path.join(current_app.root_path, 'static/chat_room_covers')
    os.makedirs(upload_folder, exist_ok=True)

    filepath = os.path.join(upload_folder, new_filename)
    file.save(filepath)

    return os.path.join('chat_room_covers', new_filename)


def save_editor_image(file):
    """Saves an image from the CKEditor upload, returns URL and error."""
    allowed_extensions = {'png', 'jpg', 'jpeg'}
    max_size = 2 * 1024 * 1024 # 2MB

    filename = secure_filename(file.filename)
    if '.' not in filename or filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        return None, "Invalid file type. Allowed: jpg, jpeg, png."

    # Check file size
    file.seek(0, os.SEEK_END)
    file_length = file.tell()
    if file_length > max_size:
        return None, "File is too large. Maximum size is 2MB."
    file.seek(0) # Reset file pointer

    random_hex = os.urandom(8).hex()
    _, f_ext = os.path.splitext(filename)
    new_filename = random_hex + f_ext

    upload_folder = os.path.join(current_app.root_path, 'static/uploads/images')
    os.makedirs(upload_folder, exist_ok=True)

    filepath = os.path.join(upload_folder, new_filename)
    file.save(filepath)

    from flask import url_for
    url = url_for('static', filename=os.path.join('uploads/images', new_filename))
    return url, None

def filter_profanity(text):
    if not text:
        return text
    words = text.split()
    # This is a simple implementation. A more robust one would handle punctuation.
    censored_words = [word if word.lower() not in BANNED_WORDS else '***' for word in words]
    return ' '.join(censored_words)

def save_status_file(file):
    """Saves an image for a status update."""
    allowed_extensions = {'png', 'jpg', 'jpeg', 'webm', 'mp3', 'mp4', 'ogg'}
    max_size = 10 * 1024 * 1024 # 10MB for audio/video

    filename = secure_filename(file.filename)
    if '.' not in filename or filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        return None

    file.seek(0, os.SEEK_END)
    file_length = file.tell()
    if file_length > max_size:
        return None
    file.seek(0)

    random_hex = os.urandom(8).hex()
    _, f_ext = os.path.splitext(filename)
    new_filename = random_hex + f_ext

    upload_folder = os.path.join(current_app.root_path, 'static/status_files')
    os.makedirs(upload_folder, exist_ok=True)

    filepath = os.path.join(upload_folder, new_filename)
    file.save(filepath)

    return os.path.join('status_files', new_filename)

def get_or_create_platform_setting(key, default_value):
    """Gets a platform setting or creates it with a default value if it doesn't exist."""
    setting = PlatformSetting.query.filter_by(key=key).first()
    if not setting:
        setting = PlatformSetting(key=key, value=default_value)
        db.session.add(setting)
        db.session.commit()
    return setting

def is_contact(user1_id, user2_id):
    """Checks if two users share a private chat room."""
    if user1_id == user2_id:
        return True # A user is always their own contact

    member1 = aliased(ChatRoomMember)
    member2 = aliased(ChatRoomMember)

    room = db.session.query(ChatRoom).join(member1, member1.chat_room_id == ChatRoom.id)\
        .join(member2, member2.chat_room_id == ChatRoom.id)\
        .filter(
            ChatRoom.room_type == 'private',
            or_(
                and_(member1.user_id == user1_id, member2.user_id == user2_id),
                and_(member1.user_id == user2_id, member2.user_id == user1_id)
            )
        ).first()

    return room is not None

def get_or_create_private_room(user1_id, user2_id):
    """Finds an existing private room or creates a new one."""
    member1 = aliased(ChatRoomMember)
    member2 = aliased(ChatRoomMember)

    room = db.session.query(ChatRoom).join(member1, member1.chat_room_id == ChatRoom.id)\
        .join(member2, member2.chat_room_id == ChatRoom.id)\
        .filter(
            ChatRoom.room_type == 'private',
            or_(
                and_(member1.user_id == user1_id, member2.user_id == user2_id),
                and_(member1.user_id == user2_id, member2.user_id == user1_id)
            )
        ).first()

    if room:
        return room

    # If no room exists, create one
    user1 = User.query.get_or_404(user1_id)
    user2 = User.query.get_or_404(user2_id)
    new_room = ChatRoom(
        name=f"Private Chat between {user1.name} and {user2.name}",
        room_type='private',
        created_by_id=user1_id
    )
    db.session.add(new_room)
    db.session.flush()

    member1_obj = ChatRoomMember(chat_room_id=new_room.id, user_id=user1_id)
    member2_obj = ChatRoomMember(chat_room_id=new_room.id, user_id=user2_id)
    db.session.add_all([member1_obj, member2_obj])
    db.session.commit()

    return new_room

def save_post_media(file):
    """
    Saves an image or video for a post.
    """
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'webm', 'ogg'}
    max_size = 50 * 1024 * 1024 # 50MB

    filename = secure_filename(file.filename)
    if '.' not in filename or filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        return None, None # Invalid file type

    file.seek(0, os.SEEK_END)
    file_length = file.tell()
    if file_length > max_size:
        return None, None # File too large
    file.seek(0)

    random_hex = os.urandom(8).hex()
    _, f_ext = os.path.splitext(filename)
    new_filename = random_hex + f_ext

    upload_folder = os.path.join(current_app.root_path, 'static/post_media')
    os.makedirs(upload_folder, exist_ok=True)

    filepath = os.path.join(upload_folder, new_filename)
    file.save(filepath)

    media_type = 'image' if f_ext.lower() in ['.png', 'jpg', 'jpeg', '.gif'] else 'video'

    return os.path.join('post_media', new_filename), media_type

def save_community_cover_image(file):
    """Saves a cover image for a community."""
    allowed_extensions = {'png', 'jpg', 'jpeg'}
    max_size = 2 * 1024 * 1024 # 2MB

    filename = secure_filename(file.filename)
    if '.' not in filename or filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        return None

    # Check file size
    file.seek(0, os.SEEK_END)
    file_length = file.tell()
    if file_length > max_size:
        return None
    file.seek(0) # Reset file pointer

    random_hex = os.urandom(8).hex()
    _, f_ext = os.path.splitext(filename)
    new_filename = random_hex + f_ext

    upload_folder = os.path.join(current_app.root_path, 'static/community_covers')
    os.makedirs(upload_folder, exist_ok=True)

    filepath = os.path.join(upload_folder, new_filename)
    file.save(filepath)

    return os.path.join('community_covers', new_filename)
