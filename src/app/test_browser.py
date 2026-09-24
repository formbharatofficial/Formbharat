import pytest

from browser import Browser


def test_open_returns_rendered_page_html(tmp_path):
    page = tmp_path / "page.html"
    page.write_text(
        """<!DOCTYPE html>
        <html>
          <head><title>FormBharat Render</title></head>
          <body>
            <p id="marker">waiting</p>
            <script>
              document.getElementById("marker").textContent = "rendered-marker";
            </script>
          </body>
        </html>
        """,
        encoding="utf-8",
    )

    html = Browser().open(page.as_uri())

    assert isinstance(html, str)
    assert "FormBharat Render" in html
    assert "rendered-marker" in html
    assert "waiting" not in html


def test_open_rejects_a_blank_url():
    with pytest.raises(ValueError):
        Browser().open("   ")
