import requests
from bs4 import BeautifulSoup
from datetime import datetime

URL = "https://visa.vfsglobal.com/tur/en/nld/"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AbimBot/1.0)"}

def check_status():
    try:
        res = requests.get(URL, headers=HEADERS, timeout=20)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        text = soup.get_text().lower()
        if "no appointment" in text or "no appointments" in text:
            status = "❌ No appointments available"
        else:
            status = "✅ Appointment might be available!"
    except Exception as e:
        status = f"⚠️ Error checking site: {e}"
    return status

if __name__ == "__main__":
    status = check_status()
    time_checked = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8'>
<title>Abim - VFS Check</title>
<style>
body {{ font-family: Arial, sans-serif; text-align:center; padding-top:40px; }}
.status {{ font-size: 1.6em; }}
.time {{ color: gray; margin-top: 15px; }}
</style>
</head>
<body>
<h1>Abim – VFS Netherlands (Turkey) Status</h1>
<div class="status">{status}</div>
<div class="time">Last checked: {time_checked}</div>
<p>URL checked: <a href="{URL}">{URL}</a></p>
</body>
</html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
