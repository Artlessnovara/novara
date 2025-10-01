from playwright.sync_api import sync_playwright, expect

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # Log in
    page.goto("http://127.0.0.1:5000/login")
    page.get_by_label("Email").fill("test1@example.com")
    page.get_by_label("Password").fill("pw")
    page.get_by_role("button", name="Login").click()

    # Go to suggestions page
    page.goto("http://127.0.0.1:5000/feed/suggestions")

    # Wait for the page to load and take a screenshot
    expect(page.get_by_role("heading", name="People You May Know")).to_be_visible()
    page.screenshot(path="jules-scratch/verification/verification.png")

    # Test the search functionality
    page.get_by_placeholder("City").fill("Test City")
    page.get_by_placeholder("State").fill("Test State")
    page.get_by_role("button", name="Search").click()

    # Wait for search results and take another screenshot
    expect(page.get_by_role("heading", name="People You May Know")).to_be_visible()
    page.screenshot(path="jules-scratch/verification/verification_search.png")


    browser.close()

with sync_playwright() as playwright:
    run(playwright)