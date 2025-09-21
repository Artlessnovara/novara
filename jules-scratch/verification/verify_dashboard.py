from playwright.sync_api import sync_playwright, expect

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Log in
        page.goto("http://127.0.0.1:5000/login")
        page.fill('input[name="email"]', "student@example.com")
        page.fill('input[name="password"]', "password")
        page.get_by_role("button", name="Sign In").click()

        # Wait for navigation to the dashboard
        expect(page).to_have_url("http://127.0.0.1:5000/student/dashboard")

        # Take a screenshot of the student dashboard
        page.screenshot(path="jules-scratch/verification/student_dashboard.png")

        browser.close()

if __name__ == "__main__":
    main()
