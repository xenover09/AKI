import tempfile
import traceback
from playwright.sync_api import sync_playwright

class BrowserTool:
    def __init__(self):
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._temp_dir = None

    def _ensure_browser(self):
        if not self._page:
            try:
                self._temp_dir = tempfile.TemporaryDirectory()
                self._playwright = sync_playwright().start()
                self._browser = self._playwright.chromium.launch_persistent_context(
                    user_data_dir=self._temp_dir.name,
                    headless=False,
                    channel="chrome",
                    args=["--window-size=1280,800"]
                )
                self._page = self._browser.pages[0] if self._browser.pages else self._browser.new_page()
            except Exception as e:
                return {"status": "error", "message": f"Failed to start browser: {str(e)}"}
        return None

    def goto(self, url: str) -> dict:
        if url.startswith("file://"):
            return {"status": "error", "message": "file:// URLs are blocked."}
        err = self._ensure_browser()
        if err: return err
        try:
            self._page.goto(url, wait_until="load")
            return {"status": "success", "message": f"Navigated to {url}"}
        except Exception as e:
            return {"status": "error", "message": traceback.format_exc()}

    def click(self, selector: str) -> dict:
        err = self._ensure_browser()
        if err: return err
        try:
            self._page.click(selector, timeout=5000)
            return {"status": "success", "message": f"Clicked on {selector}"}
        except Exception as e:
            return {"status": "error", "message": traceback.format_exc()}

    def type_text(self, selector: str, text: str) -> dict:
        err = self._ensure_browser()
        if err: return err
        try:
            self._page.fill(selector, text, timeout=5000)
            return {"status": "success", "message": f"Typed text in {selector}"}
        except Exception as e:
            return {"status": "error", "message": traceback.format_exc()}

    def screenshot(self, path: str = "screenshot.png") -> dict:
        err = self._ensure_browser()
        if err: return err
        try:
            self._page.screenshot(path=path)
            return {"status": "success", "message": f"Screenshot saved to {path}"}
        except Exception as e:
            return {"status": "error", "message": traceback.format_exc()}

    def read_text(self) -> dict:
        err = self._ensure_browser()
        if err: return err
        try:
            text = self._page.evaluate("document.body.innerText")
            return {"status": "success", "text": text}
        except Exception as e:
            return {"status": "error", "message": traceback.format_exc()}

    def close(self) -> dict:
        try:
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
            if self._temp_dir:
                self._temp_dir.cleanup()
            self._page = None
            self._browser = None
            self._playwright = None
            self._temp_dir = None
            return {"status": "success", "message": "Browser closed"}
        except Exception as e:
            return {"status": "error", "message": traceback.format_exc()}
