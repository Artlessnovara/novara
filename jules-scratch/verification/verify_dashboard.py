from playwright.sync_api import sync_playwright, expect

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # Go to the login page
    page.goto("http://localhost:5000/login")

    # Fill in the login form
    page.get_by_label("Email").fill("student@example.com")
    page.get_by_label("Password").fill("password")
    page.get_by_role("button", name="Login").click()

    # Wait for navigation to the dashboard and check the welcome message
    expect(page.get_by_role("heading", name="Welcome back, Test!")).to_be_visible()

    # Take a screenshot of the dashboard
    page.screenshot(path="jules-scratch/verification/dashboard_screenshot.png")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
