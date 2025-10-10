# monitor.py - Abim edisyonu

import os
import hashlib
from datetime import datetime
import requests
from bs4 import BeautifulSoup

URL = "https://visa.vfsglobal.com/tur/en/nld/"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://visa.vfsglobal.com/",
    "Connection": "close",
}

def fetch_page():
    try:
        r = requests.get(URL, headers=HEADERS, timeout=25)
        r.raise_for_status()
        return "ok", r.text
    except requests.HTTPError as e:
        return "http_error", f"{e}"
    except Exception as e:
        return "error", f"{e}"

def parse_status(html_text):
    soup = BeautifulSoup(html_text, "html.parser")
    text = soup.get_text(separator=" ").lower()
    # Bu kısım basit bir işaret kontrolü yapıyor
    if "no appointment" in text or "no appointments" in text:
        return "none"
    if "available" in text or "select a time" in text or "book now" in text:
        return "maybe"
    # Belirgin işaret yoksa belirsiz de
    return "unknown"

def build_page(title, headline, subline, color, detail):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    # Mini mizah ve kişiselleştirme
    greetings = (
        "Benim abim, dişçi abim... Hoş geldin.\n"
        "AbimRadar devrede. Çay hazır, randevu bekleniyor."
    )
    icon = "🟢" if color == "#e9ffe9" else ("🟡" if color == "#fff8db" else "🔴")
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Abim - VFS Kontrol</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body {{
    margin:0; padding:0; font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Arial;
    background:{color};
    color:#111;
  }}
  .wrap {{ max-width: 820px; margin: 40px auto; padding: 0 18px; text-align:center; }}
  h1 {{ margin: 8px 0 18px; }}
  .card {{
    background:#fff; border:1px solid #eee; border-radius:10px; padding:22px; margin-top:10px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  }}
  .greet {{ white-space: pre-line; color:#555; margin-top:6px; }}
  .time {{ color:#777; margin-top:12px; font-size:14px; }}
  a {{ color:#0066cc; text-decoration:none; }}
  .note {{ margin-top:16px; color:#444; font-size:15px; }}
</style>
</head>
<body>
  <div class="wrap">
    <h1>Abim - VFS Netherlands Turkey Durum</h1>
    <div class="card">
      <h2>{icon} {headline}</h2>
      <p class="greet">{greetings}</p>
      <p class="note">{subline}</p>
      <p class="time">Son kontrol: {now}</p>
      <p class="time">Kontrol edilen adres: <a href="{URL}">{URL}</a></p>
      <p class="note">{detail}</p>
    </div>
  </div>
</body>
</html>"""
    return html

def main():
    status_type, payload = fetch_page()

    if status_type == "ok":
        status = parse_status(payload)
        if status == "none":
            title = "Randevu yok"
            headline = "Randevu görünmüyor"
            subline = "Kısmetse bir sonraki kontrolde. Sakin ol abim, dumanı üstünde simit gibi taze slot yakında düşer."
            color = "#fff1f1"  # kırmızımsı
            detail = "Sayfadaki metin randevu olmadığını belirtiyor."
        elif status == "maybe":
            title = "Belki var"
            headline = "Bir şeyler var gibi"
            subline = "Abim bu işte bir hareket var. Hemen resmi siteye git ve manuel kontrol et."
            color = "#e9ffe9"  # yeşilimsi
            detail = "Metin müsaitlik olabileceğine işaret ediyor."
        else:
            title = "Belirsiz"
            headline = "Anlamlandıramadık"
            subline = "Site değişmiş olabilir. Abim, bir gözünle bakıver."
            color = "#fff8db"  # sarımsı
            detail = "Belirgin bir randevu cümlesi bulunamadı."
    else:
        # 403 dahil tüm hatalar buraya düşer
        title = "Hata"
        headline = "Site kontrolünde hata"
        if "403" in payload:
            subline = "403 Forbidden döndü. Muhtemelen VFS tarafında robot koruması var."
            detail = "Çözüm: Bekleme aralığını koru, sayfayı elle açıp bak. AbimRadar yine deneyecek."
        else:
            subline = "Kontrol sırasında teknik bir sorun oldu."
            detail = payload
        color = "#fff8db"  # sarımsı uyarı

    html = build_page(title, headline, subline, color, detail)

    # Aynı içerikse commit etmeyelim
    new_hash = hashlib.sha256(html.encode("utf-8")).hexdigest()
    old_hash = os.environ.get("ABIM_LAST_HASH", "")
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    # Kaydı bırak ki sonraki adım push yapsın. Hash karşılaştırması GitHub Secrets ile de yapılabilir.
    with open(".abim_hash", "w") as f:
        f.write(new_hash)

if __name__ == "__main__":
    main()
