"""
demo_transcripts_en.py — 合成示範逐字稿（英文，24 位受訪者）
=====================================================================

【重要聲明】
本檔所有內容均為**虛構**，由語言模型撰寫，用於軟體展示、教學與測試。
受訪者、機構、城市、專案、事件皆不存在，不對應任何真實個人或組織，
亦不得引用為經驗研究資料。

Everything in this file is fictional. The respondents, organisations, city,
project and events do not exist. The material is written for software
demonstration, teaching and regression testing. It must not be cited as
empirical data or used to support any empirical claim.


為什麼是 24 位而不是 6 位
-------------------------
前一版隨附六份逐字稿。六個人足以走完介面流程，卻不足以讓任何一項
推論統計跑得出來：機構類型 × 極性的 2×4 交叉表，期望次數多半落在 1～2，
卡方檢定的假設不成立，工具會照規則拒絕輸出 p 值。結果是第一次使用的人打開
「交互分析」頁籤，看到的是一連串「樣本不足，不予計算」——工具最該
被檢視的部分，反而完全看不到。

24 位（四種機構類型各 6 位）讓 2×4 交叉表的期望次數多數 ≥5，卡方與
Cramér's V 有意義；約 300 個編碼段落也讓主題歸納有足夠的一階概念可以
抽象，讓對數勝算比的特徵詞誘導不會被單一受訪者的用字主導。

這個數字也貼近真實：質性訪談研究常見的樣本數就在 20～40 之間。


設計上的刻意安排
----------------
* 四種機構類型各 6 人，交叉分析才有對照組，且每一格都填得滿。
* **極性分布刻意不均**：產業界偏負向、學術界偏正向、政府混合、
  民間組織對「參與」正向但對「回應性」負向。交叉表要看得出關聯，
  資料裡就必須真的有關聯——全隨機的示範資料會讓每一項檢定都不顯著，
  等於什麼也沒示範到。
* 每份逐字稿都含**同時觸及兩個維度**的段落，共現分析才有東西可算。
* 刻意保留數個**模稜兩可**的段落（例如出於商業自利而做的風險預想），
  讓「編碼複核」介面有實際可爭議的對象，也讓信度檢定不會虛假地完美。
* 保留口語填充詞、自我修正、離題，貼近真實逐字稿的難度。
* 兩種 .docx 版面各做幾份（段落式與表格式），實測兩條匯入解析路徑。

虛構案例設定
------------
Port Calder（虛構的中型沿海城市）在市區三十處路口部署 AI 自適應號誌
與行人偵測系統：以路側攝影機辨識行人與車流，動態調整號誌秒數。
本批逐字稿模擬對 24 位利害關係人的半結構式訪談，探討此一技術部署
過程中的負責任創新實踐。

與 demo_transcripts_zh.py 的關係
--------------------------------
中文那批是同一個案例設定的另一個城市（濱海市），六位受訪者。
兩批合起來可以示範語言路由：同一套框架、同一套統計，
中文走 CKIP 斷詞、英文走空白斷詞，語意編碼兩者都不經過斷詞。
"""

DEMO_CASE = "Port Calder adaptive traffic signal and pedestrian detection system"

# 每位受訪者：識別代號 -> {role, descriptors, turns, summary}
TRANSCRIPTS = {}

# 說話者標記。信度檢定模組以此切分編碼單元，自備逐字稿時建議保留類似標記。
Q_MARK = "[Interviewer]"
A_MARK = "[Respondent]"


class CodingError(ValueError):
    """參考編碼與逐字稿對不起來——引文不是原文的子字串。"""


def C(dimension, polarity, title, quote, rationale):
    """
    一個參考編碼。

    quote 必須是所在回答段落的**逐字子字串**。這條規則不是形式主義：
    信度檢定要把引文對回逐字稿才能定位編碼單元，引文只要差一個字就
    對不上，抽樣框會莫名其妙少掉單元，而且極難查。所以在建檔時就驗，
    不要等到跑統計才發現。
    """
    return {"dimension": dimension, "polarity": polarity, "title": title,
            "quote": quote, "rationale": rationale}


def Q(text):
    return ("Q", text, [])


def A(text, *codes):
    return ("A", text, list(codes))


def R(rid, role, descriptors, turns, summary):
    """建立一位受訪者，並在建檔當下就驗證每一段引文都對得上原文。"""
    for kind, text, codes in turns:
        for c in codes:
            if c["quote"] not in text:
                raise CodingError(
                    f"{rid}: quote not found verbatim in the answer it is "
                    f"attached to.\n  quote: {c['quote'][:80]}...\n"
                    f"  answer: {text[:80]}...")
    TRANSCRIPTS[rid] = {"role": role, "descriptors": descriptors,
                        "turns": turns, "summary": summary}
    return TRANSCRIPTS[rid]


# =====================================================================
# 存取函式（與 demo_transcripts_zh 介面一致，讓兩批可以互換使用）
# =====================================================================
def all_ids():
    return list(TRANSCRIPTS)


def text_of(rid):
    """完整逐字稿文字，含說話者標記。"""
    parts = []
    for kind, text, _ in TRANSCRIPTS[rid]["turns"]:
        parts.append(f"{Q_MARK} {text}" if kind == "Q" else f"{A_MARK} {text}")
    return "\n\n".join(parts)


