from playwright.sync_api import sync_playwright
import random
import string
import time

def random_string(length=10):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    try:
        # Go to register page
        page.goto("http://127.0.0.1:5000/register", timeout=60000)

        # Register a new student user
        email = f"student_{random_string()}@example.com"
        password = "password"
        page.get_by_label("Name").fill("Test Student")
        page.get_by_label("Email").fill(email)
        page.get_by_label("Password").fill(password)
        page.locator('select#role').select_option('student')
        page.get_by_role("button", name="Create Account").click()

        # After registration, we should be on the login page.
        # Wait for the login form to be visible to confirm redirection.
        page.wait_for_selector('form[action="/login"]')

        # Log in
        page.get_by_label("Email").fill(email)
        page.get_by_label("Password").fill(password)
        page.get_by_role("button", name="Sign In").click()

        # Wait for navigation to the student dashboard
        page.wait_for_url("**/student/dashboard", timeout=60000)

        # Go to the profile page
        page.goto("http://127.0.0.1:5000/profile", timeout=60000)

        # Wait for a key element of the new profile page to be visible
        page.wait_for_selector('.profile-header-content')
        time.sleep(2) # Wait for animations to settle

        # Take a single screenshot
        page.screenshot(path="profile_screenshot.png")

        print("Screenshot taken successfully.")

    except Exception as e:
        print(f"An error occurred: {e}")
        page.screenshot(path="error_screenshot.png")
    finally:
        browser.close()


with sync_playwright() as playwright:
    run(playwright)
