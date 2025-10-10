# monitor.py – Headless browser edition for Abim

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
from bs4 import BeautifulSoup
from datetime import datetime
import os, hashlib, time

URL = "https://visa.vfsglobal.com/tur/en/nld/"

def check_status():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--window-size=1280,800")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) "
                                "Chrome/124.0 Safari/537.36")

    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(URL)
        time.sleep(5)  # wait for Cloudflare + JS
        html = driver.page_source
        driver.quit()
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text().lower()
        if "no appointment" in text or "no appointments" in text:
            return "none", "❌ No appointments available"
        elif "available" in text or "select a time" in text or "book now" in text:
            return "maybe", "✅ Appointment might be available!"
        else:
            return "unknown", "🤔 Could not determine status. Site may have changed."
    except WebDriverException as e:
        return "error", f"⚠️ Selenium error: {e}"

def generate_html(status_type, message):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    color = {
        "none": "#fff1f1",
        "maybe": "#e9ffe9",
        "unknown": "#fff8db",
        "error": "#fff8db",
    }.get(status_type, "#fff8db")

    text = f"""
    <html><head><meta charset='utf-8'>
    <title>Abim - VFS Netherlands Turkey Status</title>
    <style>
    body {{
      background:{color}; font-family:Arial; text-align:center; margin-top:50px;
    }}
    h1 {{ font-size:24px; }}
    p {{ font-size:18px; }}
    </style></head><body>
    <h1>Abim - VFS Netherlands Turkey Status</h1>
    <p>{message}</p>
    <p>Benim abim, dişçi abim... AbimRadar devrede. ☕️</p>
    <p>Last checked: {now}</p>
    <p><a href='{URL}'>{URL}</a></p>
    </body></html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(text)
    return hashlib.sha256(text.encode()).hexdigest()

if __name__ == "__main__":
    s, msg = check_status()
    generate_html(s, msg)
