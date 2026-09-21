"""
製作使用手冊.py — 由截圖與內文產生圖文並茂的操作手冊
=====================================================
用法：
    python 製作使用手冊.py            產生中英文兩份 HTML
    python 製作使用手冊.py --pdf      再各轉一份 PDF
    python 製作使用手冊.py --lang zh  只產生其中一種

【中英文各一份，內文分開維護】
  英文版不是逐句翻譯：中文版對台灣的研究生說話，英文版對國外的研究者與
  指導教授說話，詳略與語氣本來就不同。但每一個技術主張、每一個數字
  都必須一致，所以兩份內文檔的區塊結構刻意保持相同。

【英文版的截圖只有一部分】
  拍攝時只補了 16 張英文介面。缺的部分沿用中文截圖並在開頭誠實說明——
  介面語言是使用者設定，不是產品差異；假裝全部都有英文版才是誤導。

【為什麼用腳本產生而不是直接手寫 HTML】
  手冊有六十幾張圖。手寫的話，圖檔改名、少一張、或截圖重拍卻忘了改圖說，
  都不會有任何人發現——直到讀者看到一個破掉的圖框。
  這支腳本在產生前會比對「內文引用的圖」與「資料夾裡實際有的圖」，
  對不上就直接報錯，不會默默產出一份壞掉的手冊。

【圖片一律內嵌成 base64】
  單一 HTML 檔可以直接寄給別人，不必附一整個資料夾。
"""

import base64
import html as _html
import mimetypes
import os
import re
import sys
from datetime import date

SHOT_DIR = "screenshots"
OUT = {"zh": "TACIT_操作手冊",
       "en": "TACIT_User-Manual"}

# 介面用語（不是內文，內文在 manual_content_zh.py / manual_content_en.py）
LABELS = {
    "zh": {"fig": "圖", "toc": "目錄", "title": "TACIT 操作手冊",
           "htmllang": "zh-Hant", "dated": "版本日期",
           "mixed": "本手冊有 {n} 張截圖使用中文介面，因為只補拍了部分英文畫面。"
                    "介面語言是使用者設定，兩種語言的功能完全相同。"},
    "en": {"fig": "Figure", "toc": "Contents",
           "title": "TACIT — User Manual",
           "htmllang": "en", "dated": "Version",
           "mixed": "{n} screenshots in this manual show the Chinese interface, "
                    "because only part of the set was recaptured in English. "
                    "Interface language is a user setting; the two are "
                    "functionally identical."},
}


# =====================================================================
# 內文
# =====================================================================
# 每個區塊是 (種類, 內容)。種類：
#   h1 h2 h3   標題
#   p          段落（可含 <b> <code> 等）
#   note       灰底補充
#   why        藍底：說明「為什麼要這樣做」——方法論理由
#   warn       黃底：容易踩的坑
#   danger     紅底：會造成資料損毀或效度問題
#   steps      有序步驟清單
#   bullets    無序清單
#   table      (表頭, 各列)
#   shot       (檔名不含副檔名與語言後綴, 圖說)
#   shots      多張圖並列，每個元素是 (檔名, 圖說)
# ---------------------------------------------------------------------
# =====================================================================
# 產生
# =====================================================================
CSS = """
:root{--ink:#1a1d21;--muted:#5b6570;--line:#e3e7ec;--bg:#fff;
--why:#eef4fb;--why-b:#3b7dd8;--warn:#fdf6e3;--warn-b:#d9a520;
--danger:#fdeeee;--danger-b:#cc3b3b;--note:#f4f6f8;--note-b:#9aa5b1;}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,"Segoe UI","Noto Sans TC","PingFang TC",
"Microsoft JhengHei",sans-serif;color:var(--ink);background:#f0f2f5;
line-height:1.85;font-size:16.5px;}
.wrap{max-width:960px;margin:0 auto;background:var(--bg);padding:0 62px 90px;
box-shadow:0 0 40px rgba(0,0,0,.07);}
h1{font-size:2.3em;margin:0 0 .3em;padding-top:64px;letter-spacing:-.01em;}
h2{font-size:1.6em;margin:2.4em 0 .7em;padding-top:.5em;border-top:3px solid var(--ink);}
h3{font-size:1.2em;margin:2em 0 .5em;color:#2a3138;}
p{margin:.9em 0;}
code{background:#eef1f4;padding:.12em .4em;border-radius:4px;
font-family:"SFMono-Regular",Consolas,monospace;font-size:.88em;}
.box{padding:16px 20px;border-radius:8px;margin:1.5em 0;border-left:4px solid;}
.why{background:var(--why);border-color:var(--why-b);}
.warn{background:var(--warn);border-color:var(--warn-b);}
.danger{background:var(--danger);border-color:var(--danger-b);}
.note{background:var(--note);border-color:var(--note-b);font-size:.95em;}
figure{margin:2em 0;}
figure img{width:100%;border:1px solid var(--line);border-radius:8px;display:block;
box-shadow:0 2px 10px rgba(0,0,0,.06);}
/* 直式截圖（側欄、單欄面板）拉到全寬會變成一整頁的巨圖，而且沒有意義——
   它本來就窄。依原始長寬比限制寬度，讓版面回到可讀的比例。 */
figure.tall img{max-width:340px;margin:0 auto;}
figure.tall figcaption{max-width:560px;margin-left:auto;margin-right:auto;}
figure.medium img{max-width:620px;margin:0 auto;}
figure.medium figcaption{max-width:660px;margin-left:auto;margin-right:auto;}
figcaption{font-size:.9em;color:var(--muted);margin-top:.7em;padding-left:2px;
border-left:3px solid var(--line);padding-left:12px;}
.fignum{font-weight:700;color:var(--ink);}
table{border-collapse:collapse;width:100%;margin:1.5em 0;font-size:.94em;}
th,td{border:1px solid var(--line);padding:10px 13px;text-align:left;
vertical-align:top;}
th{background:#f4f6f8;font-weight:700;}
td:first-child{white-space:nowrap;font-weight:600;}
ol,ul{padding-left:1.5em;}li{margin:.5em 0;}
.toc{background:var(--note);border-radius:8px;padding:20px 26px;margin:2em 0;}
.toc a{color:var(--ink);text-decoration:none;}
.toc a:hover{text-decoration:underline;}
.toc ol{padding-left:1.3em;margin:.4em 0;}
@media print{
  body{background:#fff;font-size:10.5pt;line-height:1.6;}
  .wrap{box-shadow:none;max-width:none;padding:0 8mm;}
  h1{padding-top:0;}
  /* 不要每章強制換頁。圖片一多，換頁會把章名孤零零留在整頁空白的頂端，
     整份文件被大量空白撐開。只要求標題不與其後內容分離即可。 */
  h2,h3{page-break-after:avoid;break-after:avoid;}
  h2{margin-top:1.4em;}
  figure,.box,table,li{page-break-inside:avoid;break-inside:avoid;}
  figure img{box-shadow:none;max-height:170mm;object-fit:contain;}
  figcaption{orphans:2;widows:2;}
  p{orphans:2;widows:2;}
}
"""


