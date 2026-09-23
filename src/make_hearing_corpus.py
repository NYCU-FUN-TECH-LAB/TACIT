"""
make_hearing_corpus.py — 從美國國會聽證會逐字稿建立公開示範語料
================================================================

    python make_hearing_corpus.py                 抓取、解析、輸出全部
    python make_hearing_corpus.py --list          只列出每場的證人與判定的部門
    python make_hearing_corpus.py --only CHRG-118shrg53503

為什麼要有這份語料
------------------
合成示範語料是語言模型依既定碼書寫出來的訪談：碼與文本同源、每份
不到 3,500 字元、分窗機制從未真的被執行，任何人也無從拿原始來源去核對。
這份語料補上那一塊，用的是**真實、官方、公有領域**的文本：

  * 來源：美國政府出版局 govinfo.gov 的國會聽證會逐字稿（CHRG 集合）
  * 授權：17 U.S.C. § 105，聯邦政府著作不受著作權保護
  * 主題：AI 治理（監管、風險、隱私、政府採用），118–119 屆國會
  * 形狀：議員提問、證人回答——天然就是訪談的問答形式

每位證人各成一份「訪談稿」：口頭開場陳述，接著每一輪「議員的提問 → 該證人
的回答」。證人的**書面**聲明不收，因為那部分理論上可能仍有著作權，且不是
口語資料；只收會議記錄員逐字記下的口頭發言。

證人本來就分產業、學界、政府、公民團體四類，跟原本示範語料的
institution_type 四值直接對應，Table 6 的交叉表設計不必改。

輸出
----
  demo_data/hearings/_raw/<id>.htm        govinfo 原檔（快取，重跑不再抓）
  demo_data/hearings/en/<n>_<id>_<Surname>.docx
  demo_data/hearings/manifest.json        每位證人的官方網址、日期、委員會、
                                          職稱、機構、部門判定、字元數
  demo_data/hearings/00_ABOUT_THIS_DATA.txt

部門判定是關鍵字猜的，manifest 裡標 needs_review；定案前要人工看一遍。
"""
import argparse
import html
import json
import os
import re
import sys
import urllib.request
from datetime import datetime

import docx

OUT = os.path.join("demo_data", "hearings")
RAW = os.path.join(OUT, "_raw")
EN = os.path.join(OUT, "en")

# 主題：AI 治理。標題、日期與委員會會從原檔讀，這裡只列 package id。
HEARINGS = [
    "CHRG-118shrg52483",   # 2023-03-08 AI: Risks and Opportunities (HSGAC)
    "CHRG-118shrg52706",   # 2023-05-16 Oversight of A.I.: Rules for AI (Judiciary)
    "CHRG-118shrg52785",   # 2023-05-16 AI in Government (HSGAC)
    "CHRG-118shrg52709",   # 2023-06-13 AI and Human Rights (Judiciary)
    "CHRG-118hhrg52499",   # 2023-06-22 AI: Advancing Innovation (House Science)
    "CHRG-118shrg53503",   # 2023-07-25 Oversight of A.I.: Principles for Regulation
    "CHRG-118shrg53879",   # 2023-09-12 Oversight of A.I.: Legislating on AI
    "CHRG-118shrg59704",   # 2023-09-12 The Need for Transparency in AI (Commerce)
    "CHRG-118shrg53707",   # 2023-09-14 Governing AI Through Acquisition (HSGAC)
    "CHRG-118hhrg53382",   # 2023-09-14 How Are Federal Agencies Harnessing AI? (House Oversight; agency officials)
    "CHRG-118hhrg53782",   # 2023-10-18 Risk Management of AI (House Science)
    "CHRG-118hhrg56783",   # 2023-12-12 DHS and CISA's Role in Securing AI (House Homeland; officials)
    "CHRG-118shrg54718",   # 2024-01-10 Harnessing AI to Improve Government Services (HSGAC; officials)
    "CHRG-118hhrg54392",   # 2023-12-06 White House Policy on AI (House Oversight)
    "CHRG-118hhrg55220",   # 2024-03-21 White House Overreach on AI
    "CHRG-118shrg58917",   # 2024-04-16 Oversight of AI: Election Deepfakes
    "CHRG-118shrg61871",   # 2024-07-11 Privacy and the AI Accelerant (Commerce)
    "CHRG-118shrg63050",   # 2024-09-17 Oversight of AI: Insiders' Perspectives
    "CHRG-119hhrg60631",   # 2025-05-21 AI Regulation and the Future of U.S. Leadership
    "CHRG-119hhrg60818",   # 2025-06-05 The Federal Government in the Age of AI
    "CHRG-119shrg62739",   # 2025-09-10 America's AI Action Plan (Commerce)
    "CHRG-119hhrg61690",   # 2025-09-18 AI at a Crossroads: Nationwide Strategy or Californication?
]

