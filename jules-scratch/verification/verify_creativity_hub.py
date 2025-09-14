import re
from playwright.sync_api import Page, expect

def test_creativity_hub_modal(page: Page):
    """
    This test verifies that the creativity hub page loads,
    the FAB is present, and clicking it opens the upload modal.
    """
    # 1. Register a new user to ensure a clean state
    page.goto("http://127.0.0.1:5000/register")
    page.get_by_label("Name").fill("Test User")
    page.get_by_label("Email").fill("test@example.com")
    page.get_by_label("Password").fill("password123")
    page.get_by_label("Confirm Password").fill("password123")
    page.get_by_role("button", name="Register").click()

    # Wait for navigation to the login page after registration
    expect(page).to_have_url(re.compile(r".*/login"))

    # 2. Log in with the new user
    page.get_by_label("Email").fill("test@example.com")
    page.get_by_label("Password").fill("password123")
    page.get_by_role("button", name="Login").click()

    # Wait for navigation to the feed home page
    expect(page).to_have_url(re.compile(r".*/feed"))

    # 3. Navigate to the Creativity Hub
    page.goto("http://127.0.0.1:5000/feed/creativity")
    expect(page).to_have_title(re.compile(r"Creativity Hub"))

    # 4. Find and click the Floating Action Button (FAB)
    fab = page.locator("#fab-create")
    expect(fab).to_be_visible()
    fab.click()

    # 5. Verify the modal appears and take a screenshot
    modal = page.locator("#create-modal")
    expect(modal).to_be_visible()
    expect(modal.get_by_text("Upload to Creativity Hub")).to_be_visible()

    # 6. Switch to the "Writing" tab to show a different form
    writing_tab = modal.get_by_role("link", name="Writing")
    writing_tab.click()

    # Check that the writing form is now visible
    expect(page.locator("#writing-form-content")).to_be_visible()

    # 7. Take a screenshot
    page.screenshot(path="jules-scratch/verification/verification.png")

    # 8. Close the modal
    modal.get_by_role("button", name="Close").click()
    expect(modal).not_to_be_visible()