def _embed(path):
    mime = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as f:
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode()


def _size_class(path):
    """
    依原始長寬比決定顯示寬度。

    直式截圖（例如側欄）若一律拉到版面全寬，會被放大到三倍以上，
    佔掉整整一頁卻沒有增加任何可讀性——它原本就只有 355px 寬。
    """
    try:
        from PIL import Image
        w, h = Image.open(path).size
    except Exception:
        return ""
    if h / w >= 1.6:            # 明顯直式：側欄、單欄面板
        return "tall"
    if w < 900:                 # 窄的橫式：單一區塊的特寫
        return "medium"
    return ""


def _shot_path(stem, lang="zh"):
    """
    優先取該語言的截圖，沒有就退回中文版。

    回傳 (路徑, 是否為退回)。退回的張數要如實統計並在手冊開頭說明——
    英文手冊裡混著中文畫面，讀者一定會發現；與其讓他猜是不是拿錯檔案，
    不如一開始就講清楚原因。
    """
    for cand, fell_back in ((f"{stem}_{lang}.png", False),
                            (f"{stem}_zh.png", lang != "zh"),
                            (f"{stem}.png", False)):
        p = os.path.join(SHOT_DIR, cand)
        if os.path.exists(p):
            return p, fell_back
    return None, False


def build_html(blocks, lang):
    L = LABELS[lang]
    missing, used, n_fig, n_fallback = [], set(), [0], [0]
    body, toc = [], []

    def figure(stem, caption):
        p, fell_back = _shot_path(stem, lang)
        if p is None:
            missing.append(stem)
            return ""
        used.add(os.path.basename(p))
        n_fig[0] += 1
        n_fallback[0] += 1 if fell_back else 0
        return (f'<figure class="{_size_class(p)}">'
                f'<img alt="{_html.escape(stem)}" src="{_embed(p)}">'
                f'<figcaption><span class="fignum">{L["fig"]} {n_fig[0]}</span>'
                f'{"　" if lang == "zh" else ". "}'
                f'{caption}</figcaption></figure>')

    for kind, val in blocks:
        if kind == "h1":
            body.append(f"<h1>{val}</h1>")
        elif kind == "h2":
            anchor = f"s{len(toc)}"
            toc.append((anchor, val))
            body.append(f'<h2 id="{anchor}">{val}</h2>')
        elif kind == "h3":
            body.append(f"<h3>{val}</h3>")
        elif kind == "p":
            body.append(f"<p>{val}</p>")
        elif kind in ("why", "warn", "danger", "note"):
            body.append(f'<div class="box {kind}">{val}</div>')
        elif kind == "steps":
            body.append("<ol>" + "".join(f"<li>{x}</li>" for x in val) + "</ol>")
        elif kind == "bullets":
            body.append("<ul>" + "".join(f"<li>{x}</li>" for x in val) + "</ul>")
        elif kind == "table":
            head, rows = val
            body.append("<table><tr>" +
                        "".join(f"<th>{h}</th>" for h in head) + "</tr>" +
                        "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) +
                                "</tr>" for r in rows) + "</table>")
        elif kind == "shot":
            body.append(figure(*val))
        elif kind == "shots":
            body.extend(figure(s, c) for s, c in val)

    toc_html = (f'<div class="toc"><b>{L["toc"]}</b><ol>' +
                "".join(f'<li><a href="#{a}">{t}</a></li>' for a, t in toc) +
                "</ol></div>")
    # 標點跟著語言走：英文用半形冒號與間隔號，中文用全形。
    sep, dot = ("：", "　·　") if lang == "zh" else (": ", " · ")
    stamp = (f'<div class="box note">{L["dated"]}{sep}{date.today():%Y-%m-%d}'
             + (dot + L["mixed"].format(n=n_fallback[0])
                if n_fallback[0] else "") + "</div>")
    head = body[0] if body and body[0].startswith("<h1") else ""
    rest = body[1:] if head else body
    # 目錄放在標題與前言之後
    intro_end = next((i for i, b in enumerate(rest) if b.startswith("<h2")), 0)
    doc = (f"<!DOCTYPE html><html lang='{L['htmllang']}'><head>"
           f"<meta charset='utf-8'>"
           f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
           f"<title>{L['title']}</title><style>{CSS}</style></head>"
           f"<body><div class='wrap'>{head}"
           f"{''.join(rest[:intro_end])}{stamp}{toc_html}"
           f"{''.join(rest[intro_end:])}"
           f"</div></body></html>")
    return doc, missing, used, n_fig[0], n_fallback[0]