URL_HTML = "https://www.govinfo.gov/content/pkg/{id}/html/{id}.htm"
URL_PDF = "https://www.govinfo.gov/content/pkg/{id}/pdf/{id}.pdf"
URL_DETAILS = "https://www.govinfo.gov/app/details/{id}"

TITLES = (r"Chair|Chairman|Chairwoman|Chairperson|The Chairman|The Chair|"
          r"Senator|Representative|Congressman|Congresswoman|Mr\.|Ms\.|Mrs\.|Dr\.|"
          r"Professor|General|Admiral|Ambassador|Secretary|Governor|Mayor|Judge|"
          r"Commissioner|Director")
TURN_RE = re.compile(
    rf"^ {{4}}(?P<label>(?:{TITLES}) (?P<name>[A-Z][A-Za-z'\-]+(?: [A-Z][A-Za-z'\-]+)?))(?: \[continuing\])?\.\s+(?P<text>.*)$")
NOT_NAMES = {"Chairman", "Chair", "Chairwoman", "President", "Speaker", "Secretary"}
STATEMENT_RE = re.compile(r"^\s*(OPENING )?(?:STATEMENTS?|TESTIMONY) OF (.+)$")
FOOTNOTE_RE = re.compile(r"\\\d+\\")
DEGREE_RE = re.compile(r"^(PH\.?D\.?|J\.?D\.?|M\.?D\.?|ESQ\.?|MPH|MBA)$", re.I)
MEMBER_HINT = re.compile(r"SENATOR FROM|REPRESENTATIVE IN CONGRESS|U\.S\. SENATOR|"
                         r"MEMBER OF CONGRESS|A U\.S\. REPRESENTATIVE", re.I)
CAPS_LINE = re.compile(r"^\s*[A-Z0-9 .,:;'\-\(\)&/]+$")
STAGE_RE = re.compile(r"\[(?:Laughter|Applause|Pause|Inaudible|Off microphone|Crosstalk)[^\]]*\]", re.I)

SECTOR_RULES = [
    ("academia", r"\b(University|Universit|College|Professor|School of|Institute of Technology|MIT|Berkeley|Stanford|Harvard|Princeton|Carnegie|Mila)\b"),
    ("government", r"\b(Department of|Office of|Administration|Bureau|Agency|Commission|Federal|U\.S\. Government|General Services|Government Accountability|Comptroller|Inspector General|GAO|OMB|OSTP|NIST|White House|Chief Data Scientist)\b"),
    ("industry", r"\b(Inc\.?|LLC|Corporation|Corp\.?|Company|Co\.|Chamber Of Commerce|Software Alliance|App Association|Alliance For Digital Innovation|NetChoice|Microsoft|Google|OpenAI|Anthropic|IBM|NVIDIA|Meta|Amazon|Palantir|Hugging Face|Technologies|Labs|Ventures|Capital|Media|Defender|Resemble|Openai)\b"),
    ("nonprofit", r"\b(Center|Centre|Foundation|Institute|Coalition|Council|Union|Association|Alliance|Society|Project|Fund|Initiative|Partnership|Brookings|RAND|EPIC|ACLU|Consumer|Advocacy|Civil|Rights|Witness|Now)\b"),
]
ROLE_RULES = [
    ("senior_management", r"\b(CEO|Chief Executive|President|Founder|Co-Founder|Chair|Chief .*Officer|General Counsel|Managing Director|Executive Director|Director)\b"),
    ("policy_maker", r"\b(Secretary|Administrator|Commissioner|Assistant|Deputy|Comptroller|Officer of the|Senior Advisor|Adviser)\b"),
    ("researcher", r"\b(Professor|Fellow|Researcher|Scientist|Scholar|Lecturer|Research)\b"),
]


