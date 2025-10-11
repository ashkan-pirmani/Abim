def build_html(status_type, message):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    palette = {
        "none":   {"bg": "#fff6f6", "fg": "#b31b1b", "emoji": "☕️", "title": "Randevu Yok Abim"},
        "maybe":  {"bg": "#f2fff2", "fg": "#1b7a1b", "emoji": "🕺", "title": "Randevu Var Gibi Abim!"},
        "unknown":{"bg": "#fffbe6", "fg": "#8a6d3b", "emoji": "🤔", "title": "Abim Düşünüyor..."},
        "error":  {"bg": "#fffbe6", "fg": "#8a6d3b", "emoji": "⚙️", "title": "Bir Şeyler Bozuldu Abim"},
    }
    theme = palette.get(status_type, palette["unknown"])

    easter_eggs = [
        "Abim benim, dişçi kardeşim... sabır 🍀",
        "Bir kahve koy, sistem düşmüş olabilir ☕️",
        "Her 20 dakikada bir umut tazelenir 💫",
        "Randevu yoksa bile moralini bozma abim 🌤️",
    ]
    fun_quote = random.choice(easter_eggs)

    confetti_html = ""
    if status_type == "maybe":
        pieces = []
        for i in range(24):
            left = random.randint(0, 98)
            delay = random.uniform(0, 2.8)
            color = random.choice(["#2ecc71", "#3498db", "#f1c40f", "#e67e22", "#e74c3c"])
            pieces.append(
                f'<span class="c" style="left:{left}vw; background:{color}; animation-delay:{delay:.2f}s;"></span>'
            )
        confetti_html = f'<div class="confetti">{"".join(pieces)}</div>'

    html = f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Abim Radar</title>
<style>
body {{
  margin:0; padding:40px 16px; font-family:-apple-system,Segoe UI,Roboto,Arial;
  background:linear-gradient(135deg,{theme['bg']} 0%,#ffffff 70%);
  color:#222; text-align:center;
}}
h1 {{ color:{theme['fg']}; font-size:28px; margin-bottom:6px; }}
.message {{ font-size:18px; margin:10px 0; }}
.meta {{ color:#555; font-size:14px; margin-top:12px; }}
.fun {{ font-size:16px; color:#777; margin-top:18px; font-style:italic; }}
.confetti {{ position:fixed; top:-10px; left:0; right:0; pointer-events:none; }}
.c {{
  position:absolute; width:10px; height:10px; opacity:.9;
  animation:fall 4s linear infinite; border-radius:2px;
}}
@keyframes fall {{
  0%{{transform:translateY(-10px) rotate(0deg);}}
  100%{{transform:translateY(110vh) rotate(720deg);}}
}}
.card {{
  display:inline-block; background:#fff; border-radius:16px;
  padding:24px 32px; box-shadow:0 10px 30px rgba(0,0,0,.1);
  max-width:800px;
}}
.hoverline:hover::after {{
  content:' (Abim Mode aktif)'; font-size:14px; color:#999;
}}
</style>
</head>
<body>
{confetti_html}
<div class="card">
  <h1 class="hoverline">{theme['emoji']} {theme['title']}</h1>
  <p class="message">{escape_html(message)}</p>
  <p class="meta">Son kontrol: {now}</p>
  <p class="fun">{fun_quote}</p>
  <p><a href="{BOOK_URL}" target="_blank">VFS Randevu Sayfası</a></p>
</div>
</body>
</html>"""
    return html
