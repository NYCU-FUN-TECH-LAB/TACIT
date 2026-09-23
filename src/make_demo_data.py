"""
make_demo_data.py — 產生示範資料
=====================================================================

    python make_demo_data.py

產出：

    demo_data/en/   24 份英文逐字稿 .docx + 資料聲明
    demo_data/zh/    6 份中文逐字稿 .docx + 資料聲明
    analyses/       30 份參考分析紀錄 .json

為什麼要連參考分析一起產出
--------------------------
沒有金鑰、沒有地端模型的人（例如第一次打開這個 repo 的人）應該
也能把每一個頁籤打開來看。逐字稿只讓人看得到「執行分析」那一頁，
其餘八個頁籤全是空的。附上參考分析，交叉分析、主題結構、信度檢定
才有東西可算。

這批參考分析是**與逐字稿一起寫出來的**，不是某一次模型執行的輸出。
這一點必須講清楚，否則會被誤讀為「這就是模型的表現」。真正的模型
輸出取決於供應者、模型與當次取樣，本來就不該由 repo 預先決定。
把它們拿來當信度檢定的對照組是合理用法：你自己跑一次，再跟這份
參考編碼比 κ，看的是你選的模型與這份設計好的編碼有多接近。

逐字稿與參考編碼之間的一致性
----------------------------
每一段引文都必須是逐字稿的逐字子字串。這裡的做法是先寫出 .docx，
再用與軟體完全相同的解析邏輯把它讀回來，用讀回來的文字當作紀錄裡的
transcript，然後逐條驗證引文對得上。這樣可以同時擋掉兩類錯誤：
引文抄錯，以及 .docx 版面讓解析結果與原始字串不一致。
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root; sources live in src/
sys.path.insert(0, ROOT)

import demo_transcripts_en as EN          # noqa: E402
import demo_transcripts_zh as ZH          # noqa: E402
import tacit_schema as S                  # noqa: E402
import tacit_framework as F               # noqa: E402

EN_DIR = os.path.join(ROOT, "demo_data", "en")
ZH_DIR = os.path.join(ROOT, "demo_data", "zh")
ANALYSES_DIR = os.path.join(ROOT, "analyses")

# 表格式版面的份數。兩種版面都要有，才能實測 .docx 匯入的兩條解析路徑；
# 多數維持段落式，因為那才是研究者手上逐字稿的常見樣子。
TABLE_LAYOUT_EN = {"P03", "A03", "G03", "N03"}


EN_NOTICE = """\
ABOUT THIS DATA
===============

Every transcript in this folder is FICTIONAL. It was written by a language
model (Claude, Anthropic) for software demonstration, teaching and
regression testing. The reference codings in analyses/ were written by the
same model in the same request, so agreement measured against them is an
upper bound: the text was composed to exemplify the codes.

  * The respondents, organisations, city, project and events do not exist.
  * Nothing here corresponds to any real person or organisation.
  * It must not be cited as a source of empirical data.
  * It must not be used to support any empirical claim about industry,
    academia, government or civil society.

The fictional case
------------------
{case}

Port Calder, a fictional mid-sized coastal city, has installed AI-enabled
adaptive traffic signals with pedestrian detection at thirty intersections.
Roadside cameras identify pedestrians and vehicles and adjust signal timing
dynamically. These transcripts simulate semi-structured interviews with
{n} stakeholders about responsible innovation practice during the
deployment.

Why synthetic data
------------------
Manuals, screenshots and papers circulate publicly. Screenshots containing
verbatim quotations from real interviews would exceed the scope of any
realistic informed-consent agreement. Synthetic data satisfies three needs
at once: screenshots can be published, anyone can reproduce the analysis,
and the material can be used for teaching.

Why twenty-four
---------------
Six transcripts are enough to walk through the interface and not enough for
any inferential statistic to run. In a 2x4 crosstab of institution type
against polarity, expected cell counts land around one or two, the
chi-square assumptions fail, and the tool correctly refuses to print a
p-value. A newcomer then opens the cross-analysis tab and sees a column of
"insufficient data" notices.

With twenty-four respondents, six in each of four institution types, most
expected counts exceed five, and the roughly {segments} coded segments give the
theme induction enough first-order concepts to work with.

What is deliberately built in
-----------------------------
* Polarity is deliberately unevenly distributed across institution types.
  Industry accounts lean negative, academic accounts lean positive,
  government is mixed, and civil society accounts pair positive engagement
  with negative responsiveness. A crosstab can only show an association if
  the data contains one; uniformly random demonstration data would make
  every test non-significant and demonstrate nothing.
