import unittest
import sys
import os
from app import create_app, db
from models import User, Event, EventRSVP
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import the app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestConfig:
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test_event_secret'
    # Suppress the warning about track modifications
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class EventTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()
        self.seed_db()
        self.login('user1@test.com', 'password')

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def seed_db(self):
        # Create users
        self.user1 = User(id=1, name='Test User 1', email='user1@test.com', role='student', approved=True)
        self.user1.set_password('password')
        self.user2 = User(id=2, name='Test User 2', email='user2@test.com', role='instructor', approved=True)
        self.user2.set_password('password')
        db.session.add_all([self.user1, self.user2])
        db.session.commit()

        # Create events
        self.event1 = Event(title='Upcoming Event', description='Fun times ahead', date=datetime.utcnow() + timedelta(days=7), location='Online', organizer_id=self.user1.id)
        self.event2 = Event(title='Past Event', description='Fun times were had', date=datetime.utcnow() - timedelta(days=7), location='In Person', organizer_id=self.user1.id)
        self.event3 = Event(title='Another Upcoming Event', description='Organized by user 2', date=datetime.utcnow() + timedelta(days=14), location='Online', organizer_id=self.user2.id)
        db.session.add_all([self.event1, self.event2, self.event3])
        db.session.commit()

    def login(self, email, password):
        return self.client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)

    def test_1_event_creation_page(self):
        """ Test that the event creation page loads. """
        response = self.client.get('/event/create')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Create a New Event', response.data)

    def test_2_event_creation_post(self):
        """ Test creating a new event via POST request. """
        event_count_before = Event.query.count()

        event_data = {
            'title': 'My New Test Event',
            'description': 'This is a test description.',
            'date': (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%dT%H:%M'),
            'location': 'Test Location'
        }

        response = self.client.post('/event/create', data=event_data, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'My New Test Event', response.data)

        event_count_after = Event.query.count()
        self.assertEqual(event_count_after, event_count_before + 1)

    def test_3_event_list_page(self):
        """ Test that the main events page loads and shows events. """
        response = self.client.get('/events')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Upcoming Event', response.data)
        self.assertIn(b'Past Event', response.data)

    def test_4_api_event_filtering(self):
        """ Test the event filtering API endpoint. """
        # Test filter=upcoming
        response = self.client.get('/api/events/filter?filter=upcoming')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 2)
        self.assertIn('Upcoming Event', [e['title'] for e in data])
        self.assertNotIn('Past Event', [e['title'] for e in data])

        # Test filter=past
        response = self.client.get('/api/events/filter?filter=past')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['title'], 'Past Event')

        # Test filter=my_events
        response = self.client.get('/api/events/filter?filter=my_events')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 2)
        self.assertNotIn('Another Upcoming Event', [e['title'] for e in data])

        # Test search
        response = self.client.get('/api/events/filter?search=Past')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['title'], 'Past Event')

    def test_5_event_details_and_rsvp(self):
        """ Test viewing an event's details and the RSVP functionality. """
        event = Event.query.filter_by(title='Upcoming Event').first()
        self.assertIsNotNone(event)

        # Test details page
        response = self.client.get(f'/event/{event.id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'RSVP Now', response.data)

        # Test RSVPing
        rsvp_count_before = EventRSVP.query.count()
        response = self.client.post(f'/event/{event.id}/rsvp', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Cancel RSVP', response.data)
        rsvp_count_after = EventRSVP.query.count()
        self.assertEqual(rsvp_count_after, rsvp_count_before + 1)

        # Test canceling RSVP
        response = self.client.post(f'/event/{event.id}/rsvp', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'RSVP Now', response.data)
        rsvp_count_final = EventRSVP.query.count()
        self.assertEqual(rsvp_count_final, rsvp_count_before)

if __name__ == "__main__":
    unittest.main()
