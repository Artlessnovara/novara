import os
import subprocess
import time
from playwright.sync_api import sync_playwright, expect

# Reset the database
subprocess.run(['python', '-m', 'flask', 'reset-db'])

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))

    # Register user 1
    page.goto("http://127.0.0.1:5000/register")
    page.fill("input[name='name']", "Alice")
    page.fill("input[name='email']", "alice@example.com")
    page.fill("input[name='password']", "password")
    page.select_option("select[name='role']", "student")
    page.click("button[type='submit']")

    # Register user 2
    page.goto("http://127.0.0.1:5000/register")
    page.fill("input[name='name']", "Bob")
    page.fill("input[name='email']", "bob@example.com")
    page.fill("input[name='password']", "password")
    page.select_option("select[name='role']", "student")
    page.click("button[type='submit']")

    # Log in as Alice
    page.goto("http://127.0.0.1:5000/login")
    page.fill("input[name='email']", "alice@example.com")
    page.fill("input[name='password']", "password")
    page.click("button[type='submit']")
    page.wait_for_url("http://127.0.0.1:5000/student/dashboard")

    # Navigate to the feed and then to Bob's profile to start a chat
    page.goto("http://127.0.0.1:5000/feed/profile/2") # Assuming Bob has user_id=2
    page.wait_for_selector("button:has-text('Message')")
    page.click("button:has-text('Message')")

    # Send a message
    page.wait_for_selector("textarea.message-input")
    page.fill("textarea.message-input", "Hello Bob!")
    page.click("button.send-btn")

    expect(page.get_by_text("Hello Bob!")).to_be_visible(timeout=5000)
    page.screenshot(path="jules-scratch/verification/chat_conversation.png")

    # Go to chat list and take screenshot
    page.goto("http://127.0.0.1:5000/chat")
    print(page.content())
    expect(page.locator("h3.chat-name-whatsapp:has-text('Private Chat between Alice and Bob')")).to_be_visible()
    page.screenshot(path="jules-scratch/verification/chat_list.png")

    # Go back to the conversation and take screenshot
    page.click("a.chat-link-whatsapp:has-text('Private Chat between Alice and Bob')")
    page.wait_for_selector("div.conversation-page")
    expect(page.locator("p.message-content:has-text('Hello Bob!')")).to_be_visible()
    page.screenshot(path="jules-scratch/verification/chat_conversation.png")

    context.close()
    browser.close()

with sync_playwright() as playwright:
    run(playwright)
