import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from extensions import db
from models import User, Post, Community, ReportedPost, follow

class TestConfig:
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test'
    # Suppress the warning about the static folder not being found
    STATIC_FOLDER = 'static'

class FeedWorldTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()
        self.seed_users()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def seed_users(self):
        self.user1 = User(name='Test User 1', email='test1@example.com', role='student', approved=True)
        self.user1.set_password('pw')
        self.user2 = User(name='Test User 2', email='test2@example.com', role='student', approved=True)
        self.user2.set_password('pw')
        db.session.add_all([self.user1, self.user2])
        db.session.commit()

    def login_user1(self):
        return self.client.post('/login', data={'email': 'test1@example.com', 'password': 'pw'}, follow_redirects=True)

    def login_user2(self):
        return self.client.post('/login', data={'email': 'test2@example.com', 'password': 'pw'}, follow_redirects=True)

    def test_create_post(self):
        self.login_user1()
        response = self.client.post('/feed/create_post', data={
            'content': 'This is a test post.',
            'privacy': 'public'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Your post has been created!', response.data)

        # Check if the post is in the database
        post = Post.query.filter_by(content='This is a test post.').first()
        self.assertIsNotNone(post)
        self.assertEqual(post.author.id, self.user1.id)

    def test_follow_user(self):
        self.login_user1()
        response = self.client.post(f'/feed/follow/{self.user2.id}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'You are now following Test User 2.', response.data)
        self.assertTrue(self.user1.is_following(self.user2))

    def test_unfollow_user(self):
        self.login_user1()
        self.user1.follow(self.user2)
        db.session.commit()
        self.assertTrue(self.user1.is_following(self.user2))

        response = self.client.post(f'/feed/unfollow/{self.user2.id}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'You have unfollowed Test User 2.', response.data)
        self.assertFalse(self.user1.is_following(self.user2))

    def test_create_community(self):
        self.login_user1()
        response = self.client.post('/feed/community/create', data={
            'name': 'Test Community',
            'description': 'A community for testing.'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Community created successfully!', response.data)

        community = Community.query.filter_by(name='Test Community').first()
        self.assertIsNotNone(community)
        self.assertEqual(community.creator.id, self.user1.id)

    def test_report_post(self):
        self.login_user1()
        post = Post(content='A post to be reported', author=self.user2)
        db.session.add(post)
        db.session.commit()

        response = self.client.get(f'/feed/report_post/{post.id}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Post has been reported.', response.data)

        report = ReportedPost.query.filter_by(post_id=post.id).first()
        self.assertIsNotNone(report)
        self.assertEqual(report.reported_by_id, self.user1.id)

if __name__ == '__main__':
    unittest.main()