def descriptors_of(rid):
    return dict(TRANSCRIPTS[rid]["descriptors"])


def role_of(rid):
    return TRANSCRIPTS[rid]["role"]


def summary_of(rid):
    return TRANSCRIPTS[rid]["summary"]


# 兩個引文的合併上限（字元）。見 segments_of 的說明。
#
# 240 這個值是回頭挑的，挑的依據是多重編碼率落在 24% 左右——真實的
# 演繹式編碼裡，一個段落同時落在兩個維度上大約就是兩成上下。放寬到 480
# 會做出 47%，那不像編碼結果，像切分方式出了問題；收到 200 只剩 13%，
# 共現矩陣又太稀疏，看不出樣態。這個數字是示範資料的參數，不是軟體的
# 參數：真實資料的段落切分由模型與研究者決定，與此無關。
MERGE_SPAN_LIMIT = 240


def segments_of(rid):
    """
    參考編碼段落，格式與軟體儲存的分析紀錄相同。

    同一段回答上的多個碼，什麼時候算「同一個段落」？
    ------------------------------------------------
    共現分析算的是「同一個段落上同時出現了哪些碼」。若每個碼都自成一個
    段落，共現矩陣會全部歸零——不是因為資料裡沒有共現，而是因為切分方式
    讓共現無從發生。所以切分規則會直接決定共現分析有沒有東西可算。

    這裡採用的規則是：同一段回答裡，兩個碼的引文若**在原文中的位置夠近**
    （涵蓋兩者的最短區間不超過 MERGE_SPAN_LIMIT 個字元），視為指向同一個
    passage，合併成一個段落，並以涵蓋兩者的那一段文字作為引文。位置相隔
    很遠的兩個碼則各自成段。

    這條規則貼近人工編碼的實際做法：編碼者面對一段回答時，是先圈出一個
    可引用的 passage，再判斷它落在哪些維度上；同一句話同時體現兩個維度
    是常態，而一段回答的開頭與結尾談的是兩件事也是常態。

    合併後的引文一定是原文的逐字子字串，這是信度模組把引文對回逐字稿的
    前提，R() 在建檔時已經逐條驗過。
    """
    out = []
    n = 0
    for kind, text, codes in TRANSCRIPTS[rid]["turns"]:
        if kind != "A" or not codes:
            continue
        spans = [(text.index(c["quote"]),
                  text.index(c["quote"]) + len(c["quote"]), c) for c in codes]
        spans.sort(key=lambda s: s[0])

        groups = []                       # [(start, end, [codes])]
        for start, end, c in spans:
            if groups and max(groups[-1][1], end) - groups[-1][0] <= MERGE_SPAN_LIMIT:
                g = groups[-1]
                groups[-1] = (g[0], max(g[1], end), g[2] + [c])
            else:
                groups.append((start, end, [c]))

        for start, end, group in groups:
            n += 1
            out.append({
                "segment_id": f"S{n:03d}",
                "title": group[0]["title"],
                "quote": text[start:end],
                "full_text": text,
                "codes": [{"dimension": c["dimension"],
                           "polarity": c["polarity"],
                           "rationale": c["rationale"]} for c in group],
            })
    return out


def stats():
    """建檔用的分布摘要。用來檢查刻意安排的不均衡有沒有真的做出來。"""
    from collections import Counter
    inst, pol, dim, pair = Counter(), Counter(), Counter(), Counter()
    n_seg = n_multi = n_units = 0
    for rid in TRANSCRIPTS:
        it = TRANSCRIPTS[rid]["descriptors"]["institution_type"]
        inst[it] += 1
        for s in segments_of(rid):
            n_seg += 1
            if len(s["codes"]) > 1:
                n_multi += 1
            # 分析單位 = 相異的 (維度, 極性)。分析層以此為單位（見
            # tacit_schema.codes_of），所以這個數字才是交叉表與卡方的 n。
            n_units += len({(c["dimension"], c["polarity"]) for c in s["codes"]})
            for c in s["codes"]:
                pol[c["polarity"]] += 1
                dim[c["dimension"]] += 1
                pair[(it, c["polarity"])] += 1
    return {"respondents": len(TRANSCRIPTS), "segments": n_seg,
            "multi_coded": n_multi, "by_institution": dict(inst),
            "analysis_units": n_units,
            "by_polarity": dict(pol), "by_dimension": dict(dim),
            "institution_x_polarity": {f"{k[0]}/{k[1]}": v
                                       for k, v in sorted(pair.items())}}


# 維度識別碼，與 frameworks/ri_stilgoe_2013.json 一致
ANT, REF, ENG, RES = "anticipation", "reflexivity", "engagement", "responsiveness"

from _demo_en_industry import build as _b1      # noqa: E402
from _demo_en_academia import build as _b2      # noqa: E402
from _demo_en_government import build as _b3    # noqa: E402
from _demo_en_nonprofit import build as _b4     # noqa: E402

for _b in (_b1, _b2, _b3, _b4):
    _b(R, Q, A, C, ANT, REF, ENG, RES)


if __name__ == "__main__":
    import json
    print(json.dumps(stats(), indent=2))
