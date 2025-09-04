from playwright.sync_api import sync_playwright, Page, expect
import re

def login(page: Page, base_url: str):
    """
    Logs into the application using predefined credentials.
    """
    print("Navigating to login page...")
    page.goto(f"{base_url}/login")

    print("Filling in login credentials...")
    page.get_by_placeholder("Email").fill("student@example.com")
    page.get_by_placeholder("Password").fill("password")

    print("Submitting login form...")
    page.get_by_role("button", name="Sign In").click()

    # Wait for navigation to the student dashboard to confirm login.
    # The heading is dynamic (e.g., "Welcome back, Test Student!"), so we use a regex.
    print("Waiting for dashboard to load...")
    welcome_heading = page.get_by_role("heading", name=re.compile("Welcome back, .*"))
    expect(welcome_heading).to_be_visible()
    print("Login successful.")

def run_verification(page: Page):
    """
    Logs in, navigates to the new chat UI pages, and takes screenshots.
    """
    base_url = "http://127.0.0.1:5000"

    # --- Step 1: Login ---
    login(page, base_url)

    # --- Step 2: Verify Chat List View ---
    print("Navigating to Chat List view...")
    page.goto(f"{base_url}/new_chat_interface")

    expect(page.get_by_role("heading", name="Chats")).to_be_visible()
    expect(page.get_by_text("Web Development Course")).to_be_visible()

    print("Capturing screenshot of Chat List view...")
    page.screenshot(path="jules-scratch/verification/chat_list_view.png")

    # --- Step 3: Verify Chat Room View ---
    print("Navigating to Chat Room view...")
    page.goto(f"{base_url}/new_chat_interface/room")

    expect(page.locator(".conversation-header")).to_be_visible()
    expect(page.get_by_text("Hey, how is everyone?")).to_be_visible()

    print("Capturing screenshot of Chat Room view...")
    page.screenshot(path="jules-scratch/verification/chat_room_view.png")

    print("Verification script finished successfully.")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            run_verification(page)
        finally:
            browser.close()

if __name__ == "__main__":
    main()
