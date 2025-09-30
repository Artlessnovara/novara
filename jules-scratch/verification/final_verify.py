import re
from playwright.sync_api import sync_playwright, Page, expect

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # Log in first
    page.goto("http://127.0.0.1:5000/login")
    page.get_by_placeholder("Email Address").fill("student@example.com")
    page.get_by_placeholder("Password").fill("password")
    page.get_by_role("button", name="Sign In").click()

    # Wait for the dashboard to load
    expect(page.get_by_text("Welcome back,")).to_be_visible()

    # Navigate to the chat list page
    page.goto("http://127.0.0.1:5000/chat")
    expect(page.get_by_text("GloobaApp")).to_be_visible()
    page.screenshot(path="jules-scratch/verification/chat_list_view.png")

    # Click on the "General" chat room
    page.get_by_text("General").click()

    # Verify the chat room view
    expect(page.locator(".chat-view-header .chat-name", has_text="General")).to_be_visible()
    expect(page.locator("#message-input")).to_be_visible()

    # Take a screenshot of the chat room
    page.screenshot(path="jules-scratch/verification/chat_room_view.png")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)