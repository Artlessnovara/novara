import subprocess
import time
from playwright.sync_api import sync_playwright, Page, expect

def run(playwright):
    # Initialize and seed the database
    subprocess.run(["flask", "init-db"])
    subprocess.run(["flask", "seed-db"])

    # Start the server
    server = subprocess.Popen(["python", "app.py"])
    time.sleep(5) # Give the server some time to start

    try:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Log in
        page.goto("http://127.0.0.1:5000/login")
        page.get_by_label("Email").fill("student@example.com")
        page.get_by_label("Password").fill("password")
        page.get_by_role("button", name="Sign In").click()

        # Go to home feed
        page.goto("http://127.0.0.1:5000/feed")

        # Create a story
        page.get_by_role("link", name="Create Story").click()
        page.get_by_role("button", name="Text").click()
        page.get_by_placeholder("Start typing").fill("This is a test story from Playwright!")
        page.get_by_role("button", name="Post Story").click()

        # Go back to home feed and verify the story
        page.goto("http://127.0.0.1:5000/feed")

        # The story should be from "Test Student"
        story_card = page.locator(".story-card", has_text="Test")
        expect(story_card).to_be_visible(timeout=10000)

        page.screenshot(path="jules-scratch/verification/story_feature.png")

        browser.close()
    finally:
        server.terminate()
        server.wait()


with sync_playwright() as playwright:
    run(playwright)
