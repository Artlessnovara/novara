import firebase_admin
from firebase_admin import credentials, messaging
import os
from models import User

def initialize_firebase():
    """
    Initializes the Firebase Admin SDK using credentials from an environment variable.
    """
    cred_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if cred_path:
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                print("Firebase Admin SDK initialized successfully.")
        except Exception as e:
            print(f"Error initializing Firebase Admin SDK: {e}")
    else:
        print("GOOGLE_APPLICATION_CREDENTIALS environment variable not set. Push notifications will be disabled.")

def send_push_notification(user_id, title, body, data=None):
    """
    Sends a push notification to a specific user.
    """
    if not firebase_admin._apps:
        # Silently fail if Firebase is not initialized
        return

    user = User.query.get(user_id)
    if not user or not user.fcm_tokens:
        return

    registration_tokens = [token.token for token in user.fcm_tokens]

    if not registration_tokens:
        return

    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=data or {},
        tokens=registration_tokens,
    )

    try:
        response = messaging.send_multicast(message)
        print(f'Successfully sent message to {response.success_count} devices.')
        if response.failure_count > 0:
            responses = response.responses
            failed_tokens = []
            for idx, resp in enumerate(responses):
                if not resp.success:
                    failed_tokens.append(registration_tokens[idx])
            print(f'List of failed tokens: {failed_tokens}')
    except Exception as e:
        print(f"Error sending push notification: {e}")