* Some passages are coded on two dimensions at once, so the co-occurrence
  matrix has something to compute.
* Several passages are deliberately ambiguous — for example, risk foresight
  undertaken for commercial rather than ethical reasons — so the code review
  interface has genuine disagreements to resolve and reliability statistics
  are not spuriously perfect.
* Fillers, self-corrections and digressions are preserved.
* Every file carries the same heading and synthetic-data notice, and the
  importer reads them as part of the transcript. Raw term discovery in the
  lexicon tab therefore surfaces "port calder adaptive traffic", "synthetic
  data" and similar boilerplate near the top. This is left in deliberately:
  document boilerplate really does dominate raw frequency counts, and it is
  worth seeing that the log-odds feature induction step removes it — none of
  those terms appear in the per-group feature lists, because a term present
  in every document distinguishes no group from any other.

File layouts
------------
Most files use a paragraph layout, with each turn prefixed [Interviewer] or
[Respondent]. Four files ({table}) use a two-column table layout with
"Speaker" and "Content" headers. Both are parsed by the importer; both are
included so that the two parsing paths are exercised.

Speaker markers are what the reliability module uses to divide the
transcript into codeable units. Keep something similar in your own data.

Reference codings
-----------------
The analyses/ folder contains a reference coding for every transcript here.
These were written alongside the transcripts. They are NOT the output of any
particular model run, and should not be read as evidence of how well any
model performs. They exist so that every tab in the application can be
opened and inspected without an API key or a local model.

Using them as a comparison set for reliability is a legitimate use: run the
coder yourself, then compare your run against this reference coding to see
how closely your chosen model tracks a fixed, deliberately designed scheme.
"""


ZH_NOTICE_HEADER = """\
關於這批資料
============

本資料夾中的所有逐字稿均為**虛構的合成資料**，由語言模型撰寫，
用途為軟體展示、教學示範與程式測試。

  * 受訪者、機構、城市、專案與事件皆不存在。
  * 不對應任何真實個人或組織。
  * 不得引用為經驗研究的資料來源。
  * 不得作為任何實證主張的依據。

這批中文資料的用途
------------------
主要的示範語料是 demo_data/en/ 底下的 24 份英文逐字稿——只有那一批
的樣本數足以讓推論統計跑得出來。這 6 份中文逐字稿保留下來的理由是
它們示範了英文語料示範不到的東西：繁體中文的斷詞（CKIP 或內建的
n-gram 後備方法）、中文詞庫誘導，以及介面與分析語言的獨立切換。

虛構案例設定
------------
{case}

濱海市（虛構）在市區三十處路口導入智慧號誌與行人偵測系統，
以路側攝影機辨識行人與車流，動態調整號誌秒數。
本批逐字稿模擬對六位利害關係人的半結構式訪談，
探討此一技術部署過程中的負責任創新實踐。

檔案版面
--------
01–05 為段落式版面（每段以【訪談者】／【受訪者】標記說話者）。
06 為表格式版面（含「講者」與「內容」兩欄）。
兩種版面本軟體皆可解析，一併提供以示範匯入功能。

