from playwright.sync_api import sync_playwright, expect
import random
import string

def random_string(length=10):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # Register a new student user
    email = f"student_{random_string()}@example.com"
    password = "password"
    page.goto("http://127.0.0.1:5000/register")
    page.get_by_label("Name").fill("Test Student")
    page.get_by_label("Email").fill(email)
    page.get_by_label("Password").fill(password)
    page.get_by_label("Role").select_option("student")
    page.get_by_role("button", name="Register").click()

    # Log in
    page.goto("http://127.0.0.1:5000/login")
    page.get_by_label("Email").fill(email)
    page.get_by_label("Password").fill(password)
    page.get_by_role("button", name="Login").click()

    # Go to the student dashboard
    page.goto("http://127.0.0.1:5000/student/dashboard")

    # Verify that the old nav bar is not present
    # The old nav bar has a class of "site-header"
    expect(page.locator(".site-header")).to_have_count(0)

    # Take a screenshot
    page.screenshot(path="jules-scratch/verification/verification.png")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
