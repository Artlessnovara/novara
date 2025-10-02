import unittest
import sys
import os
import shutil
import io

# Add the parent directory to the path so we can import the app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from extensions import db
from models import User
from PIL import Image

class TestConfig:
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test'
    # Configure a temporary static folder for tests
    STATIC_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_static')

class BaseTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app.config['STATIC_FOLDER'] = TestConfig.STATIC_FOLDER
        self.app.static_folder = self.app.config['STATIC_FOLDER']
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()
        self.seed_db()

        # Create static directories for testing
        self.profile_pics_dir = os.path.join(self.app.static_folder, 'profile_pics')
        os.makedirs(self.profile_pics_dir, exist_ok=True)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

        # Clean up the test static folder
        if os.path.exists(TestConfig.STATIC_FOLDER):
            shutil.rmtree(TestConfig.STATIC_FOLDER)

    def seed_db(self):
        self.admin = User(name='Admin', email='admin@test.com', role='admin', approved=True)
        self.admin.set_password('pw')
        self.instructor = User(name='Instructor', email='inst@test.com', role='instructor', approved=True)
        self.instructor.set_password('pw')
        self.student = User(name='Student', email='stud@test.com', role='student', approved=True)
        self.student.set_password('pw')
        db.session.add_all([self.admin, self.instructor, self.student])
        db.session.commit()

class AdminTests(BaseTestCase):
    def login_admin(self):
        return self.client.post('/login', data={'email': 'admin@test.com', 'password': 'pw'})

    def test_analytics_dashboard(self):
        self.login_admin()
        response = self.client.get('/admin/dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Admin Dashboard', response.data)
        self.assertIn(b'Total Users', response.data)
        self.assertIn(b'3', response.data)

class ProfileTests(BaseTestCase):
    def login_student(self):
        return self.client.post('/login', data={'email': 'stud@test.com', 'password': 'pw'})

    def test_profile_picture_upload(self):
        self.login_student()

        # Create a real dummy image file
        dummy_image = Image.new('RGB', (10, 10), color = 'red')
        dummy_image_path = os.path.join(self.app.config['STATIC_FOLDER'], 'test.jpg')
        dummy_image.save(dummy_image_path)

        with open(dummy_image_path, 'rb') as img:
            data = {
                'profile_pic': (img, 'test.jpg'),
                'name': self.student.name,
                'email': self.student.email,
                'bio': 'A test bio'
            }

            response = self.client.post(
                '/profile/edit',
                data=data,
                content_type='multipart/form-data',
                follow_redirects=True
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Your profile has been updated.', response.data)

        # Verify the change in the database
        updated_user = User.query.get(self.student.id)
        self.assertIsNotNone(updated_user)
        self.assertNotEqual(updated_user.profile_pic, 'default.jpg')

        # Verify the file was saved
        expected_filepath = os.path.join(self.profile_pics_dir, updated_user.profile_pic)
        self.assertTrue(os.path.exists(expected_filepath))

if __name__ == "__main__":
    unittest.main()
