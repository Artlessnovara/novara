import pytest
from playwright.sync_api import sync_playwright, Page, expect

def test_profile_page_screenshot(page: Page, base_url: str):
    """
    Logs in, navigates to the profile page, and takes a screenshot.
    """
    # Navigate to the login page
    page.goto(f"{base_url}/login")

    # Fill in the login credentials
    page.locator('input[name="email"]').fill("student@example.com")
    page.locator('input[name="password"]').fill("password")

    # Click the submit button
    page.locator('button[type="submit"]').click()

    # Wait for the navigation to the student dashboard.
    page.wait_for_url(f"{base_url}/student/dashboard")

    # Now that we are logged in, navigate to the profile page
    page.goto(f"{base_url}/profile")

    # Wait for the main profile container to be visible
    profile_container = page.locator(".profile-container")
    expect(profile_container).to_be_visible()

    # Take a screenshot
    page.screenshot(path="profile_screenshot.png")