def main():
    if not os.path.isdir(SHOT_DIR):
        sys.exit(f"找不到截圖資料夾：{SHOT_DIR}")
    langs = ["zh", "en"]
    if "--lang" in sys.argv:
        langs = [sys.argv[sys.argv.index("--lang") + 1]]
    seen_all = set()      # 跨語言累計，否則後一輪會蓋掉前一輪的紀錄

    for lang in langs:
        mod = __import__(f"manual_content_{lang}")
        doc, missing, used, n_fig, n_fb = build_html(mod.BLOCKS, lang)
        seen_all |= used

        # 內文引用的圖必須都存在，否則產出的手冊會有破圖而沒人發現
        if missing:
            sys.exit(f"[{lang}] 以下截圖在內文被引用但資料夾裡沒有：\n  "
                     + "\n  ".join(missing))

        out_html = OUT[lang] + ".html"
        with open(out_html, "w", encoding="utf-8") as f:
            f.write(doc)
        mb = os.path.getsize(out_html) / 1024 / 1024
        note = f"，其中 {n_fb} 張沿用中文截圖" if n_fb else ""
        print(f"已產生 {out_html}（{n_fig} 張圖{note}，{mb:.1f} MB）")

        if "--pdf" in sys.argv:
            make_pdf(out_html, OUT[lang] + ".pdf")

    on_disk = {f for f in os.listdir(SHOT_DIR) if f.endswith("_zh.png")}
    unused = sorted(on_disk - seen_all)
    if unused:
        print(f"未被任何手冊使用的中文截圖 {len(unused)} 張："
              + "、".join(unused))


def make_pdf(html_path, pdf_path):
    src = os.path.abspath(html_path)
    # WeasyPrint 排第一：純 Python，不需要另外下載瀏覽器，
    # 而且對 CSS 分頁控制（page-break-inside）的支援足夠這份文件使用。
    try:
        from weasyprint import HTML
        HTML(filename=src).write_pdf(pdf_path)
        print(f"已產生 {pdf_path}")
        return
    except Exception as e:
        print(f"（WeasyPrint 不可用：{str(e)[:90]}）")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            pg = b.new_page()
            pg.goto("file://" + src, wait_until="load")
            pg.pdf(path=pdf_path, format="A4", print_background=True,
                   margin={"top": "14mm", "bottom": "14mm",
                           "left": "12mm", "right": "12mm"})
            b.close()
        print(f"已產生 {pdf_path}")
        return
    except Exception as e:
        print(f"（playwright 不可用：{e}）")
    import shutil
    import subprocess
    exe = shutil.which("wkhtmltopdf")
    if exe:
        subprocess.run([exe, "--enable-local-file-access", src, pdf_path])
        print(f"已產生 {pdf_path}")
    else:
        print("找不到 PDF 轉檔工具。可安裝其中一種後重跑：\n"
              "    pip install playwright && playwright install chromium\n"
              "  或安裝 wkhtmltopdf\n"
              "也可以直接用瀏覽器開啟 HTML，按 Ctrl+P 選「另存為 PDF」，"
              "版面已針對列印調整過。")


if __name__ == "__main__":
    main()
