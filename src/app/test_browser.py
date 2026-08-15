from browser import Browser

def test_open():
    browser = Browser()
    assert browser.open() is None
