class Browser:
    """Open a URL in Chromium and return the rendered page HTML.

    This step only reads the page. It does not fill fields, enter
    OTP or CAPTCHA, or submit a form.
    """

    _EDGE_EXECUTABLE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

    def open(self, url):
        if not isinstance(url, str) or not url.strip():
            raise ValueError("url must be a non-empty string")

        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                executable_path=self._EDGE_EXECUTABLE,
            )
            try:
                page = browser.new_page()
                page.goto(url, wait_until="load")
                return page.content()
            finally:
                browser.close()


class BrowserSession:
    """Keep one local Edge page open and reread its current DOM.

    open() accepts only a file URL. read_current() does not navigate,
    click, type, or submit. close() ends the browser process.
    """

    def __init__(self):
        self._playwright = None
        self._browser = None
        self._page = None
        self._prepared_dirs = []
        self.url = None

    def open(self, url):
        if not isinstance(url, str) or not url.strip():
            raise ValueError("url must be a non-empty string")
        if not url.strip().lower().startswith("file:"):
            raise ValueError("only a local file page can stay open")

        from playwright.sync_api import sync_playwright

        if self._page is None:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=True,
                executable_path=Browser._EDGE_EXECUTABLE,
            )
            self._page = self._browser.new_page()
        self.url = url.strip()
        self._page.goto(self.url, wait_until="load")
        return self._page.content()

    def read_current(self):
        if self._page is None:
            raise RuntimeError("no local page is open")
        return self._page.content()

    def attach_files(self, attachments):
        """Place prepared files on ordinary file inputs.

        A capture or crop control is left for the user. This does not
        click, type a password, or submit.
        """
        if self._page is None:
            raise RuntimeError("no local page is open")
        if not isinstance(attachments, list):
            raise ValueError("attachments must be a list")
        placed = []
        for item in attachments:
            if not isinstance(item, dict) or item.get("status") != "ready":
                continue
            info = self._page.evaluate(
                """([id, name]) => {
                    const nodes = Array.from(document.querySelectorAll('input[type="file"]'));
                    const index = nodes.findIndex((node) =>
                        (id && node.id === id) || (name && node.getAttribute('name') === name)
                    );
                    if (index < 0) return null;
                    const node = nodes[index];
                    return {
                        index: index,
                        capture: node.getAttribute('capture') || '',
                        type: (node.getAttribute('type') || '').toLowerCase()
                    };
                }""",
                [str(item.get("id") or ""), str(item.get("name") or "")],
            )
            if not info or info.get("type") != "file" or info.get("capture"):
                item["status"] = "needs_user"
                item["reason"] = "site asks the user to choose this file"
                continue
            self._page.locator('input[type="file"]').nth(info["index"]).set_input_files(item["path"])
            item["status"] = "attached"
            placed.append(item.get("field"))
        return placed

    def apply_filled(self, filled):
        """Write already accepted text values into the open local page.

        Password, file, and submit controls are left unchanged.
        """
        if self._page is None:
            raise RuntimeError("no local page is open")
        if not isinstance(filled, list):
            raise ValueError("filled must be a list")
        for item in filled:
            if not isinstance(item, dict) or item.get("value") is None:
                continue
            field = str(item.get("field") or "")
            if not field:
                continue
            self._page.evaluate(
                """([field, value]) => {
                    const nodes = Array.from(document.querySelectorAll("input, textarea, select"));
                    const node = nodes.find((item) => item.id === field || item.getAttribute("name") === field);
                    if (!node || node.tagName === "BUTTON") return false;
                    const type = (node.getAttribute("type") || "").toLowerCase();
                    if (["password", "file", "submit", "button", "reset", "image", "hidden"].includes(type)) return false;
                    node.value = String(value);
                    node.dispatchEvent(new Event("input", { bubbles: true }));
                    node.dispatchEvent(new Event("change", { bubbles: true }));
                    return true;
                }""",
            [field, str(item.get("value"))],
        )

    def keep_prepared_files(self, directory):
        """Keep temporary upload copies until the local page session closes."""
        if directory:
            self._prepared_dirs.append(directory)

    def close(self):
        import shutil

        browser = self._browser
        playwright = self._playwright
        prepared = list(self._prepared_dirs)
        self._browser = None
        self._page = None
        self._playwright = None
        self._prepared_dirs = []
        if browser is not None:
            browser.close()
        if playwright is not None:
            playwright.stop()
        for directory in prepared:
            shutil.rmtree(directory, ignore_errors=True)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()
        return False
