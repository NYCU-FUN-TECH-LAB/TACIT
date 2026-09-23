"""make_fig2.py — 重畫 Fig. 2（context window 為什麼不能放著不管）

    python paper/make_fig2.py          在專案根目錄下執行

為什麼要用程式畫
----------------
手寫的 SVG 會跟程式脫節：保留額的公式一改（現在是「視窗的四分之一，夾在
3,072 與 8,192 之間」），圖上的數字就不再是程式實際算出來的數字。

所以每一個數字都在執行時向 tacit_llm 問：保留額問 default_max_tokens，
安全邊際與估算方式跟 check_context 用的是同一套，系統提示詞的長度用
RI 框架實際建出來量。程式改了，重跑這支，圖就跟著改。

灰階印刷前提。畫布 1200 單位、最小字 21 單位 → 6.27 吋寬印出來約 7.8 pt。
"""
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.getcwd(), "src"))

import bench_models as B            # noqa: E402
import tacit_framework as F         # noqa: E402
import tacit_llm as LLM             # noqa: E402

OUT_SVG = os.path.join("paper", "fig2_context_window.svg")
OUT_PNG = os.path.join("paper", "fig2_context_window.png")
SCALE = 3
SAFETY = 512                        # check_context 裡的固定邊際
CHARS_PER_TOKEN = 3.5               # estimate_tokens 對非 CJK 文字的換算
WINDOWS = [4096, 8192, 16384, 32768]