# 人工複核（2026-09-17）。關鍵字規則猜錯或缺資料的，在這裡改；
# 沒列在這裡的證人維持規則判定，manifest 標 needs_review。
# 鍵是 (hearing id, 姓氏)。institution_type 用原本示範語料的四值。
OVERRIDES = {
    ("CHRG-118shrg52483", "Matheny"): {"institution_type": "nonprofit"},      # RAND 是非營利
    ("CHRG-118hhrg52499", "Matheny"): {"institution_type": "nonprofit"},
    ("CHRG-118hhrg52499", "Delangue"): {"institution_type": "industry"},
    ("CHRG-118hhrg52499", "Farshchi"): {"institution_type": "industry", "role_level": "senior_management"},
    ("CHRG-118hhrg52499", "Murdick"): {"institution_type": "academia"},       # CSET, Georgetown
    ("CHRG-118shrg53503", "Bengio"): {"role_level": "researcher"},
    ("CHRG-118shrg59704", "Strayer"): {"institution_type": "industry"},       # ITI 是產業公會
    ("CHRG-118shrg53707", "Raj"): {"institution_type": "industry"},
    ("CHRG-118shrg53707", "Roberts"): {"institution_type": "industry"},
    ("CHRG-118hhrg53382", "Tabassi"): {"institution_type": "government", "role_level": "policy_maker", "org": "NIST Information Technology Laboratory"},
    ("CHRG-118hhrg53382", "Kratsios"): {"institution_type": "industry", "org": "Scale AI"},
    ("CHRG-118hhrg53382", "Prabhakar"): {"role_level": "policy_maker"},
    ("CHRG-118hhrg53382", "Martell"): {"role_level": "policy_maker"},
    ("CHRG-118hhrg53382", "Hysen"): {"role_level": "policy_maker"},
    ("CHRG-118hhrg53782", "Tabassi"): {"institution_type": "government", "role_level": "policy_maker", "org": "NIST Information Technology Laboratory"},
    ("CHRG-118hhrg53782", "Kratsios"): {"institution_type": "industry", "org": "Scale AI"},
    ("CHRG-118hhrg56783", "Swanson"): {"institution_type": "industry"},
    ("CHRG-118hhrg56783", "O'Neill"): {"institution_type": "industry"},
    ("CHRG-118hhrg56783", "Stamos"): {"institution_type": "industry"},
    ("CHRG-118shrg54718", "Pahlka"): {"institution_type": "nonprofit", "role": "Author and former U.S. Deputy Chief Technology Officer"},
    ("CHRG-118shrg54718", "Blauer"): {"institution_type": "academia", "role_level": "senior_management", "org": "Johns Hopkins University"},
    ("CHRG-118shrg54718", "Noveck"): {"institution_type": "government", "role_level": "policy_maker", "role": "Chief Innovation Officer"},
    ("CHRG-118hhrg55220", "Lee"): {"institution_type": "nonprofit", "org": "Brookings Institution"},
    ("CHRG-118shrg58917", "Scanlan"): {"institution_type": "government", "role_level": "policy_maker"},
    ("CHRG-118shrg61871", "Tiwari"): {"institution_type": "industry", "org": "Mozilla"},
    ("CHRG-118shrg61871", "Reed"): {"institution_type": "industry", "org": "ACT | The App Association"},
    ("CHRG-118shrg63050", "Toner"): {"institution_type": "academia", "org": "Center for Security and Emerging Technology, Georgetown University"},
    ("CHRG-118shrg63050", "Harris"): {"institution_type": "nonprofit", "org": "California Initiative for Technology and Democracy"},
    ("CHRG-119hhrg60631", "Kak"): {"institution_type": "nonprofit", "role": "Co-Executive Director", "org": "AI Now Institute"},
    ("CHRG-119hhrg60631", "Thierer"): {"institution_type": "nonprofit", "org": "R Street Institute"},
    ("CHRG-119hhrg60631", "Bhargava"): {"institution_type": "industry", "role": "Managing Director", "org": "General Catalyst"},
    ("CHRG-119hhrg60818", "Shah"): {"institution_type": "industry"},
    ("CHRG-119hhrg60818", "Miller"): {"institution_type": "industry"},
    ("CHRG-119shrg62739", "Kratsios"): {"role_level": "policy_maker"},
    ("CHRG-119hhrg61690", "Bray"): {"institution_type": "nonprofit", "org": "Stimson Center"},
}
# 不收的證人：個人經歷證詞或媒體人，不屬於四類利害關係人
EXCLUDE = {
    ("CHRG-118shrg52785", "Siegel"): "journalist testifying as an author",
    ("CHRG-118shrg52709", "Destefano"): "personal-experience testimony, not a stakeholder category",
    ("CHRG-118shrg53707", "Shellenberger"): "journalist testifying as an author",
}


