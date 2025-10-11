# monitor.py  pro version with login, retries, multi center, and a fun status page
# env secrets used:
#   LOGIN_EMAIL, LOGIN_PASSWORD  required for login
# optional env vars:
#   CENTER_LIST  comma separated centers. example: "Netherlands Visa Application Centre - Ankara, Netherlands Visa Application Centre - Istanbul"
#   CATEGORY_TEXT  defaults to "KISA DONEM VIZE / SHORT TERM VISA"
#   SUBCATEGORY_TEXT  defaults to "TURIZM VIZE BASVURUSU / TOURISM VISA APPLICATION"
#   HEADLESS  "1" or "0"
#
# output: writes index.html

import os
import re
import time
import json
import random
import hashlib
from datetime import datetime
from dataclasses import dataclass

from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

BASE = "https://visa.vfsglobal.com"
ROOT = "https://visa.vfsglobal.com/tur/en/nld/"
BOOK_URL = ROOT.rstrip("/") + "/book-an-appointment"

@dataclass
class Config:
    email: str = os.getenv("LOGIN_EMAIL", "")
    password: str = os.getenv("LOGIN_PASSWORD", "")
    centers_raw: str = os.getenv("CENTER_LIST", "Netherlands Visa Application Centre - Ankara")
    category: str = os.getenv("CATEGORY_TEXT", "KISA DONEM VIZE / SHORT TERM VISA")
    subcategory: str = os.getenv("SUBCATEGORY_TEXT", "TURIZM VIZE BASVURUSU / TOURISM VISA APPLICATION")
    headless: bool = os.getenv("HEADLESS", "1") != "0"
    timeout: int = 25
    tries: int = 3
    ua: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    )

CFG = Config()
CENTERS = [c.strip() for c in CFG.centers_raw.split(",") if c.strip()]

def log(msg: str):
    ts = datetime.utcnow().strftime("%H:%M:%S")
    print(f"[{ts} UTC] {msg}", flush=True)

def jitter(a=0.12, b=0.35):
    time.sleep(random.uniform(a, b))

def make_driver():
    opts = Options()
    if CFG.headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--window-size=1366,900")
    opts.add_argument(f"user-agent={CFG.ua}")
    chrome_path = os.getenv("CHROME_PATH")
    if chrome_path:
        opts.binary_location = chrome_path
    d = webdriver.Chrome(options=opts)
    d.set_page_load_timeout(CFG.timeout)
    return d

def wait_css(driver, css, t=None):
    return WebDriverWait(driver, t or CFG.timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, css)))

def click_css(driver, css, t=None):
    el = WebDriverWait(driver, t or CFG.timeout).until(EC.element_to_be_clickable((By.CSS_SELECTOR, css)))
    el.click()
    jitter()
    return el

def accept_cookies(driver):
    for css in [
        "#onetrust-accept-btn-handler",
        "[aria-label='Accept All']",
        "[aria-label='Accept all']",
        "button.cookie-accept",
    ]:
        try:
            click_css(driver, css, t=5)
            log("cookie banner accepted")
            return
        except Exception:
            pass

def goto(driver, url):
    driver.get(url)
    jitter(0.25, 0.7)
    accept_cookies(driver)

def select_by_text_safe(select_el, target_text):
    sel = Select(select_el)
    options = [o.text.strip() for o in sel.options if o.text and o.text.strip()]
    # exact first
    for opt in options:
        if opt == target_text:
            sel.select_by_visible_text(opt)
            return opt
    # contains fallback
    lower = target_text.lower()
    for opt in options:
        if lower in opt.lower():
            sel.select_by_visible_text(opt)
            return opt
    raise ValueError(f"option not found: {target_text}")

def robust_login(driver):
    # open root, click sign in, fill, wait for success indicators
    goto(driver, ROOT)
    log("opened root")
    for css in ["a[href*='sign-in']", "a[href*='signin']", "a#signInBtn", "a[aria-label*='Sign in']"]:
        try:
            click_css(driver, css, t=8)
            log("clicked sign in")
            break
        except Exception:
            continue
    try:
        email_el = wait_css(driver, "input[type='email'], input[name='email']", t=10)
        email_el.clear()
        email_el.send_keys(CFG.email)
        jitter()
        pass_el = wait_css(driver, "input[type='password'], input[name='password']", t=10)
        pass_el.clear()
        pass_el.send_keys(CFG.password)
        jitter()
        for css in ["button[type='submit']", "button[id*='sign']", "button[name='submit']"]:
            try:
                click_css(driver, css, t=8)
                log("submitted login")
                break
            except Exception:
                pass
        WebDriverWait(driver, CFG.timeout).until(
            EC.any_of(
                EC.url_contains("/dashboard"),
                EC.presence_of_element_located((By.XPATH, "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'logout')]")),
                EC.presence_of_element_located((By.XPATH, "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'book an appointment')]")),
            )
        )
        log("login appears successful")
        return True
    except TimeoutException:
        log("login timeout, proceeding anyway")
        return False

