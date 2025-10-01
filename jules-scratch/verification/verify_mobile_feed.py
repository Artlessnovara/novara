import re
from playwright.sync_api import sync_playwright, expect

def run(playwright):
    # Use a predefined mobile device profile
    iphone_13 = playwright.devices['iPhone 13']
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(**iphone_13)
    page = context.new_page()

    try:
        # Navigate to the registration page
        page.goto("http://127.0.0.1:5000/register")

        # Register a new user using placeholder text
        page.get_by_placeholder("Full Name").fill("Mobile User")
        import time
        unique_email = f"mobileuser{int(time.time())}@example.com"
        page.get_by_placeholder("Email Address").fill(unique_email)
        page.get_by_placeholder("Password").fill("password123")
        page.locator('select[name="role"]').select_option("student")
        page.get_by_role("button", name="Create Account").click()

        # Should be redirected to login page
        expect(page).to_have_url(re.compile(".*login"))

        # Wait for the page to be fully loaded and idle
        page.wait_for_load_state('networkidle')

        # Log in using placeholder text
        page.get_by_placeholder("Email Address").fill(unique_email)
        page.get_by_placeholder("Password").fill("password123")
        page.get_by_role("button", name="Sign In").click(force=True)

        # Should be redirected to the dashboard after login
        expect(page).to_have_url(re.compile(".*/student/dashboard"))

        # Navigate to the feed
        page.goto("http://127.0.0.1:5000/feed")

        # Wait for the feed to load and check for the "Novara Pro" brand logo
        expect(page.get_by_role("heading", name="Novara Pro")).to_be_visible(timeout=10000)

        # Verify the "What's on your mind" placeholder is visible
        expect(page.get_by_text(re.compile("What’s on your mind,.*"))).to_be_visible()

        # Take a screenshot for visual verification
        page.screenshot(path="jules-scratch/verification/verification.png")

        print("Screenshot saved to jules-scratch/verification/verification.png")

    except Exception as e:
        print(f"An error occurred: {e}")
        # Take a screenshot on error for debugging
        page.screenshot(path="jules-scratch/verification/error.png")

    finally:
        browser.close()

with sync_playwright() as playwright:
    run(playwright)