說話者標記為信度檢定模組切分編碼單元的依據，
自備逐字稿時建議保留類似標記。
"""


# =====================================================================
# .docx 產出
# =====================================================================
def _add_header(doc, title, note):
    from docx.shared import Pt
    doc.add_heading(title, level=1)
    p = doc.add_paragraph()
    run = p.add_run(note)
    run.italic = True
    run.font.size = Pt(9)


def build_paragraph_doc(doc, title, note, turns):
    from docx.shared import Pt
    _add_header(doc, title, note)
    for mark, text in turns:
        para = doc.add_paragraph(f"{mark} {text}")
        para.paragraph_format.space_after = Pt(6)


def build_table_doc(doc, title, note, turns, headers):
    _add_header(doc, title, note)
    table = doc.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    hdr[0].text, hdr[1].text = headers
    for mark, text in turns:
        cells = table.add_row().cells
        cells[0].text = mark
        cells[1].text = text


def read_back(path):
    """
    用與軟體完全相同的邏輯把 .docx 讀回來。

    直接匯入 app.read_docx 會把整個 Streamlit 介面一起執行，所以這裡
    重述同一套解析規則。兩邊若走岔了，test_demo_data 會抓到——那支測試
    比對的是這個函式的輸出與軟體實際解析的結果。
    """
    import docx
    d = docx.Document(path)
    out = [p.text for p in d.paragraphs if p.text.strip()]
    speaker_names = ["講者", "Speaker", "speaker", "發言人"]
    content_names = ["內容", "Content", "content", "逐字稿"]
    for table in d.tables:
        headers = [c.text.strip() for c in table.rows[0].cells] if table.rows else []
        if any(h in speaker_names + content_names for h in headers):
            si = next((i for i, h in enumerate(headers) if h in speaker_names), None)
            ci = next((i for i, h in enumerate(headers) if h in content_names), None)
            for row in table.rows[1:]:
                cells = [c.text.strip() for c in row.cells]
                if ci is not None and ci < len(cells) and cells[ci]:
                    sp = cells[si] if si is not None and si < len(cells) else ""
                    out.append(f"【{sp}】{cells[ci]}" if sp else cells[ci])
        else:
            for row in table.rows:
                vals = [c.text.strip() for c in row.cells if c.text.strip()]
                if vals:
                    out.append(" | ".join(vals))
    return "\n".join(out)


# =====================================================================
# 參考分析紀錄
# =====================================================================
def make_record(respondent, role, descriptors, segments, transcript,
                transcript_file, summary, basis):
    d = dict(descriptors)
    d[S.DESCRIPTOR_BASIS] = basis
    return {
        S.RESPONDENT: respondent,
        S.DESCRIPTORS: d,
        S.SEGMENTS: segments,
        S.DELETED_SEGMENTS: [],
        S.SUMMARY: summary,
        S.TRANSCRIPT: transcript,
        S.TRANSCRIPT_FILE: transcript_file,
        S.META: {"schema_version": S.SCHEMA_VERSION,
                 "framework_id": F.DEFAULT_FRAMEWORK_ID,
                 # 來源標成 demo/reference，不要偽裝成某次模型執行的輸出。
                 # 這個欄位會出現在匯出檔與稽核軌跡裡，寫錯就是在誤導讀者。
                 "source": "demo/reference-coding"},
    }


def verify(rec, rid):
    """引文必須是 transcript 的逐字子字串，否則信度模組定位不到單元。"""
    tr = rec[S.TRANSCRIPT]
    bad = [s[S.QUOTE][:60] for s in rec[S.SEGMENTS] if s[S.QUOTE] not in tr]
    if bad:
        raise SystemExit(f"{rid}: {len(bad)} quote(s) not found in the parsed "
                         f"transcript. First: {bad[0]}")


# =====================================================================
# 主流程
# =====================================================================
def build_english(Document):
    os.makedirs(EN_DIR, exist_ok=True)
    note_tpl = (f"Case: {EN.DEMO_CASE}  |  SYNTHETIC DATA — not a real "
                f"interview")
    made = 0
    for i, rid in enumerate(EN.all_ids(), start=1):
        role = EN.role_of(rid)
        stem = f"{i:02d}_{rid}_{role.split(',')[0].replace(' ', '-')}"
        path = os.path.join(EN_DIR, stem + ".docx")
        turns = [(EN.Q_MARK if k == "Q" else EN.A_MARK, txt)
                 for k, txt, _ in EN.TRANSCRIPTS[rid]["turns"]]
        doc = Document()
        title = f"Interview transcript {rid} — {role}"
        if rid in TABLE_LAYOUT_EN:
            # 表格式版面裡，說話者欄不該再帶方括號——read_docx 會自己補上
            # 【】。留著方括號會做出【[Respondent]】這種雙重標記。
            plain = [(m.strip("[]"), t) for m, t in turns]
            build_table_doc(doc, title, note_tpl, plain, ("Speaker", "Content"))
        else:
            build_paragraph_doc(doc, title, note_tpl, turns)
        doc.save(path)

        transcript = read_back(path)
        rec = make_record(
            respondent=f"{rid} ({role})",
            role=role,
            descriptors=EN.descriptors_of(rid),
            segments=EN.segments_of(rid),
            transcript=transcript,
            transcript_file=stem + ".docx",
            summary=EN.summary_of(rid),
            basis=f"Interview transcript: {rid} ({role})")
        verify(rec, rid)
        with open(os.path.join(ANALYSES_DIR, f"demo_en_{rid}.json"), "w",
                  encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=2)
        made += 1
        print(f"  {stem}.docx"
              f"{'  [table layout]' if rid in TABLE_LAYOUT_EN else ''}")

    s = EN.stats()
    with open(os.path.join(EN_DIR, "00_ABOUT_THIS_DATA.txt"), "w",
              encoding="utf-8") as f:
        f.write(EN_NOTICE.format(case=EN.DEMO_CASE, n=s["respondents"],
                                 segments=s["segments"],
                                 table=", ".join(sorted(TABLE_LAYOUT_EN))))
    return made


def build_chinese(Document):
    """
    中文那批沒有隨附參考編碼——它的用途是示範斷詞與語言路由，不是統計。
    只產出 .docx 與資料聲明。
    """
    os.makedirs(ZH_DIR, exist_ok=True)
    layout = {"產A": ("01_產A_系統整合商", "paragraph"),
              "產B": ("02_產B_AI新創技術長", "paragraph"),
              "學C": ("03_學C_交通工程教授", "paragraph"),
              "學D": ("04_學D_科技與社會研究", "paragraph"),
              "政E": ("05_政E_市府交通局", "paragraph"),
              "民F": ("06_民F_身障權益團體", "table")}
    titles = {"產A": "系統整合商 專案總監", "產B": "AI 新創公司 技術長",
              "學C": "大學 交通工程教授", "學D": "科技與社會研究 博士後研究員",
              "政E": "市政府交通局 科長", "民F": "身障權益倡議團體 秘書長"}
    note = f"案例：{ZH.DEMO_CASE}　｜　※ 本逐字稿為合成資料，非真實訪談"
    made = 0
    for rid, (stem, kind) in layout.items():
        turns = []
        for line in ZH.text_of(rid).splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("【訪談者】"):
                turns.append(("訪談者", line[5:]))
            elif line.startswith("【受訪者】"):
                turns.append(("受訪者", line[5:]))
            elif turns:
                turns[-1] = (turns[-1][0], turns[-1][1] + line)
        doc = Document()
        title = f"訪談逐字稿：{rid}（{titles[rid]}）"
        if kind == "table":
            build_table_doc(doc, title, note, turns, ("講者", "內容"))
        else:
            build_paragraph_doc(doc, title, note,
                                [(f"【{sp}】", tx) for sp, tx in turns])
        doc.save(os.path.join(ZH_DIR, stem + ".docx"))
        made += 1
        print(f"  {stem}.docx{'  [表格式版面]' if kind == 'table' else ''}")
    with open(os.path.join(ZH_DIR, "00_關於這批資料.txt"), "w",
              encoding="utf-8") as f:
        f.write(ZH_NOTICE_HEADER.format(case=ZH.DEMO_CASE))
    return made


def main():
    try:
        from docx import Document
    except ImportError:
        print("python-docx is required.  pip install python-docx")
        return 1

    os.makedirs(ANALYSES_DIR, exist_ok=True)
    print("English demonstration corpus")
    print("-" * 60)
    n_en = build_english(Document)
    print()
    print("Chinese demonstration corpus")
    print("-" * 60)
    n_zh = build_chinese(Document)

    s = EN.stats()
    print()
    print("=" * 60)
    print(f"  {n_en} English transcripts  ->  demo_data/en/")
    print(f"  {n_zh} Chinese transcripts  ->  demo_data/zh/")
    print(f"  {n_en} reference codings    ->  analyses/")
    print()
    print(f"  {s['segments']} coded segments, {s['multi_coded']} of them "
          f"multi-coded "
          f"({100 * s['multi_coded'] / s['segments']:.0f}%)")
    # 兩個編碼數都要印，而且要講清楚差別在哪。
    # 上面那一個是 184，每一份分析報的是下面那一個（181），
    # 兩者相差三筆——同維度同極性但理由不同的碼。
    # 只印一個數字，等於讓讀者自己去撞這個矛盾。
    n_assigned = sum(s["by_dimension"].values())
    n_units = s.get("analysis_units", n_assigned)
    print(f"  {n_assigned} codes assigned (one per researcher judgement)")
    if n_units != n_assigned:
        print(f"  {n_units} analysis units "
              f"(distinct segment x dimension x polarity; "
              f"{n_assigned - n_units} segments carry two judgements on the "
              f"same dimension and polarity)")
    print(f"  polarity  {s['by_polarity']}")
    print(f"  dimension {s['by_dimension']}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