def open_booking_form(driver):
    goto(driver, BOOK_URL)
    # sometimes language or country page appears, just try again
    if "/choose-country" in driver.current_url or "/en/" not in driver.current_url:
        goto(driver, BOOK_URL)
    wait_css(driver, "form", t=CFG.timeout)

def pick_dropdowns(driver, center_text):
    form = wait_css(driver, "form", t=CFG.timeout)
    selects = form.find_elements(By.CSS_SELECTOR, "select")
    if len(selects) < 3:
        selects = driver.find_elements(By.CSS_SELECTOR, "select")
    if len(selects) < 3:
        raise TimeoutException("could not find the 3 dropdowns")
    chosen_center = select_by_text_safe(selects[0], center_text)
    jitter()
    chosen_cat = select_by_text_safe(selects[1], CFG.category)
    jitter()
    chosen_sub = select_by_text_safe(selects[2], CFG.subcategory)
    jitter(0.6, 1.0)
    log(f"selected: {chosen_center}  |  {chosen_cat}  |  {chosen_sub}")

def extract_status(driver):
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    full = soup.get_text(separator=" ").strip()
    banners = []
    for css in ["[role='alert']", ".alert", ".alert-info", ".MuiAlert-root", ".vfs-alert", ".notification", ".snackbar"]:
        banners.extend(soup.select(css))
    texts = [re.sub(r"\s+", " ", el.get_text(" ", strip=True)) for el in banners if el.get_text()]

    negatives = ["no appointment", "no appointments", "no slots", "uygun randevu bulunamamaktadır", "üzgünüz", "uzgunuz"]
    positives = ["available", "slot", "select a time", "müsait", "musait", "randevu var"]

    for t in texts:
        low = t.lower()
        if any(k in low for k in negatives):
            return "none", t
        if any(k in low for k in positives):
            return "maybe", t

    low_full = full.lower()
    if any(k in low_full for k in negatives):
        return "none", slice_sentence(full, negatives)
    if any(k in low_full for k in positives):
        return "maybe", slice_sentence(full, positives)

    return "unknown", "durum net degil. sayfa yapisi degismis olabilir."

def slice_sentence(text, keys):
    for k in keys:
        i = text.lower().find(k)
        if i != -1:
            return re.sub(r"\s+", " ", text[max(0, i - 140): i + 240]).strip()
    return re.sub(r"\s+", " ", text[:280]).strip()

def check_one_center(driver, center):
    open_booking_form(driver)
    pick_dropdowns(driver, center)
    time.sleep(1.6)  # let banner render
    return extract_status(driver)

def check_all():
    try:
        d = make_driver()
        if CFG.email and CFG.password:
            try:
                robust_login(d)
            except Exception as e:
                log(f"login error: {e}")
        results = []
        for center in CENTERS:
            try:
                status, msg = check_one_center(d, center)
                results.append({"center": center, "status": status, "message": msg})
                log(f"{center}  ->  {status}")
            except Exception as e:
                results.append({"center": center, "status": "error", "message": f"kontrol hatasi: {e}"})
                log(f"{center}  ->  error: {e}")
        d.quit()
        return results
    except WebDriverException as e:
        return [{"center": "global", "status": "error", "message": f"Selenium error: {e}"}]

# ---------- html building with Turkish humor ----------

def build_html(results):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    status_overall = "none"
    if any(r["status"] == "maybe" for r in results):
        status_overall = "maybe"
    elif any(r["status"] == "unknown" for r in results):
        status_overall = "unknown"
    elif any(r["status"] == "error" for r in results):
        status_overall = "error"

    palette = {
        "none":   {"bg": "#fff6f6", "fg": "#b31b1b", "emoji": "☕️", "title": "Randevu Yok Abim"},
        "maybe":  {"bg": "#f2fff2", "fg": "#1b7a1b", "emoji": "🕺", "title": "Randevu Var Gibi Abim"},
        "unknown":{"bg": "#fffbe6", "fg": "#8a6d3b", "emoji": "🤔", "title": "Abim Dusunuyor"},
        "error":  {"bg": "#fffbe6", "fg": "#8a6d3b", "emoji": "⚙️", "title": "Bir Seyler Bozuldu Abim"},
    }
    theme = palette.get(status_overall, palette["unknown"])

    quotes = [
        "Abim benim, disci kardesim, sabir 🍀",
        "Bir kahve koy, sistem biraz yorgun olabilir ☕️",
        "Her 20 dakikada umut tazelenir 💫",
        "Bugun yoksa yarin olur abim 🌤️",
        "Abim modu acik. Radar devrede 🔎",
    ]
    fun_quote = random.choice(quotes)

    confetti_html = ""
    if status_overall == "maybe":
        pieces = []
        for _ in range(26):
            left = random.randint(0, 98)
            delay = random.uniform(0, 2.6)
            color = random.choice(["#2ecc71", "#3498db", "#f1c40f", "#e67e22", "#e74c3c"])
            pieces.append(f'<span class="c" style="left:{left}vw; background:{color}; animation-delay:{delay:.2f}s;"></span>')
        confetti_html = f'<div class="confetti">{"".join(pieces)}</div>'

    rows = []
    for r in results:
        badge = {
            "none":   '<span class="b b-red">Yok</span>',
            "maybe":  '<span class="b b-green">Var gibi</span>',
            "unknown":'<span class="b b-amber">Belirsiz</span>',
            "error":  '<span class="b b-amber">Hata</span>',
        }.get(r["status"], '<span class="b b-amber">Belirsiz</span>')
        rows.append(f"""
        <tr>
          <td class="td-left">{escape_html(r['center'])}</td>
          <td>{badge}</td>
          <td>{escape_html(r['message'])}</td>
        </tr>
        """)

    html = f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Abim Radar</title>