def find_browser():
    candidates = [
        shutil.which("chrome"), shutil.which("msedge"),
        shutil.which("google-chrome"), shutil.which("chromium"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]
    return next((c for c in candidates if c and os.path.isfile(c)), None)


def measure():
    F.activate_by_id("ri_stilgoe_2013")
    prompt = LLM.estimate_tokens(B.build_system_prompt(F.active(), "en"))
    rows = []
    for n in WINDOWS:
        reserve = LLM.default_max_tokens(LLM.OLLAMA, n)
        left = n - reserve - SAFETY - prompt
        rows.append({"num_ctx": n, "reserve": reserve, "left": left,
                     "chars": max(0, int(left * CHARS_PER_TOKEN))})
    return prompt, rows


def render(prompt, rows):
    first = rows[0]
    need = prompt + first["reserve"] + SAFETY
    over = need - first["num_ctx"]

    # 上半：固定成本會超出視窗，視窗的終點畫成一條虛線，
    # 超出的部分就落在線的右邊——「放不下」要一眼看得出來。
    # 比例依「固定成本」與「視窗」較大的那個決定，整條一定畫得進版面。
    px = 1040.0 / max(need, first["num_ctx"])
    x0 = 80
    w_prompt, w_out, w_safe = prompt * px, first["reserve"] * px, SAFETY * px
    x_out, x_safe = x0 + w_prompt, x0 + w_prompt + w_out
    x_win_end = round(x0 + first["num_ctx"] * px)

    # 下半：880 單位 = 80,000 字元
    per_char = 880.0 / 80000
    bar_x = 280
    ys = [484, 554, 624, 694]
    fills = ["#8f8f8f", "#b4b4b4", "#d6d6d6", "#ffffff"]

    out = []
    a = out.append
    a('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 800" width="1200" height="800">')
    a('  <!-- 由 paper/make_fig2.py 產生。數字來自 tacit_llm，不要手改。 -->')
    a('  <defs><style>')
    a("    .t    { font-family:'DejaVu Sans','Helvetica','Arial',sans-serif; fill:#1a1a1a; }")
    a('    .hd   { font-size:26px; font-weight:700; }')
    a('    .lab  { font-size:22px; }')
    a("    .mos  { font-family:'DejaVu Sans Mono','Courier New',monospace; font-size:22px; }")
    a('    .tiny { font-size:21px; fill:#4a4a4a; }')
    a('    .note { font-size:23px; fill:#1a1a1a; font-style:italic; }')
    a('    .ax   { stroke:#888888; stroke-width:1.6; }')
    a('  </style></defs>')
    a('  <rect width="1200" height="800" fill="#ffffff"/>')

    a(f'  <text class="t hd" x="80" y="56">What a {first["num_ctx"]:,}-token window has to hold</text>')
    a('  <text class="t tiny" x="80" y="84">Ollama\'s default. The fixed costs alone exceed it, '
      'before any transcript is added.</text>')

    a(f'  <rect x="{x0}" y="104" width="{w_prompt:.0f}" height="66" fill="#b4b4b4" stroke="#1a1a1a" stroke-width="2"/>')
    a(f'  <rect x="{x_out:.0f}" y="104" width="{w_out:.0f}" height="66" fill="#d6d6d6" stroke="#1a1a1a" stroke-width="2"/>')
    a(f'  <rect x="{x_safe:.0f}" y="104" width="{w_safe:.0f}" height="66" fill="#ededed" stroke="#1a1a1a" stroke-width="2"/>')
    # 視窗的邊界
    a(f'  <line x1="{x_win_end}" y1="92" x2="{x_win_end}" y2="200" stroke="#1a1a1a" stroke-width="3.5" stroke-dasharray="9 6"/>')
    a(f'  <text class="t tiny" x="{x_win_end - 10}" y="226" text-anchor="end">window ends: {first["num_ctx"]:,}</text>')

    a(f'  <text class="t lab" x="{x0 + 16}" y="144">coding prompt</text>')
    a(f'  <text class="t tiny" x="{x0 + 16}" y="196">{prompt:,} tokens</text>')
    # 視窗終點的虛線會落在保留額那一格裡；標籤放在線的右邊，不要被線切過去
    x_lab = max(x_out + 16, x_win_end + 16)
    a(f'  <text class="t lab" x="{x_lab:.0f}" y="144">output reservation</text>')
    a(f'  <text class="t tiny" x="{x_out + 16:.0f}" y="196">{first["reserve"]:,}</text>')
    a(f'  <text class="t tiny" x="{x_safe + 8:.0f}" y="144">safety</text>')
    a(f'  <text class="t tiny" x="{x_safe + 8:.0f}" y="196">{SAFETY}</text>')

    a(f'  <text class="t note" x="1120" y="262" text-anchor="end">needed before any transcript: '
      f'{need:,} tokens, {over:,} more than the window</text>')
    a('  <text class="t note" x="1120" y="292" text-anchor="end">'
      '\u2014 TACIT refuses the prompt; a bare server truncates it silently</text>')

    a('  <text class="t hd" x="80" y="350">Longest transcript that fits</text>')
    a('  <text class="t tiny" x="80" y="378">Derived from the same formula. Bars are drawn to scale.</text>')

    band_x0 = bar_x + 20000 * per_char
    band_x1 = bar_x + 60000 * per_char
    a(f'  <rect x="{band_x0:.0f}" y="470" width="{band_x1 - band_x0:.0f}" height="252" fill="#f0f0f0"/>')
    a(f'  <line class="ax" x1="{band_x0:.0f}" y1="440" x2="{band_x0:.0f}" y2="722" stroke-dasharray="7 5"/>')
    a(f'  <line class="ax" x1="{band_x1:.0f}" y1="440" x2="{band_x1:.0f}" y2="722" stroke-dasharray="7 5"/>')
    a(f'  <text class="t tiny" x="{band_x0 + 15:.0f}" y="424">a one-hour research interview</text>')
    a(f'  <text class="t tiny" x="{band_x0 + 15:.0f}" y="448">runs 20,000\u201360,000 characters</text>')
    a('  <text class="t mos" x="80" y="448">num_ctx</text>')

    notes = {4096: "Ollama default", 32768: "TACIT default"}
    for r, y, fill in zip(rows, ys, fills):
        a(f'  <text class="t mos" x="80" y="{y + 20}">{r["num_ctx"]:>7,}</text>')
        if r["num_ctx"] in notes:
            a(f'  <text class="t tiny" x="80" y="{y + 44}">{notes[r["num_ctx"]]}</text>')
        w = r["chars"] * per_char
        if r["chars"] <= 0:
            a(f'  <line x1="{bar_x}" y1="{y}" x2="{bar_x}" y2="{y + 30}" stroke="#1a1a1a" stroke-width="3"/>')
            a(f'  <text class="t tiny" x="{bar_x + 14}" y="{y + 22}">nothing fits \u2014 refused</text>')
            continue
        heavy = 3 if r["num_ctx"] == 32768 else 1.8
        a(f'  <rect x="{bar_x}" y="{y}" width="{w:.0f}" height="30" fill="{fill}" stroke="#1a1a1a" stroke-width="{heavy}"/>')
        label = f'{r["chars"]:,}'
        if bar_x + w + 100 > 1180:          # 放不下就寫在長條裡面
            a(f'  <text class="t tiny" x="{bar_x + w - 12:.0f}" y="{y + 22}" text-anchor="end">{label}</text>')
        else:
            a(f'  <text class="t tiny" x="{bar_x + w + 13:.0f}" y="{y + 22}">{label}</text>')

    a(f'  <line class="ax" x1="{bar_x}" y1="754" x2="1160" y2="754"/>')
    a('  <g class="t tiny" text-anchor="middle">')
    for k in (0, 20, 40, 60, 80):
        x = bar_x + k * 1000 * per_char
        a(f'    <line class="ax" x1="{x:.0f}" y1="754" x2="{x:.0f}" y2="764"/>'
          f'<text x="{x:.0f}" y="788">{"0" if k == 0 else str(k) + "k"}</text>')
    a('  </g>')
    a('</svg>')
    return "\n".join(out) + "\n"


def main():
    prompt, rows = measure()
    print(f"系統提示詞：{prompt:,} tokens（RI 框架，英文）")
    for r in rows:
        print(f"  num_ctx={r['num_ctx']:>6,}  保留額={r['reserve']:>5,}  "
              f"剩給逐字稿={r['left']:>7,} tokens  約 {r['chars']:>7,} 字元")

    if os.path.isfile(OUT_PNG) and not os.path.isfile(OUT_PNG.replace(".png", "_old.png")):
        shutil.copyfile(OUT_PNG, OUT_PNG.replace(".png", "_old.png"))
    svg = render(prompt, rows)
    with open(OUT_SVG, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"已寫入 {OUT_SVG}")

    browser = find_browser()
    if not browser:
        print("找不到 Chrome 或 Edge，未輸出 PNG。")
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        page = os.path.join(tmp, "fig2.html")
        with open(page, "w", encoding="utf-8") as f:
            f.write('<!doctype html><meta charset="utf-8">'
                    '<style>html,body{margin:0;padding:0;background:#fff}'
                    'svg{display:block}</style>' + svg)
        shot = os.path.join(tmp, "fig2.png")
        subprocess.run([browser, "--headless=new", "--disable-gpu",
                        "--hide-scrollbars", "--window-size=1200,800",
                        f"--force-device-scale-factor={SCALE}",
                        f"--screenshot={shot}", "file:///" + page.replace("\\", "/")],
                       check=True, capture_output=True, timeout=120)
        shutil.copyfile(shot, OUT_PNG)
    print(f"已寫入 {OUT_PNG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
