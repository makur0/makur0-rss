import os
from feedgen.feed import FeedGenerator
from playwright.sync_api import sync_playwright

GOODREADS_EMAIL = os.environ.get("GOODREADS_EMAIL")
GOODREADS_PASSWORD = os.environ.get("GOODREADS_PASSWORD")
SHELF_URL = "https://www.goodreads.com/review/list/4376988-makuro?shelf=read&sort=date_read"

def generate_goodreads_rss(output_filename="goodreads_feed.xml"):
    print("Fetching Goodreads read shelf with Playwright...")

    fg = FeedGenerator()
    fg.title("Goodreads - Read Shelf (makuro)")
    fg.link(href=SHELF_URL, rel="alternate")
    fg.description("Latest books read by makuro on Goodreads")
    fg.language("en")

    items_found = 0

    if not GOODREADS_EMAIL or not GOODREADS_PASSWORD:
        print("Error: GOODREADS_EMAIL or GOODREADS_PASSWORD secrets are missing!")
        fg.rss_file(output_filename)
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="en-US"
        )
        page = context.new_page()

        try:
            # 1. Open Sign-In Page
            print("Opening Goodreads login page...")
            page.goto("https://www.goodreads.com/user/sign_in", timeout=60000)

            # Click "Sign in with email" if option appears
            email_option = page.locator("a:has-text('Sign in with email'), button:has-text('Sign in with email')")
            if email_option.count() > 0:
                email_option.first.click()
                page.wait_for_load_state("networkidle", timeout=15000)

            # 2. Fill Credentials
            email_field = page.locator("input[type='email'], #ap_email, input[name='email']").first
            password_field = page.locator("input[type='password'], #ap_password, input[name='password']").first

            email_field.fill(GOODREADS_EMAIL)
            password_field.fill(GOODREADS_PASSWORD)

            # Submit
            submit_btn = page.locator("input[type='submit'], #signInSubmit, button[type='submit']").first
            submit_btn.click()

            page.wait_for_load_state("networkidle", timeout=30000)
            print("Logged into Goodreads successfully.")

            # 3. Go to Read Shelf
            print(f"Navigating to: {SHELF_URL}")
            page.goto(SHELF_URL, timeout=60000)
            page.wait_for_selector("table#books", timeout=30000)

            rows = page.locator("table#books tr.bookalike")
            count = min(rows.count(), 25)

            for i in range(count):
                row = rows.nth(i)
                title_loc = row.locator("td.field.title div.value a")
                author_loc = row.locator("td.field.author div.value a")

                if title_loc.count() == 0:
                    continue

                title = title_loc.first.inner_text().strip()
                href = title_loc.first.get_attribute("href")
                if href and href.startswith("/"):
                    href = "https://www.goodreads.com" + href

                author = author_loc.first.inner_text().strip() if author_loc.count() > 0 else "Unknown Author"

                entry_title = f"{title} by {author}"

                fe = fg.add_entry()
                fe.id(href)
                fe.title(entry_title)
                fe.link(href=href)
                fe.description(f"Book: {title} | Author: {author}")

                items_found += 1

        except Exception as e:
            print(f"Error scraping Goodreads: {e}")
        finally:
            browser.close()

    # Fallback entry
    if items_found == 0:
        fe = fg.add_entry()
        fe.id(SHELF_URL)
        fe.title("Goodreads - Read Shelf")
        fe.link(href=SHELF_URL)
        fe.description("Visit Goodreads to view shelf.")

    fg.rss_file(output_filename)
    print(f"Done! Generated '{output_filename}' with {items_found} items.")

if __name__ == "__main__":
    generate_goodreads_rss()