SUBSET_SEED = 20260918
SUBSET_PER_SECTOR = 6
SUBSET_SECTORS = ("industry", "academia", "government", "nonprofit")


def select_paper_subset(manifest, per=SUBSET_PER_SECTOR, seed=SUBSET_SEED):
    """
    稿件用的 24 人子集：四個部門各 6 位，固定種子的分層隨機抽樣。

    為什麼要子集：全部 80 份約 160 萬字元，雲端免費額度跑不完，地端要好幾個
    小時；而稿件的示範只需要一個四類各六人的語料——跟原本合成語料同一個設計，
    Table 6 的交叉表敘事不必改。全部 80 份仍然出貨，使用者可以自己跑。

    同一個人出席多場聽證會時只抽一次（Thierer 出席四場），否則「24 位受訪者」
    其實不到 24 個人。抽樣是隨機的而不是挑的：挑長度適中或內容漂亮的證詞，
    就是在替示範結果選資料。
    """
    import random
    rng = random.Random(seed)
    for m in manifest:
        m["paper_subset"] = False
    people = set()
    for sector in SUBSET_SECTORS:
        pool = [m for m in manifest if m["descriptors"]["institution_type"] == sector]
        rng.shuffle(pool)
        n = 0
        for m in pool:
            if m["name"] in people:
                continue
            m["paper_subset"] = True
            people.add(m["name"])
            n += 1
            if n == per:
                break
    return [m for m in manifest if m["paper_subset"]]


def fetch(pkg):
    os.makedirs(RAW, exist_ok=True)
    p = os.path.join(RAW, pkg + ".htm")
    if not os.path.isfile(p) or os.path.getsize(p) < 50000:
        req = urllib.request.Request(URL_HTML.format(id=pkg),
                                     headers={"User-Agent": "TACIT corpus builder (research)"})
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
        if b"Page Not Found" in data[:5000]:
            raise RuntimeError(f"{pkg}: govinfo has no HTML rendition at that id")
        open(p, "wb").write(data)
    raw = open(p, encoding="utf-8", errors="replace").read()
    m = re.search(r"<pre>(.*)</pre>", raw, re.S)
    text = html.unescape(m.group(1) if m else raw)
    # 官方檔案裡有換頁字元（\x0c）等控制字元，寫進 .docx 會被 XML 拒絕
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)


