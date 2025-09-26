from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    try:
        page.goto("http://127.0.0.1:5000/")

        # Wait for the main heading in the hero section to be visible
        page.wait_for_selector('h1:has-text("Scholars Novara Institute")')

        # Take a full-page screenshot
        page.screenshot(path="jules-scratch/verification/homepage.png", full_page=True)

        print("Screenshot saved to jules-scratch/verification/homepage.png")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        browser.close()

with sync_playwright() as playwright:
    run(playwright)