<style>
:root {{
  --card: #ffffff;
  --shadow: 0 10px 30px rgba(0,0,0,.07);
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; padding: 32px 14px; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial;
  background: linear-gradient(135deg, {theme['bg']} 0%, #ffffff 60%);
  color: #222;
}}
.container {{ max-width: 960px; margin: 0 auto; }}
.header {{
  display: flex; align-items: center; gap: 10px; color: {theme['fg']};
}}
.header h1 {{ font-size: 26px; margin: 0; }}
.card {{
  background: var(--card); border-radius: 16px; padding: 20px; box-shadow: var(--shadow);
  border: 1px solid rgba(0,0,0,.06);
}}
.table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
th, td {{ padding: 10px 8px; border-bottom: 1px solid #eee; text-align: left; }}
.td-left {{ font-weight: 600; }}
.meta {{ color: #666; font-size: 14px; margin-top: 10px; }}
a {{ color: #0b57d0; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
.badges {{ margin-top: 8px; display: flex; flex-wrap: wrap; gap: 6px; }}
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 12px; border: 1px solid #ddd; background: #fafafa; }}
.b {{ padding: 4px 8px; border-radius: 8px; font-size: 12px; font-weight: 600; }}
.b-red {{ color: #b31b1b; background: #ffecec; border: 1px solid #ffd3d3; }}
.b-green {{ color: #1b7a1b; background: #eaffea; border: 1px solid #c9f0c9; }}
.b-amber {{ color: #8a6d3b; background: #fff6df; border: 1px solid #ffe3ac; }}
.fun {{ font-size: 16px; color: #777; margin-top: 12px; font-style: italic; text-align: center; }}
.pulse {{ animation: pulse 1.4s ease-in-out infinite; }}
@keyframes pulse {{ 0%{{transform:scale(1)}} 50%{{transform:scale(1.01)}} 100%{{transform:scale(1)}} }}
.confetti {{ position: fixed; top: -10px; left: 0; right: 0; pointer-events: none; }}
.c {{ position: absolute; width: 10px; height: 10px; opacity: .9; animation: fall 4s linear infinite; border-radius: 2px; }}
@keyframes fall {{ 0%{{transform:translateY(-10px) rotate(0deg)}} 100%{{transform:translateY(110vh) rotate(720deg)}} }}
</style>
</head>
<body>
{confetti_html}
<div class="container">
  <div class="card pulse">
    <div class="header">
      <div style="font-size:28px; line-height:1">{theme['emoji']}</div>
      <h1>{theme['title']}</h1>
    </div>

    <div class="badges">
      <span class="badge">Kategori: {escape_html(CFG.category)}</span>
      <span class="badge">Alt Kategori: {escape_html(CFG.subcategory)}</span>
      <span class="badge">Merkez sayisi: {len(results)}</span>
    </div>

    <table class="table">
      <thead>
        <tr><th>Merkez</th><th>Durum</th><th>Detay</th></tr>
      </thead>
      <tbody>
        {''.join(rows)}
      </tbody>
    </table>

    <p class="meta">Son kontrol: {now}</p>
    <p class="meta"><a href="{BOOK_URL}" target="_blank">VFS Randevu Sayfasi</a></p>
    <p class="fun">Abim benim. Disci kardesim. {fun_quote}</p>
  </div>
</div>
</body>
</html>"""
    return html

def escape_html(s: str) -> str:
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
         .replace("'", "&#39;")
    )

def write_index(html: str):
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    return hashlib.sha256(html.encode()).hexdigest()

if __name__ == "__main__":
    log(f"centers: {CENTERS}")
    results = check_all()
    html = build_html(results)
    digest = write_index(html)
    log(f"index.html sha256: {digest}")