def header_info(text, pkg):
    title = re.search(r"<title>\s*-?\s*(.*?)</title>", text, re.S)
    head = text[:6000]
    date = None
    for m in re.finditer(r"^\s*(?:[A-Z]+DAY, )?([A-Z]+ \d{1,2}, \d{4})\s*$", head,
                         re.M | re.I):
        try:
            date = datetime.strptime(m.group(1).title(), "%B %d, %Y").date().isoformat()
            break
        except ValueError:
            continue
    chamber = {"s": "Senate", "h": "House", "j": "Joint"}.get(pkg[8], "?")
    # 「BEFORE THE … 委員會 … of the … 委員會 … CONGRESS」中間的大寫行接起來
    seg = re.search(r"BEFORE THE\s+(.*?)\s+(?:ONE HUNDRED|UNITED STATES SENATE|"
                    r"HOUSE OF REPRESENTATIVES)", head, re.S)
    comm_txt = re.sub(r"\s+", " ", seg.group(1)) if seg else ""
    parts = [c.strip().title() for c in re.split(r"\bof the\b", comm_txt, flags=re.I)
             if "COMMITTEE" in c.upper()]
    committee = " / ".join(parts[:2]) or "?"
    return {"date": date, "chamber": chamber, "committee": committee}


def parse_witnesses(body):
    """STATEMENT OF NAME, ROLE, ORG（可跨兩三行）→ 證人清單。"""
    lines = body.split("\n")
    out = []
    for i, ln in enumerate(lines):
        m = STATEMENT_RE.match(ln)
        if not m or m.group(1):            # OPENING STATEMENT 是議員
            continue
        # 標頭可能跨好幾行，眾議院的版本還會用空行隔開姓名／職稱／機構
        block = [m.group(2).strip()]
        j, blanks = i + 1, 0
        while j < len(lines) and blanks <= 1:
            ln2 = lines[j]
            if not ln2.strip():
                blanks += 1; j += 1; continue
            if CAPS_LINE.match(ln2) and not STATEMENT_RE.match(ln2) \
                    and not TURN_RE.match(ln2):
                block.append(ln2.strip()); blanks = 0; j += 1; continue
            break
        block = [re.sub(r"\s+", " ", FOOTNOTE_RE.sub("", b)).strip() for b in block]
        full = " ".join(block)
        if MEMBER_HINT.search(full):
            continue                       # 議員的開場陳述
        if len(block) >= 2 and "," not in block[0]:
            # 眾議院監督委員會的格式：STATEMENT OF NAME / 職稱 / 機構，各占一行
            full = ", ".join([block[0], block[1], " ".join(block[2:])]).strip(", ")
        full = re.sub(r"^HON\. ", "", full)
        full = re.sub(r"^(MR|MS|MRS|DR)\.? ", "", full)
        parts = [p.strip(" .") for p in full.split(",") if p.strip(" .")]
        parts = [p for k, p in enumerate(parts) if k == 0 or not DEGREE_RE.match(p)]
        if not parts:
            continue
        name = parts[0].title().replace("Jr", "Jr.").replace("Ii", "II").strip()
        name = re.sub(r"\bPh\.?d\b\.?", "", name, flags=re.I).strip(" ,")
        role = parts[1].title() if len(parts) > 1 else ""
        # 最後兩段通常是城市、州；只有在段數夠多時才切掉
        tail = 2 if len(parts) >= 5 else 0
        org = ", ".join(p.title() for p in parts[2:len(parts) - tail]) \
            if len(parts) > 2 else ""
        surname = re.sub(r"[^A-Za-z\-']", "", name.split()[-1]) if name else ""
        if surname.lower() in ("jr", "sr", "ii", "iii"):
            surname = re.sub(r"[^A-Za-z\-']", "", name.split()[-2])
        out.append({"name": name, "role": role, "org": org, "surname": surname,
                    "header": full})
    # 同一證人重複出現（例如第二輪）只留第一筆
    seen, uniq = set(), []
    for w in out:
        if w["surname"].lower() in seen:
            continue
        seen.add(w["surname"].lower()); uniq.append(w)
    return uniq


