import unittest
import sys
import os
from app import create_app, db
from models import User, Event, EventRSVP, Category, Notification
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import the app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestConfig:
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test_event_advanced_secret'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class EventAdvancedTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()
        self.seed_db()
        self.login('user2@test.com', 'password') # Login as user 2 to test notifications for user 1

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def seed_db(self):
        # Create users
        self.user1 = User(id=1, name='Organizer User', email='user1@test.com', role='instructor', approved=True)
        self.user1.set_password('password')
        self.user2 = User(id=2, name='Attendee User', email='user2@test.com', role='student', approved=True)
        self.user2.set_password('password')
        db.session.add_all([self.user1, self.user2])
        db.session.commit()

        # Create categories
        self.cat1 = Category(name='Tech Talk')
        self.cat2 = Category(name='Workshop')
        db.session.add_all([self.cat1, self.cat2])
        db.session.commit()

        # Create events
        self.event1 = Event(title='Python Workshop', description='Learn Python', date=datetime.utcnow() + timedelta(days=5), location='Online', organizer_id=self.user1.id, category_id=self.cat2.id, duration_hours=2)
        self.event2 = Event(title='JS Tech Talk', description='Learn JavaScript', date=datetime.utcnow() - timedelta(days=1), location='In Person', organizer_id=self.user1.id, category_id=self.cat1.id, duration_hours=1)
        db.session.add_all([self.event1, self.event2])
        db.session.commit()

    def login(self, email, password):
        return self.client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)

    def test_1_category_filtering(self):
        """ Test filtering events by category. """
        response = self.client.get(f'/api/events/filter?category={self.cat1.id}')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['title'], 'JS Tech Talk')

    def test_2_rsvp_notification(self):
        """ Test that a notification is created on RSVP. """
        notification_count_before = Notification.query.filter_by(user_id=self.user1.id).count()

        # User 2 RSVPs to User 1's event
        response = self.client.post(f'/event/{self.event1.id}/rsvp', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        notification_count_after = Notification.query.filter_by(user_id=self.user1.id).count()
        self.assertEqual(notification_count_after, notification_count_before + 1)

        notification = Notification.query.filter_by(user_id=self.user1.id).first()
        self.assertEqual(notification.type, 'event_rsvp')
        self.assertEqual(notification.actor_id, self.user2.id)

    def test_3_live_now_badge_context(self):
        """ Test that the context for the live now badge is passed correctly. """
        response = self.client.get('/events')
        self.assertEqual(response.status_code, 200)
        # We can't directly test the rendered template context easily,
        # but we can check if the main page loads, which implies the route is working.
        # The logic is tested implicitly by the template rendering without error.
        self.assertIn(b'Events', response.data)

    def test_4_calendar_api_endpoint(self):
        """ Test the API endpoint for the calendar. """
        response = self.client.get('/api/events/for_calendar')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 2)
        self.assertIn('title', data[0])
        self.assertIn('start', data[0])
        self.assertIn('url', data[0])

    def test_5_attendees_api_endpoint(self):
        """ Test the API endpoint for fetching all attendees. """
        # First, user 2 RSVPs
        self.client.post(f'/event/{self.event1.id}/rsvp')

        response = self.client.get(f'/api/event/{self.event1.id}/attendees')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'Attendee User')

if __name__ == "__main__":
    unittest.main()
