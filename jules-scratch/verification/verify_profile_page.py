from playwright.sync_api import sync_playwright, expect
import sys

def login_and_screenshot(page, email, password, dashboard_url, screenshot_path):
    """Helper function to log in and take a screenshot of the profile page."""
    # Go to login page and log out first to ensure a clean session
    page.goto("http://127.0.0.1:5000/logout")
    page.goto("http://127.0.0.1:5000/login")

    # Fill in the login form
    page.get_by_placeholder("Email Address").fill(email)
    page.get_by_placeholder("Password").fill(password)
    page.get_by_role("button", name="Sign In").click(force=True)

    # Wait for navigation to the correct dashboard
    expect(page).to_have_url(f"http://127.0.0.1:5000{dashboard_url}")

    # Go to the profile page
    page.goto("http://127.0.0.1:5000/profile")

    # Wait for the profile page to load
    expect(page.locator(".profile-hero")).to_be_visible()

    # Take a screenshot
    page.screenshot(path=screenshot_path)
    print(f"Screenshot taken successfully: {screenshot_path}")


def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    try:
        # Student View
        login_and_screenshot(page,
                             "student@example.com",
                             "password",
                             "/student/dashboard",
                             "jules-scratch/verification/profile_student.png")

        # Instructor View
        login_and_screenshot(page,
                             "john@example.com",
                             "password",
                             "/instructor/dashboard",
                             "jules-scratch/verification/profile_instructor.png")

        # Admin View
        login_and_screenshot(page,
                             "admin@example.com",
                             "password",
                             "/admin/dashboard",
                             "jules-scratch/verification/profile_admin.png")

    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        page.screenshot(path="jules-scratch/verification/error.png")

    finally:
        browser.close()

with sync_playwright() as playwright:
    run(playwright)