def parse_contents_witnesses(text):
    """
    目錄裡的證人清單：'Dr. Jason Matheny, President & CEO, RAND Corporation'。
    眾議院有些委員會（科學、能源商業）的正文標頭只寫 STATEMENT OF NAME，
    職稱與機構只出現在這裡；科學委員會連正文標頭都沒有，只能靠這份清單。
    """
    head = text[:12000]
    m = re.search(r"^\s*(?:WITNESSES|Witnesses):?\s*$", head, re.M)
    if not m:
        return []
    out, entry = [], []
    for ln in head[m.end():].splitlines():
        st = ln.strip()
        # 目錄裡每位證人下面是 Oral/Written/Prepared Statement 的頁碼行（有點線），
        # 那些行在下一個條件跳過；真正結束清單的是 Discussion / Appendix 這類標題
        if re.match(r"^(Discussion|Appendix|APPENDIX|Additional|ADDITIONAL|Submissions|SUBMISSIONS|Questions|QUESTIONS|Statements Submitted|STATEMENTS SUBMITTED|Alphabetical|\(I+\)|\(II+\))", st):
            break
        if not st:
            if entry:
                out.append(" ".join(entry)); entry = []
            continue
        if "...." in st or re.match(r"^(Oral|Written|Prepared) (Statement|Testimony)", st):
            if entry:
                out.append(" ".join(entry)); entry = []
            continue
        if re.match(r"^\d+$", st):
            continue
        entry.append(st)
    if entry:
        out.append(" ".join(entry))
    wits = []
    for e in out:
        e = FOOTNOTE_RE.sub("", e)
        e = re.sub(r"^(Hon\.|Dr\.|Mr\.|Ms\.|Mrs\.|Professor|The Honorable)\s+", "", e).strip()
        parts = [p.strip(" .") for p in e.split(",") if p.strip(" .")]
        parts = [p for k, p in enumerate(parts) if k == 0 or not DEGREE_RE.match(p)]
        if not parts or len(parts[0].split()) > 5 or MEMBER_HINT.search(e):
            continue
        name = parts[0].strip()
        surname = re.sub(r"[^A-Za-z\-']", "", name.split()[-1])
        if surname.lower() in ("jr", "sr", "ii", "iii") and len(name.split()) > 1:
            surname = re.sub(r"[^A-Za-z\-']", "", name.split()[-2])
        wits.append({"name": name, "role": parts[1] if len(parts) > 1 else "",
                     "org": ", ".join(parts[2:]) if len(parts) > 2 else "",
                     "surname": surname, "header": e})
    return wits


def guess(rules, text, default):
    for label, pat in rules:
        if re.search(pat, text, re.I):
            return label
    return default


def parse_turns(body):
    """把正文切成發言輪：[{speaker, name, paras}]。"""
    lines = body.split("\n")
    turns, cur, skipping = [], None, False
    for ln in lines:
        if not ln.strip():
            continue
        # 有些委員會（參院商務）把書面聲明、來函直接印在正文裡：
        # 「[The prepared statement of Ms. Kak follows:]」之後整份書面稿，直到
        # 下一位發言者。書面稿不收（可能仍有著作權，也不是口語資料）。
        if re.match(r"^\s*\[The .{0,120}follows?:?\]", ln) or \
                re.match(r"^\s*\[The (prepared )?statements? of", ln):
            skipping = True
            continue
        if skipping:
            if TURN_RE.match(ln):
                skipping = False
            else:
                continue
        if CAPS_LINE.match(ln) and len(ln.strip()) > 12 and not ln.strip().startswith("["):
            continue                      # 節標題（STATEMENT OF …、A P P E N D I X）
        m = TURN_RE.match(ln)
        if m and m.group("name").split()[-1] not in NOT_NAMES:
            cur = {"label": m.group("label"), "name": m.group("name"),
                   "paras": [m.group("text").strip()]}
            turns.append(cur)
            continue
        if cur is None:
            continue
        s = FOOTNOTE_RE.sub("", STAGE_RE.sub("", ln)).rstrip()
        if not s.strip():
            continue
        if s.startswith("    "):
            cur["paras"].append(s.strip())
        else:
            cur["paras"][-1] = (cur["paras"][-1] + " " + s.strip()).strip()
    for t in turns:
        t["text"] = "\n".join(p for p in t["paras"] if p and not p.startswith("["))
    return [t for t in turns if t["text"].strip()]


