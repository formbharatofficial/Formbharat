class Browser:
    """Open a URL in Chromium and return the rendered page HTML.

    This step only reads the page. It does not fill fields, enter
    OTP or CAPTCHA, or submit a form.
    """

    def open(self, url):
        if not isinstance(url, str) or not url.strip():
            raise ValueError("url must be a non-empty string")

        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(url, wait_until="load")
                return page.content()
            finally:
                browser.close()
