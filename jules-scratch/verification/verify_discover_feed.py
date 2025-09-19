from playwright.sync_api import sync_playwright, Page, expect
import time

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # Increase the default timeout for all actions
    page.set_default_timeout(60000) # 60 seconds

    try:
        # Generate a unique email address using a timestamp
        unique_email = f"testuser_{int(time.time())}@example.com"

        # Navigate to the registration page
        page.goto("http://127.0.0.1:5000/register")

        # Fill out the registration form
        page.get_by_placeholder("Full Name").fill("Test User")
        page.get_by_placeholder("Email Address").fill(unique_email)
        page.get_by_placeholder("Password").fill("password")
        page.select_option("select#role", "student")
        page.get_by_role("button", name="Create Account").click()

        # Wait for navigation to the login page
        expect(page).to_have_url("http://127.0.0.1:5000/login")

        # Fill out the login form
        page.get_by_placeholder("Email Address").fill(unique_email)
        page.get_by_placeholder("Password").fill("password")
        page.get_by_role("button", name="Sign In").click()

        # Wait for navigation to the student dashboard
        expect(page).to_have_url("http://127.0.0.1:5000/student/dashboard")

        # Navigate to the discover feed
        page.goto("http://127.0.0.1:5000/discover")

        # Wait for the discover feed to load
        expect(page).to_have_url("http://127.0.0.1:5000/discover")

        # Take a screenshot
        page.screenshot(path="jules-scratch/verification/verification.png")

    except Exception as e:
        print(f"An error occurred: {e}")
        # Take a screenshot even if there is an error
        page.screenshot(path="jules-scratch/verification/error.png")
    finally:
        browser.close()

with sync_playwright() as playwright:
    run(playwright)