def build_hearing(pkg):
    text = fetch(pkg)
    info = header_info(text, pkg)
    m_title = re.search(r"<title>\s*-?\s*(.*?)</title>", open(os.path.join(RAW, pkg + ".htm"),
                                                             encoding="utf-8", errors="replace").read(), re.S)
    title = html.unescape(m_title.group(1)).strip().title() if m_title else pkg
    start = re.search(r"^\s*OPENING STATEMENT OF", text, re.M)
    end = re.search(r"^\s*\[Whereupon", text, re.M)
    body = text[start.start() if start else 0: end.start() if end else len(text)]
    witnesses = parse_witnesses(body)
    toc = {w["surname"].lower(): w for w in parse_contents_witnesses(text)}
    for w in witnesses:
        t = toc.get(w["surname"].lower())
        if t:
            if not w["role"]:
                w["role"] = t["role"]
            if not w["org"]:
                w["org"] = t["org"]
    if not witnesses:
        witnesses = list(toc.values())
    turns = parse_turns(body)
    by_surname = {w["surname"].lower(): w for w in witnesses}

    per = {w["surname"].lower(): [] for w in witnesses}
    last_member = None
    for t in turns:
        key = t["name"].split()[-1].lower()
        if key in by_surname:
            blk = []
            if last_member:
                blk.append(("Interviewer", last_member["label"], last_member["text"]))
            blk.append(("Respondent", t["label"], t["text"]))
            per[key].append(blk)
        else:
            last_member = t
    return {"id": pkg, "title": title, **info, "witnesses": witnesses, "per": per,
            "n_turns": len(turns)}


def write_docx(path, heading, source_line, blocks):
    d = docx.Document()
    d.add_paragraph(heading)
    d.add_paragraph(source_line)
    seen_first = False
    for blk in blocks:
        for kind, who, text in blk:
            if kind == "Interviewer":
                d.add_paragraph(f"[Interviewer] ({who}) {text}")
            else:
                d.add_paragraph(f"[Respondent] {text}")
                seen_first = True
    d.save(path)


