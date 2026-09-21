"""
make_fig6.py — 重新產生 Fig. 6（Gioia 資料結構圖）
================================================

    python paper/make_fig6.py

為什麼要有這支
--------------
在介面上手動挑主題、匯出 SVG、再另外轉成 PNG，圖的來源不會留下來：
日後需要重新匯出時（例如字級要調到期刊要求的 7 pt），沒有人說得出
那兩個主題是從哪一批資料、哪幾個段落組出來的。

這支腳本把那張圖的內容寫死成可重跑的形式：主題與成員段落都取自出貨的參考
編碼（analyses/demo_en_*.json），繪圖走的是介面「匯出 SVG」按鈕呼叫的同一個
函式，參數等同在介面上把「每個主題顯示幾個一階概念」拉到 3。所以論文裡的
圖就是這個工具實際匯出的東西，不是另外修過的版本。

輸出
----
  paper/fig6_data_structure.svg
  paper/fig6_data_structure.png   用本機 Chrome 或 Edge 以 3 倍解析度轉出

轉 PNG 需要 Chrome 或 Edge；找不到時只輸出 SVG，並說明怎麼手動轉。
"""

import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import tacit_framework as F  # noqa: E402
import tacit_i18n as I  # noqa: E402
import tacit_schema as S  # noqa: E402
import tacit_themes as T  # noqa: E402

OUT_SVG = os.path.join("paper", "fig6_data_structure.svg")
OUT_PNG = os.path.join("paper", "fig6_data_structure.png")
SCALE = 3

# 每個主題的成員用段落標題指定，而不是 G0033 這種全域編號：全域編號是
# collect_first_order 依載入順序配的，語料一變就會指到別的段落。
THEMES = [
    {"name": "Public engagement and representation",
     "relation": S.RELATION_ALIGNED,
     "members": [
         ("A05", "Requires a plan for inconvenient findings"),
         ("A06", "Community input systematically removed at write-up"),
         ("A06", "Consultation reached only the already-informed"),
         ("A05", "Public representation reduced to a single member"),
     ]},
    {"name": "Engagement as a formality",
     "relation": S.RELATION_CHALLENGES,
     "members": [
         ("G05", "Engagement carried 2.5% of the evaluation weight"),
         ("G05", "Promised engagement never entered the monitored schedule"),
     ]},
]
SHOWN_PER_THEME = 3


def find_browser():
    candidates = [
        shutil.which("chrome"), shutil.which("msedge"),
        shutil.which("google-chrome"), shutil.which("chromium"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]
    return next((c for c in candidates if c and os.path.isfile(c)), None)


def main():
    F.activate_by_id("ri_stilgoe_2013")
    I.set_lang("en")
    recs = [S.migrate_record(json.load(open(p, encoding="utf-8")))
            for p in sorted(glob.glob(os.path.join("analyses", "demo_en_*.json")))]
    items = T.collect_first_order(recs)

    themes = []
    for n, spec in enumerate(THEMES, start=1):
        ids = []
        for who, title in spec["members"]:
            hit = [it[T.GLOBAL_ID] for it in items
                   if it[S.RESPONDENT].startswith(who) and it[S.TITLE] == title]
            if len(hit) != 1:
                sys.exit(f"找不到或不唯一：{who} / {title}（{len(hit)} 筆）。"
                         f"參考編碼可能被改過，先執行 python make_demo_data.py")
            ids.append(hit[0])
        themes.append(S.migrate_theme({
            S.THEME_ID: f"T{n:02d}", S.THEME_NAME: spec["name"],
            S.AGG_DIMENSION: S.ENGAGEMENT, S.FRAME_RELATION: spec["relation"],
            S.MEMBER_IDS: ids}, n))

    svg = T.render_data_structure_svg(
        themes, items, max_first_order_per_theme=SHOWN_PER_THEME,
        show_speaker=True,
        dim_label=lambda d: I.dim(d, "en"),
        relation_label=lambda r: I.relation(r, "en"))
    with open(OUT_SVG, "w", encoding="utf-8") as f:
        f.write(svg)
    w = int(re.search(r'width="(\d+)"', svg).group(1))
    h = int(re.search(r'height="(\d+)"', svg).group(1))
    sizes = [float(x) for x in re.findall(r'font-size="([\d.]+)"', svg)]
    print(f"{OUT_SVG}: {w} x {h}，最小字 {min(sizes)} 單位 = "
          f"{min(sizes) * T.SVG_PT_PER_UNIT:.2f} pt（6.27 吋寬）")

    browser = find_browser()
    if not browser:
        print("找不到 Chrome 或 Edge，未輸出 PNG。可用瀏覽器開啟 SVG 後截圖，"
              f"或用 Inkscape 以 {w * SCALE} px 寬匯出。")
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        page = os.path.join(tmp, "fig6.html")
        with open(page, "w", encoding="utf-8") as f:
            f.write('<!doctype html><meta charset="utf-8">'
                    '<style>html,body{margin:0;padding:0;background:#fff}'
                    'svg{display:block}</style>' + svg)
        shot = os.path.join(tmp, "fig6.png")
        subprocess.run([browser, "--headless=new", "--disable-gpu",
                        "--hide-scrollbars", f"--window-size={w},{h}",
                        f"--force-device-scale-factor={SCALE}",
                        f"--screenshot={shot}", "file:///" + page.replace("\\", "/")],
                       check=True, capture_output=True, timeout=120)
        shutil.copyfile(shot, OUT_PNG)
    try:
        from PIL import Image
        with Image.open(OUT_PNG) as im:
            print(f"{OUT_PNG}: {im.size[0]} x {im.size[1]} px")
    except ImportError:
        print(f"{OUT_PNG} 已輸出")
    print(f"build_paper.js 的長寬比要改成 {w} / {h}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