ABOUT = """PUBLIC HEARING CORPUS — AI governance hearings of the United States Congress

Source: U.S. Government Publishing Office, govinfo.gov, collection CHRG
        (Congressional Hearings). Every file names its hearing package id; the
        official record is at https://www.govinfo.gov/app/details/<id> with
        HTML and PDF renditions under https://www.govinfo.gov/content/pkg/<id>/.
Licence: works of the United States Government are not subject to copyright
        (17 U.S.C. § 105). Only the spoken proceedings transcribed by the
        official reporter are included. Witnesses' written statements submitted
        for the record are excluded, because a non-government author may hold
        copyright in a prepared text.
Shape:  one file per witness. The first [Respondent] block is the witness's
        oral opening statement; each later pair is a member's question
        ([Interviewer], with the member named) followed by that witness's answer.
        Members of Congress are questioners, not respondents, in this corpus.
Built:  {built} by make_hearing_corpus.py from the package ids listed in
        manifest.json. Sector and role assignments in manifest.json were
        suggested by keyword rules and then reviewed by hand.
"""


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="只列證人與部門判定，不寫檔")
    ap.add_argument("--only", default="", help="只處理這個 package id")
    ap.add_argument("--min-chars", type=int, default=4000,
                    help="證人口頭發言少於此字元數就不收（太短沒有分析價值）")
    a = ap.parse_args(argv)

    ids = [a.only] if a.only else HEARINGS
    manifest, excluded, seq = [], [], 1
    os.makedirs(EN, exist_ok=True)
    for pkg in ids:
        try:
            h = build_hearing(pkg)
        except Exception as e:                           # noqa: BLE001
            print(f"!! {pkg}: {type(e).__name__}: {e}")
            continue
        print(f"\n{pkg}  {h['date']}  {h['chamber']}  {h['committee']}\n  {h['title']}")
        for w in h["witnesses"]:
            blocks = h["per"].get(w["surname"].lower(), [])
            chars = sum(len(t) for blk in blocks for k, _, t in blk if k == "Respondent")
            n_q = sum(1 for blk in blocks for k, _, _ in blk if k == "Interviewer")
            sector = guess(SECTOR_RULES, f"{w['role']} {w['org']}", "other")
            role = guess(ROLE_RULES, w["role"], "other")
            key = (pkg, w["surname"])
            ov = OVERRIDES.get(key, {})
            sector = ov.get("institution_type", sector)
            role = ov.get("role_level", role)
            w["role"] = ov.get("role", w["role"])
            w["org"] = ov.get("org", w["org"])
            reviewed = key in OVERRIDES
            if key in EXCLUDE:
                flag = f"  (excluded: {EXCLUDE[key]})"
            else:
                flag = "" if chars >= a.min_chars else "  (skipped: too short)"
            print(f"  - {w['name']:28s} {w['role'][:34]:34s} {w['org'][:30]:30s} "
                  f"→ {sector:10s} {role:18s} {chars:>6,} chars, {n_q} Q"
                  f"{' ✓' if reviewed else ''}{flag}")
            if key in EXCLUDE:
                excluded.append({"hearing": pkg, "name": w["name"], "reason": EXCLUDE[key]})
                continue
            if a.list or chars < a.min_chars:
                continue
            fn = f"{seq:02d}_{pkg}_{w['surname']}.docx"
            write_docx(
                os.path.join(EN, fn),
                f"Hearing transcript {pkg} — {w['name']}, {w['role']}, {w['org']}",
                f"Source: {URL_DETAILS.format(id=pkg)}  |  {h['title']}  |  "
                f"{h['chamber']}, {h['committee']}  |  {h['date']}  |  "
                f"PUBLIC DOMAIN (17 U.S.C. § 105)  |  spoken proceedings only",
                blocks)
            manifest.append({
                "file": fn, "respondent_id": f"{pkg}_{w['surname']}",
                "name": w["name"], "role": w["role"], "org": w["org"],
                "hearing": pkg, "hearing_title": h["title"], "date": h["date"],
                "chamber": h["chamber"], "committee": h["committee"],
                "url_details": URL_DETAILS.format(id=pkg),
                "url_html": URL_HTML.format(id=pkg), "url_pdf": URL_PDF.format(id=pkg),
                "licence": "Public domain, 17 U.S.C. § 105 (spoken proceedings only)",
                "descriptors": {"institution_type": sector, "role_level": role,
                                "sector": "ict_ai", "experience": "unspecified"},
                "needs_review": not reviewed,
                "chars_spoken": chars, "n_questions": n_q,
            })
            seq += 1
    if not a.list:
        subset = select_paper_subset(manifest)
        with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump({"built": datetime.now().isoformat(timespec="seconds"),
                       "hearings": ids,
                       "paper_subset": {"seed": SUBSET_SEED, "per_sector": SUBSET_PER_SECTOR,
                                        "n": len(subset),
                                        "chars": sum(m["chars_spoken"] for m in subset)},
                       "respondents": manifest,
                       "excluded": excluded},
                      f, ensure_ascii=False, indent=2)
        with open(os.path.join(OUT, "00_ABOUT_THIS_DATA.txt"), "w", encoding="utf-8") as f:
            f.write(ABOUT.format(built=datetime.now().date().isoformat()))
        from collections import Counter
        c = Counter(m["descriptors"]["institution_type"] for m in manifest)
        print(f"\n{len(manifest)} respondents written to {EN}; institution_type: {dict(c)}")
        print(f"total spoken chars {sum(m['chars_spoken'] for m in manifest):,}; "
              f"median {sorted(m['chars_spoken'] for m in manifest)[len(manifest)//2]:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
