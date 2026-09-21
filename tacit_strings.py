"""
tacit_strings.py — 介面文案（英文預設 / 繁體中文）
=====================================================
與 tacit_i18n 分開維護：核心字彙（維度、統計量、匯出工作表名）在 tacit_i18n，
介面文案量大且只有主程式用得到，放這裡比較好找也好翻譯。

匯入時自動註冊到 tacit_i18n。新增語言只要為每個鍵補上該語言碼即可。
"""

import tacit_i18n as I

APP_STRINGS = {
    # ------------------------------------------------------ 選擇性載入既有分析
    "app.model_need_key": {
        "en": "Enter an API key above to load the current model list.",
        "zh": "在上方填入金鑰後，會自動載入目前可用的模型清單。"},
    "app.model_from_api": {
        "en": "{n} models available on your key.",
        "zh": "你的金鑰目前可用 {n} 個模型。"},
    "app.model_list_failed": {
        "en": "Could not read the model list, showing a built-in fallback. "
              "If a model 404s, it has probably been retired — check "
              "ai.google.dev/gemini-api/docs/models. ({e})",
        "zh": "無法讀取模型清單，改用內建的備用清單。"
              "若某個模型出現 404，多半是已經下架，"
              "可到 ai.google.dev/gemini-api/docs/models 查目前可用的版本。({e})"},
    "app.pick_records": {"en": "Interviews to load", "zh": "要載入的訪談稿"},
    "app.pick_hint": {
        "en": "Load only the interviews you want in scope. Every analysis in "
              "the other tabs is computed from what is loaded here, so a "
              "smaller selection means a narrower, more readable comparison.",
        "zh": "只載入這一次要納入分析的訪談稿。其他頁籤的所有分析都以此處"
              "載入的內容為範圍，選得少一點，比較起來會清楚許多。"},
    "app.load_selected": {"en": "Load selected", "zh": "載入所選"},
    "app.select_all": {"en": "All", "zh": "全選"},
    "app.select_none": {"en": "None", "zh": "全不選"},
    "app.refresh_list": {"en": "Rescan folder", "zh": "重新掃描"},
    "app.no_saved": {"en": "No saved analyses found yet. Run an analysis first.",
                     "zh": "尚未找到任何已儲存的分析，請先執行一次分析。"},
    "app.legacy_mark": {"en": "old format", "zh": "舊格式"},
    "app.dup_mark": {"en": "superseded", "zh": "已有新版"},

    # -----------------------------------------------------------------
    # 框架不符。維度識別碼只在它自己的框架裡有意義，所以拿 B 框架開 A 框架
    # 編出來的檔案，整份編碼會在載入當下被清空——而畫面上跟「還沒編碼」
    # 長得一模一樣。使用者接著隨手一存，磁碟上的原始資料就被空的版本覆蓋。
    # 所以這裡是硬擋，不是警告。
    # -----------------------------------------------------------------
    "app.fw_mark": {"en": "framework: {fw}", "zh": "框架：{fw}"},
    "app.fw_mismatch_list": {
        "en": "{n} saved analyses were coded under a different framework "
              "({others}). The active framework is **{active}**. They are "
              "listed but not selected: their dimension identifiers do not "
              "exist in the active framework, so loading them would leave "
              "every segment with no codes. Switch to the framework they were "
              "coded under to open them.",
        "zh": "有 {n} 份存檔是用別的框架編出來的（{others}），目前作用中的框架是"
              "**{active}**。它們仍然列在下面，但預設不勾選：它們的維度識別碼在"
              "作用中的框架裡並不存在，載入之後每一個段落都會變成沒有編碼。"
              "要開啟它們，請先切回它們當初使用的框架。"},
    "app.fw_blocked": {
        "en": "Not loaded. {n} of the selected analyses were coded under "
              "**{theirs}**, but the active framework is **{active}**. Loading "
              "them would discard every code they contain, and saving "
              "afterwards would overwrite the original file with the emptied "
              "version. Switch the framework in the sidebar first, or "
              "deselect them.",
        "zh": "未載入。所選的分析裡有 {n} 份是用 **{theirs}** 編出來的，但目前"
              "作用中的框架是 **{active}**。載入會丟掉它們全部的編碼，之後一旦"
              "存檔，磁碟上的原始檔就會被清空的版本覆蓋。請先在側欄切換框架，"
              "或把它們取消勾選。"},
    "app.codes_dropped": {
        "en": "{n} codes could not be migrated and were not loaded. The table "
              "below lists each one with the reason. This is reported rather "
              "than silently applied, because a code that disappears without "
              "notice changes the analysis without changing anything visible.",
        "zh": "有 {n} 個編碼無法遷移，沒有被載入。下表逐筆列出原因。"
              "這件事一定要講出來而不是默默處理掉：無聲消失的編碼會改變分析"
              "結果，而畫面上看不出任何差別。"},
    "app.loaded_n": {"en": "Loaded {n} of {total}", "zh": "已載入 {n} / {total}"},
    "app.reference_forked": {
        "en": "{orig} is a shipped reference coding and is kept read-only. Your "
              "edits were saved to a new file, {new}, which now appears in the "
              "list above. The reference file is unchanged.",
        "zh": "{orig} 是隨軟體附的參考編碼，保持唯讀。你的修改已另存為 {new}，"
              "現在會出現在上方清單裡；參考檔本身沒有被改動。"},
    "app.nothing_selected": {"en": "Select at least one interview.",
                             "zh": "請至少選擇一份訪談稿。"},

    # ---------------------------------------------------------------- 側欄
    "side.framework": {"en": "Coding framework", "zh": "編碼框架"},
    "side.framework_help": {
        "en": "The theoretical framework used for coding. Dimensions, polarity "
              "model and definitions all come from the selected framework file.",
        "zh": "編碼所依據的理論框架。維度、極性模型與定義全部來自所選的框架檔。"},
    "side.framework_builtin": {"en": "(built-in)", "zh": "（內建）"},
    "side.ui_lang": {"en": "Interface language", "zh": "介面語言"},
    "side.analysis_lang": {"en": "Analysis output language", "zh": "分析輸出語言"},
    "side.analysis_lang_help": {
        "en": "The language the model writes titles and rationales in. Quotations "
              "are always kept verbatim in the transcript's own language. "
              "This is independent of the interface language.",
        "zh": "模型撰寫標題與理由所用的語言。引文一律以逐字稿原本的語言逐字保留。"
              "此設定與介面語言互相獨立。"},
    "side.no_polarity_note": {
        "en": "This framework has no polarity model, so polarity analyses are "
              "hidden.",
        "zh": "此框架未啟用極性模型，極性相關分析已隱藏。"},
    "side.plotly_missing": {
        "en": "plotly is not installed; charts fall back to tables.",
        "zh": "未安裝 plotly，圖表將以表格呈現。"},
    "side.scipy_missing": {
        "en": "scipy is not installed; the chi-square test is disabled.",
        "zh": "未安裝 scipy，卡方檢定停用。"},

    # ---------------------------------------------------------------- 執行分析
    "run.upload": {"en": "Upload transcripts (.docx)", "zh": "上傳逐字稿 (.docx)"},
    "run.delay": {"en": "Seconds between files", "zh": "每份稿件間隔秒數"},
    "run.delay_help": {"en": "Avoids hitting the API rate limit.",
                       "zh": "避免觸發 API 配額限制。"},
    "run.start": {"en": "Start analysis", "zh": "開始分析"},
    "run.need_key": {"en": "Please enter your Gemini API key in the sidebar.",
                     "zh": "請先在左側輸入 Gemini API Key。"},
    "run.need_file": {"en": "Please upload at least one transcript.",
                      "zh": "請先上傳至少一份逐字稿。"},
    "run.coding": {"en": "Coding… (attempt {a}/3)", "zh": "AI 編碼中…（第 {a}/3 次嘗試）"},
    "run.coding_chunk": {"en": "Coding excerpt {i}/{n}…",
                         "zh": "編碼中：第 {i}/{n} 段…"},
    # --- 分段編碼 ---
    "run.chunk_title": {"en": "Segmented coding (long transcripts)",
                        "zh": "分段編碼（長逐字稿）"},
    "run.chunk_help": {
        "en": "A whole two-hour transcript sent in one request makes the model "
              "return a handful of highlights instead of a full coding. "
              "Splitting it into overlapping excerpts and coding each one "
              "recovers the passages a single pass misses. Costs one request "
              "per excerpt.",
        "zh": "整份兩小時的逐字稿一次送出去，模型會回傳幾段代表性摘錄，"
              "而不是一份完整的編碼。切成重疊的段落逐段編碼，才找得回單次"
              "分析漏掉的內容。代價是每一段各一次請求。"},
    "run.chunk_on": {"en": "Split long transcripts into excerpts",
                     "zh": "長逐字稿切段分析"},
    "run.chunk_on_help": {
        "en": "Transcripts shorter than the excerpt size are always sent whole.",
        "zh": "短於單段長度的逐字稿一律整份送出，不切。"},
    "run.chunk_window": {"en": "Excerpt size (characters)", "zh": "單段長度（字元）"},
    "run.chunk_window_help": {
        "en": "Smaller excerpts give higher recall but cost more requests. "
              "3000 is roughly one to two speaking turns.",
        "zh": "切得越小，找回的段落越多，但請求次數也越多。3000 字元大約是"
              "一到兩個發言輪次。"},
    "run.chunk_overlap": {"en": "Overlap (characters)", "zh": "重疊長度（字元）"},
    "run.chunk_overlap_help": {
        "en": "A passage straddling a split point is only half-visible on each "
              "side; overlap lets it appear whole in at least one excerpt.",
        "zh": "橫跨切點的段落在兩邊都只看得到一半，重疊讓它至少完整出現在"
              "一段裡。"},
    "run.chunk_est": {"en": "≈ {calls} model requests for {files} file(s).",
                      "zh": "{files} 份檔案，約需 {calls} 次模型請求。"},
    "run.synth_prompt": {
        "en": "Below are per-excerpt notes on ONE interview. Write 150-200 "
              "words of analytic commentary on the account as a whole: which "
              "dimensions it most strongly exhibits, which are weak or absent. "
              "Output the commentary only, no preamble.\n\n{text}",
        "zh": "Below are per-excerpt notes on ONE interview. Write 150-200 "
              "words of analytic commentary on the account as a whole: which "
              "dimensions it most strongly exhibits, which are weak or absent. "
              "Output the commentary only, no preamble.\n\n{text}"},
    # --- 產出量檢查 ---
    "run.yield_low": {
        "en": "Low coding yield: {n} segments from {chars} characters "
              "({d} per 10,000). Manual coding of comparable interview "
              "material runs around {ref} per 10,000. This usually means the "
              "model returned highlights rather than a full coding — try "
              "segmented coding, a smaller excerpt size, or a stronger model.",
        "zh": "編碼產出偏低：{chars} 字元只產出 {n} 段（每萬字元 {d} 段）。"
              "同類訪談材料的人工編碼密度約為每萬字元 {ref} 段。這通常代表"
              "模型回傳的是幾段摘錄而不是完整編碼——請改用分段編碼、把單段"
              "長度調小，或換一顆能力較強的模型。"},
    "run.yield_template": {
        "en": "Every dimension has exactly one segment. That is the signature "
              "of a model copying the output example rather than analysing the "
              "text. Treat this result as unusable.",
        "zh": "每個維度剛好各一段。這是模型照抄輸出範例、而不是真的在分析"
              "文本的特徵。這份結果不宜採用。"},
    "run.yield_missing": {"en": "No segments at all for: {dims}",
                          "zh": "完全沒有編碼到的維度：{dims}"},
    # --- 編碼模式 ---
    "tab.codebook": {"en": "Codebook", "zh": "碼簿"},
    "run.mode": {"en": "Coding mode", "zh": "編碼模式"},
    "side.mode_help": {
        "en": "Where the codes come from. Framework-driven: the codes are the "
              "dimensions of the framework chosen below, fixed before coding "
              "starts. Open coding: no framework is applied; codes are created "
              "from the material and accumulate into a codebook, which you can "
              "later fix as a framework of its own.",
        "zh": "碼從哪裡來。框架驅動：碼就是下面選的框架的維度，編碼前就固定了。"
              "開放編碼：不套用任何框架，碼從資料裡長出來、累積成碼簿，"
              "之後可以把碼簿定案成一個自己的框架。"},
    "side.open_active": {
        "en": "**No framework is applied.** Codes come from the data. "
              "Codebook so far: {n} code(s). Fix the codebook in the Codebook "
              "tab to turn it into a framework.",
        "zh": "**沒有套用任何框架。** 碼從資料裡長出來。"
              "目前碼簿有 {n} 個碼。到「碼簿」頁籤把它定案，就會變成一個框架。"},
    "app.header_open": {
        "en": "Open coding · no framework applied · codes are developed from the data",
        "zh": "開放編碼 · 沒有套用框架 · 碼從資料裡長出來"},
    "run.mode_framework": {"en": "Framework-driven", "zh": "框架驅動"},
    "run.mode_open": {"en": "Open coding", "zh": "開放編碼"},
    "run.mode_framework_help": {
        "en": "Codes come from the active framework, fixed before coding "
              "starts. This is codebook thematic analysis; add double coding "
              "on the Reliability tab for the coding-reliability variant.",
        "zh": "編碼取自作用中的框架，在開始編碼之前就固定了。這是碼簿型主題"
              "分析；再到信度頁籤做雙盲雙編，就是編碼信度型的作法。"},
    "run.mode_open_help": {
        "en": "No framework. Codes are created from the data as coding "
              "proceeds and accumulate into a codebook across transcripts. "
              "When the codebook settles, turn it into a framework on the "
              "Codebook tab — cross-tabs, co-occurrence and reliability all "
              "become available at that point, not before.",
        "zh": "不套用框架。編碼在讀的過程中從資料裡長出來，並跨逐字稿累積成"
              "一份碼簿。碼簿穩定之後，到「碼簿」頁籤把它轉成框架——交叉表、"
              "共現與信度是在那一刻才成立的，在那之前不成立。"},
    "run.open_ignores_framework": {
        "en": "The framework selected in the sidebar ({fw}) is not used in open "
              "coding. There is no “no framework” option because the analysis "
              "tabs always read one; once you fix your codebook as a framework, "
              "it takes that slot.",
        "zh": "側欄選的框架（{fw}）在開放編碼裡不會被用到。沒有「無框架」這個"
              "選項，是因為分析頁籤一律讀作用中的框架；等你把碼簿定案成框架，"
              "它就會取代這個位置。"},
    "side.framework_unused_open": {
        "en": "Not used while coding mode is Open coding.",
        "zh": "編碼模式為開放編碼時不會用到。"},
    "run.open_start": {"en": "Start open coding", "zh": "開始開放編碼"},
    "run.open_codebook_state": {"en": "Codebook: {n} codes so far",
                                "zh": "碼簿：目前 {n} 個碼"},
    "run.open_codebook_empty": {
        "en": "No codebook yet. The first transcript will start one; every "
              "transcript after that adds to the same codebook, which is what "
              "makes codes recur instead of being one-off labels.",
        "zh": "還沒有碼簿。第一份逐字稿會開始建立，之後每一份都加進同一份"
              "碼簿——碼會重複出現而不是變成一次性的標籤，靠的就是這件事。"},
    "run.open_codebook_continues": {
        "en": "Coding continues into codebook {cb}, which already holds {n} "
              "codes. The order of transcripts matters: the ones run first "
              "shape the codebook the later ones are coded against.",
        "zh": "接續碼簿 {cb} 繼續編碼，目前已有 {n} 個碼。逐字稿的順序是有"
              "意義的：先跑的那幾份形塑了後面幾份用來對照的碼簿。"},
    "run.open_codebook_reset": {"en": "Start a new codebook",
                                "zh": "重新開一份碼簿"},
    "run.open_done": {
        "en": "{seg} segments · {new} new codes, {reused} reuses · "
              "codebook now {total}",
        "zh": "{seg} 段 · 新建 {new} 個碼、沿用 {reused} 次 · 碼簿共 {total} 個"},
    "run.open_chunk_errors": {
        "en": "{n} excerpt(s) failed and were skipped — this transcript is "
              "coded incompletely.",
        "zh": "有 {n} 個段落失敗被略過——這份逐字稿的編碼並不完整。"},
    "run.open_batch_done": {
        "en": "Done: {ok} transcript(s), {fail} failed. Codebook holds {codes} "
              "codes.",
        "zh": "完成：{ok} 份逐字稿，{fail} 份失敗。碼簿共 {codes} 個碼。"},
    "run.open_next_step": {
        "en": "Next: review the codebook, merge near-duplicates, then turn it "
              "into a framework. Nothing downstream works until you do.",
        "zh": "接下來：到「碼簿」頁籤複核、合併近義碼，再把它轉成框架。"
              "在那之前，後面的分析頁籤都沒有東西可看。"},
    # --- 碼簿頁籤 ---
    "cb.empty": {"en": "No codebook yet.", "zh": "還沒有碼簿。"},
    "cb.empty_hint": {
        "en": "A codebook is produced by open coding. Switch the coding mode "
              "on the first tab and run a transcript.",
        "zh": "碼簿由開放編碼產生。到第一個頁籤把編碼模式切換過去，跑一份"
              "逐字稿就會有了。"},
    "cb.n_codes": {"en": "Codes", "zh": "碼數"},
    "cb.n_applications": {"en": "Applications", "zh": "套用次數"},
    "cb.n_singletons": {"en": "Used once", "zh": "只出現一次"},
    "cb.n_undefined": {"en": "Undefined", "zh": "沒有定義"},
    "cb.provenance": {
        "en": "Codebook {cb}, started {created}, built from {docs} transcript(s).",
        "zh": "碼簿 {cb}，建立於 {created}，由 {docs} 份逐字稿累積而成。"},
    "cb.saturation": {"en": "New codes over time", "zh": "新碼的出現速度"},
    "cb.saturation_help": {
        "en": "How many codes were newly created in each excerpt, and how many "
              "were reuses. A flattening curve is often described as "
              "saturation — treat it as description, not as a decision. "
              "Whether more data would still yield something new depends on "
              "your research question and your sampling, not on this curve.",
        "zh": "每一段新建了幾個碼、沿用了幾次。曲線趨平常被稱為飽和——請把它"
              "當描述，不要當判定。再收資料會不會還有新東西，取決於你的研究"
              "問題與抽樣，不是這條曲線能決定的。"},
    "cb.chunk_n": {"en": "Excerpt", "zh": "第幾段"},
    "cb.created": {"en": "New", "zh": "新建"},
    "cb.reused": {"en": "Reused", "zh": "沿用"},
    "cb.cumulative": {"en": "Cumulative", "zh": "累計"},
    "cb.codes": {"en": "The codebook", "zh": "碼簿內容"},
    "cb.col_id": {"en": "id", "zh": "識別碼"},
    "cb.col_label": {"en": "Code", "zh": "碼"},
    "cb.col_count": {"en": "Count", "zh": "次數"},
    "cb.col_definition": {"en": "Definition", "zh": "定義"},
    "cb.col_example": {"en": "First example", "zh": "代表引文"},
    "cb.col_merged": {"en": "Merged from", "zh": "併自"},
    "cb.save_edits": {"en": "Save label and definition edits",
                      "zh": "儲存碼與定義的修改"},
    "cb.saved": {"en": "{n} field(s) updated.", "zh": "已更新 {n} 個欄位。"},
    "cb.similar": {"en": "Possible duplicates", "zh": "可能重複的碼"},
    "cb.similar_help": {
        "en": "Codes whose labels look alike. Near-duplicates are a normal "
              "product of open coding, not a defect — and which ones should "
              "actually merge is an analytic judgement, not something string "
              "similarity can settle. Nothing is merged unless you say so.",
        "zh": "標籤看起來相近的碼。近義碼是開放編碼的正常產物，不是缺陷——"
              "而哪些真的該合併是分析判斷，不是字串相似度能決定的。"
              "你不按，什麼都不會被合併。"},
    "cb.similar_threshold": {"en": "Similarity threshold", "zh": "相似度門檻"},
    "cb.similar_count": {
        "en": "{n} candidate pair(s) at this threshold.",
        "zh": "在這個門檻下有 {n} 對候選。"},
    "cb.similar_truncated": {
        "en": "Showing the {shown} most similar of {total} candidate pairs at "
              "this threshold. Raise the threshold to shorten the list; the "
              "count above is the real one.",
        "zh": "在這個門檻下有 {total} 對候選，這裡只列相似度最高的 {shown} 對。"
              "把門檻拉高可以縮短清單；上面那個數字才是實際筆數。"},
    "cb.similar_none": {"en": "No pairs above this threshold.",
                        "zh": "沒有超過這個門檻的配對。"},
    "cb.merge_into": {"en": "Merge into “{label}” (keeps this label)",
                      "zh": "併進「{label}」（保留這個標籤）"},
    "cb.researcher": {"en": "researcher", "zh": "研究者"},
    "cb.rare": {"en": "Codes used only once", "zh": "只出現一次的碼"},
    "cb.rare_warning": {
        "en": "{n} code(s) occur once. In coding-reliability terms they are "
              "noise; in grounded theory a single occurrence may be the "
              "negative case that matters most. Nothing is removed "
              "automatically — decide, then act.",
        "zh": "有 {n} 個碼只出現過一次。從編碼信度的角度它們是雜訊；"
              "在紮根理論裡，只出現一次的可能正是最關鍵的負面案例。"
              "工具不會自動移除——先判斷，再動作。"},
    "cb.rare_drop": {"en": "Remove codes used only once",
                     "zh": "移除只出現一次的碼"},
    "cb.rare_dropped": {"en": "{n} code(s) removed.", "zh": "已移除 {n} 個碼。"},
    "cb.to_framework": {"en": "Fix the codebook as a framework",
                        "zh": "把碼簿定案成框架"},
    "cb.to_framework_help": {
        "en": "This is the moment the codebook stops moving. Each code becomes "
              "a dimension, its examples become the indicators a later coding "
              "pass will see, and every existing record is converted so that "
              "cross-tabs, co-occurrence, reliability and theme building all "
              "work on it. The framework is saved with provenance recording "
              "that it came from your corpus, not from published literature.",
        "zh": "碼簿在這一刻停止變動。每個碼變成一個維度，它的代表引文變成"
              "之後重新編碼時模型看得到的指標，所有既有紀錄一併轉換，"
              "交叉表、共現、信度與主題歸納從此都能用。框架存檔時會記下"
              "它來自你的語料、不是來自已發表的文獻。"},
    "cb.fw_id": {"en": "Framework id (lowercase, no spaces)",
                 "zh": "框架識別碼（小寫、不含空白）"},
    "cb.fw_name": {"en": "Framework name", "zh": "框架名稱"},
    "cb.fw_name_default": {"en": "Codebook induced from this corpus",
                           "zh": "由本語料歸納的碼簿"},
    "cb.fw_min_count": {"en": "Keep codes used at least this many times",
                        "zh": "至少出現幾次的碼才保留"},
    "cb.fw_min_count_help": {
        "en": "Codes below this are left out of the framework. Leave it at 1 "
              "to keep everything.",
        "zh": "低於這個次數的碼不會進入框架。設 1 就是全部保留。"},
    "cb.fw_build": {"en": "Build framework and convert records",
                    "zh": "建立框架並轉換紀錄"},
    "cb.fw_built": {
        "en": "Framework built with {n} dimensions (saved as {path}) and "
              "{recs} record(s) converted. It is now the active framework.",
        "zh": "已建立 {n} 個維度的框架（存為 {path}），並轉換了 {recs} 筆紀錄。"
              "它現在是作用中的框架。"},
    "cb.fw_built_next": {
        "en": "The analysis tabs now work on these records. You can also "
              "re-code the same transcripts against this framework and compare "
              "the two passes on the Reliability tab.",
        "zh": "分析頁籤現在可以讀這些紀錄了。你也可以拿這個框架把同一批逐字稿"
              "重新編一次，再到信度頁籤比較兩次編碼。"},
    # --- 以缺席為證據 ---
    "run.absence_dropped": {
        "en": "{n} code(s) discarded: the rationale gave the ABSENCE of a "
              "stance as evidence for it (\"does not show…\", \"no evidence "
              "of…\"). Silence is not evidence. A high count means this model "
              "invents negative codes from silence — consider a stronger model "
              "or tighter exclusion criteria in the framework.",
        "zh": "已丟棄 {n} 個編碼：理由是以「缺席」當成證據"
              "（「未表現出…」「does not show…」）。沉默不是證據。"
              "這個數字大代表這顆模型會憑「沒有出現 X」生出 −X 的碼，"
              "該考慮換模型，或把框架的排除條件寫得更緊。"},
    "run.absence_detail": {"en": "Which codes were discarded",
                           "zh": "被丟棄的編碼明細"},
    # --- 退化標題與併碼來源 ---
    "data.degenerate_titles": {
        "en": "{n} segment title(s) are just the dimension name (e.g. "
              "\"Reflexivity - N\"). Titles are meant to be sub-theme labels "
              "for downstream theme building; filled in this way the column is "
              "useless and theme analysis will only rediscover the framework "
              "itself. Re-run, or relabel these in the coding-review tab.",
        "zh": "有 {n} 個段落標題只是維度名（例如「Reflexivity - N」）。"
              "標題的用途是給下游主題聚斂用的次主題標籤；填成維度名這一欄"
              "就作廢了，主題分析只會把框架本身再跑出來一次。請重跑，"
              "或到編碼複核頁籤改寫這些標題。"},
    "data.merge_provenance": {
        "en": "{n} of {m} multi-coded segments got their extra code from "
              "merging across excerpts, not from a single model judgement. "
              "Co-occurrence built on those is partly an artefact of segmented "
              "coding — the cross-analysis tab can exclude them.",
        "zh": "{m} 個多重編碼段落裡，有 {n} 個的第二個碼來自跨窗合併，"
              "而不是模型在單一次判斷裡同時給的。建立在這些段落上的共現"
              "有一部分是分段編碼的產物——交互分析頁籤可以把它們排除。"},
    "cross.exclude_merged": {"en": "Exclude codes merged across excerpts",
                             "zh": "排除跨窗合併帶進來的編碼"},
    "cross.exclude_merged_help": {
        "en": "Keeps only co-occurrence the model asserted within one judgement. "
              "Compare the two: a large gap means the co-occurrence structure is "
              "mostly an artefact of splitting the transcript.",
        "zh": "只保留模型在單一次判斷裡就主張的共現。兩者對照著看："
              "差距大就代表共現結構主要是切段造成的產物。"},
    "cross.merge_note": {
        "en": "{n} of {m} multi-coded segments come from cross-excerpt merging.",
        "zh": "{m} 個多重編碼段落中，{n} 個來自跨窗合併。"},
    # --- 框架排除條件 ---
    "fw.exclusions": {"en": "Does not include", "zh": "排除條件（不算這個維度）"},
    "fw.no_exclusions": {
        "en": "None set. Without them the model decides the boundary of this "
              "construct on its own, and that boundary is written down nowhere.",
        "zh": "尚未設定。沒有排除條件，這個構念的邊界就是模型自己決定的，"
              "而那個邊界不會出現在任何文件裡。"},
    "fw.exclusions_missing": {
        "en": "No dimension in this framework declares exclusion criteria. "
              "Indicators are positive examples, and positive examples cannot "
              "fix a boundary — the model will fill the gap itself. Coding is "
              "then grounded in the model's improvisation rather than in the "
              "cited literature, which is exactly what this framework module "
              "exists to prevent.",
        "zh": "這個框架沒有任何維度寫了排除條件。指標是正面例子，"
              "而正面例子界定不出邊界——空著的地方模型會自己補。"
              "那樣一來編碼依附的是模型的臨場發揮，不是所引的文獻，"
              "而這正是框架模組存在的理由要防止的事。"},
    "run.empty_doc": {"en": "The document is empty. Please check the .docx file.",
                      "zh": "逐字稿內容為空，請確認 .docx 檔案。"},
    "run.no_json": {"en": "No JSON object found in the model response.",
                    "zh": "回應中找不到 JSON 結構。"},
    "run.done": {"en": "Done: {n} segments, {m} multi-coded",
                 "zh": "完成：{n} 段編碼，其中 {m} 段多重編碼"},
    "run.quota": {"en": "API quota reached. Please try again later or upgrade.",
                  "zh": "API 配額已達上限，請稍後再試或升級付費方案。"},
    "run.retry": {"en": "Malformed output, retrying…", "zh": "格式異常，自動重試中…"},
    "run.failed": {"en": "Failed after 3 attempts: {name}",
                   "zh": "三次嘗試均失敗：{name}"},
    "run.raw_output": {"en": "Show raw model output (for debugging)",
                       "zh": "查看 AI 原始輸出（除錯用）"},

    # -------------------------------------------------- 續跑（配額中斷後）
    "run.will_skip": {
        "en": "{n} of these files have already been analysed and will be "
              "skipped; {m} will be analysed.",
        "zh": "其中 {n} 份已經分析過，將自動略過；本次會分析 {m} 份。"},
    "run.skip_list": {"en": "Files that will be skipped ({n})",
                      "zh": "將略過的檔案（{n} 份）"},
    "run.redo": {"en": "Re-analyse files that were already done",
                 "zh": "重新分析已完成的檔案"},
    "run.redo_help": {
        "en": "Off by default. Analysing a transcript again costs API quota "
              "and produces a second record for the same interview. Turn this "
              "on only when you have deliberately changed the framework, the "
              "model or the prompt and want a fresh coding.",
        "zh": "預設關閉。重跑一份逐字稿會再花一次 API 配額，而且會為同一場訪談"
              "產生第二筆紀錄。只有在你刻意換了框架、模型或提示詞、"
              "想要一份全新的編碼時才需要開啟。"},
    # -----------------------------------------------------------------
    # 批次前的單筆試跑。
    #
    # 這一步的定位是「編碼員訓練」而不是「預覽」：研究者在這裡看的不是
    # 排版，是模型怎麼切段、怎麼挑引文、怎麼寫理由——也就是這個框架與
    # 這個模型合不合用。措辭要把這件事講出來，否則使用者會直接跳過。
    # -----------------------------------------------------------------
    "run.dry_title": {"en": "Try the coding on one passage first",
                      "zh": "先用一段文字試跑編碼"},
    "run.dry_help": {
        "en": "Paste a short passage from one of your transcripts and see how "
              "the current framework and model actually code it — how it "
              "splits segments, which quotes it selects, what rationale it "
              "writes. This is the equivalent of coder training: align your "
              "understanding on a small piece before committing a whole batch. "
              "Nothing here is saved to your analyses.",
        "zh": "貼上你其中一份逐字稿裡的一小段，看看目前的框架與模型實際上"
              "怎麼編碼——怎麼切段、挑哪一句引文、寫出什麼理由。"
              "這一步相當於編碼員訓練：先在少量材料上對齊理解，再送出整批。"
              "這裡的任何結果都不會寫進你的分析紀錄。"},
    "run.dry_input": {"en": "A passage to try", "zh": "要試跑的一段文字"},
    "run.dry_placeholder": {
        "en": "Paste two or three turns of dialogue, enough to contain one "
              "codeable idea.",
        "zh": "貼上兩三輪對話，足以包含一個可編碼的想法即可。"},
    "run.dry_go": {"en": "Try it", "zh": "試跑"},
    "run.dry_running": {"en": "Coding the passage…", "zh": "正在編碼這段文字…"},
    "run.dry_need_text": {"en": "Paste a passage first.", "zh": "請先貼上一段文字。"},
    "run.dry_n": {"en": "{n} segment(s) coded from this passage",
                  "zh": "從這段文字編出 {n} 個段落"},
    "run.dry_nocode": {"en": "no code assigned", "zh": "未指派編碼"},
    "run.dry_raw": {"en": "Raw model output", "zh": "模型原始輸出"},
    "run.dry_not_saved": {
        "en": "Not saved — this is a dry run.",
        "zh": "不會存檔——這是試跑。"},
    # 空結果不是「這段話沒有內容」，是一個要研究者判斷的訊號：
    # 可能真的不涉及框架的任何面向，也可能提示詞或模型不合用。
    # 兩者的差別只有研究者能判斷，前提是他知道有這件事。
    "run.dry_empty": {
        "en": "The model returned no segments for this passage. That can mean "
              "the passage genuinely does not speak to any dimension of the "
              "active framework — or that the model is not following the "
              "coding instructions. Try a passage you are confident is "
              "codeable; if that also comes back empty, the model is the "
              "problem, not the data.",
        "zh": "模型沒有從這段文字編出任何段落。這可能代表這段話確實沒有觸及"
              "作用中框架的任何面向，也可能代表模型沒有照著編碼指示走。"
              "換一段你確定編得出來的文字再試一次；如果還是空的，"
              "問題就在模型而不在資料。"},

    "run.all_done": {
        "en": "All uploaded files have already been analysed. Nothing to do. "
              "Load them from the sidebar, or tick the re-analyse box above.",
        "zh": "上傳的檔案全部都分析過了，沒有需要執行的項目。"
              "請從左側載入既有結果，或勾選上方的「重新分析」。"},
    "run.stopped_summary": {
        "en": "Stopped: {ok} finished and saved, {left} not started. Nothing "
              "that was already finished has been lost.",
        "zh": "已停止：{ok} 份完成並已存檔，{left} 份尚未開始。"
              "已經完成的部分沒有任何損失。"},
    "run.resume_hint": {
        "en": "To continue: wait for the quota to reset or enter a different "
              "API key, then press Start again with the same files selected. "
              "The finished ones are skipped automatically, so you will not "
              "be charged for them twice.",
        "zh": "要繼續：等配額恢復，或改用另一把 API 金鑰，"
              "然後維持同樣的檔案選取、再按一次「開始分析」。"
              "已完成的會自動略過，不會重複計費。"},
    "run.batch_done": {"en": "Batch finished: {ok} succeeded, {fail} failed.",
                       "zh": "本批完成：成功 {ok} 份、失敗 {fail} 份。"},
    "run.workspace": {"en": "Workspace contents", "zh": "本次工作區內容"},
    "run.transcript_hint": {
        "en": "Paragraph or table layouts are both supported. In tables, columns "
              "named Speaker/Content are detected automatically. Speaker markers "
              "matter for the reliability module.",
        "zh": "段落式或表格式都支援。表格若含「講者／內容」欄位會自動辨識。"
              "講者標記對信度檢定模組很重要。"},

    # ---------------------------------------------------------------- 資料與屬性
    "data.descriptor_editor": {"en": "Respondent descriptors", "zh": "受訪者屬性編輯"},
    "data.descriptor_hint": {
        "en": "Filled in automatically from the transcript; anything not stated "
              "is left Unspecified. Edit below and save. Descriptors are the "
              "grouping variable for cross-analysis, so review them before "
              "running any crosstab.",
        "zh": "AI 已依逐字稿自動填入，未明確陳述者標為「未標註」。"
              "以下表格可直接修改，改完按儲存。屬性是交叉分析的分組依據，"
              "建議人工覆核後再進行交互分析。"},
    "data.save_descriptors": {"en": "Save descriptors", "zh": "儲存屬性"},
    # 改名。名稱是跨模組的連結鍵，所以改了要講清楚什麼跟著改、什麼沒有。
    "data.renamed": {
        "en": "Renamed {n} respondent(s): {pairs}. The records and their stored "
              "transcripts were updated. **Sampling frames and theme sets built "
              "before this rename still carry the old names** — rebuild them, "
              "or the reliability tab will show units it cannot match.",
        "zh": "已改名 {n} 位受訪者：{pairs}。紀錄與其保存的逐字稿都已更新。"
              "**在此之前建立的信度抽樣框與主題仍然是舊名字**——請重建，"
              "否則信度頁籤會出現對不回去的單元。"},
    "data.rename_clash": {
        "en": "Not renamed — the new name is already used by another record: "
              "{pairs}. Two records sharing a name are silently merged into one "
              "person in every crosstab, so this is refused rather than warned "
              "about. Choose a different name.",
        "zh": "未改名——新名稱已經有別的紀錄在用：{pairs}。"
              "兩筆紀錄同名的話，在每一張交叉表裡都會被靜靜地併成同一個人，"
              "所以這裡直接拒絕而不只是警告。請換一個名稱。"},
    # 模型不照語言約定。跟維度值寫成複合值是同一種病。
    "data.simplified_found": {
        "en": "The analysis language is Traditional Chinese, but {n} record(s) "
              "contain Simplified characters in text the model wrote: {chars}. "
              "Quotations are excluded from this check — those must stay "
              "verbatim. Models trained mainly on Simplified Chinese (the Qwen "
              "family in particular) often ignore the instruction. Nothing is "
              "converted automatically: Simplified-to-Traditional is not "
              "one-to-one, and rewriting the model's output would destroy the "
              "record of what it actually said. Re-run with a different model, "
              "or convert deliberately and note that you did.",
        "zh": "分析語言設定為繁體中文，但有 {n} 筆紀錄的**模型自撰文字**含簡體字："
              "{chars}。引文不列入檢查——引文本來就該逐字保留原文。"
              "以簡體語料為主訓練的模型（尤以 Qwen 系列明顯）經常忽略這個指示。"
              "工具不會自動轉換：簡轉繁不是一對一（发 → 發／髮），"
              "改寫模型的輸出等於毀掉「它到底寫了什麼」的紀錄。"
              "請換一個模型重跑，或自行轉換並在方法段落載明你做了轉換。"},
    "data.saved": {"en": "Descriptors updated and written back to file.",
                   "zh": "屬性已更新並寫回檔案。"},
    "data.ai_basis": {"en": "Basis (from AI)", "zh": "AI 判定依據"},
    "data.health": {"en": "Data health check", "zh": "資料健檢"},
    "data.per_case": {"en": "Case-by-case view", "zh": "逐案例檢視"},
    "data.select_case": {"en": "Select respondent", "zh": "選擇受訪者"},
    "data.multi_note": {"en": "{n} of these segments carry more than one code "
                              "(the source of co-occurrence).",
                        "zh": "其中 {n} 段為多重編碼（共現分析的來源）。"},

    # ---------------------------------------------------------------- 健檢欄位
    "health.segments": {"en": "Segments", "zh": "段落數"},
    "health.codes": {"en": "Codes", "zh": "編碼數"},
    "health.multi_segments": {"en": "Multi-coded segments", "zh": "多重編碼段落"},
    "health.multi_rate": {"en": "Multi-coded rate", "zh": "多重編碼比例"},
    "health.dims_covered": {"en": "Dimensions covered", "zh": "涵蓋維度數"},
    "health.desc_filled": {"en": "Descriptors filled", "zh": "屬性完整度"},

    # ---------------------------------------------------------------- 交互分析
    "cross.basis": {"en": "Basis: {r} respondents, {s} segments, {c} codes "
                          "(a multi-coded segment is counted once per code)",
                    "zh": "分析基底：{r} 位受訪者、{s} 個段落、{c} 筆編碼"
                          "（一段多碼會重複計入）"},
    "cross.tab1": {"en": "Dimension x descriptor", "zh": "維度 × 屬性"},
    "cross.tab2": {"en": "Code co-occurrence", "zh": "編碼共現"},
    "cross.tab3": {"en": "Cross-case matrix", "zh": "跨案例矩陣"},
    "cross.tab4": {"en": "Polarity balance", "zh": "極性平衡"},
    "cross.group_by": {"en": "Group by descriptor", "zh": "分組屬性"},
    "cross.unit": {"en": "Unit of analysis", "zh": "分析單位"},
    "cross.unit_help": {"en": "Code = dimension x polarity; Dimension = ignoring "
                              "polarity.",
                        "zh": "「編碼」＝維度×極性；「維度」＝不分極性。"},
    "cross.show": {"en": "Show", "zh": "顯示"},
    "cross.row_pct": {"en": "Row percentage", "zh": "列百分比"},
    "cross.raw_count": {"en": "Raw counts", "zh": "原始次數"},
    "cross.drop_unspecified": {"en": "Exclude Unspecified", "zh": "排除未標註"},
    "cross.no_data_after_filter": {
        "en": "Nothing left after excluding Unspecified. Uncheck it, or fill in "
              "the descriptors first.",
        "zh": "排除未標註後沒有資料，請取消勾選或先補齊屬性。"},
    "cross.pct_note": {
        "en": "Row percentages show the distribution within each group, removing "
              "the effect of group size, so groups can be compared. Raw counts "
              "are confounded by group size and transcript length.",
        "zh": "列百分比＝各屬性組別內部的編碼分布，已消除組別大小差異，"
              "組別之間才可直接比較。原始次數受該組人數與逐字稿長度影響。"},
    "cross.chi_title": {"en": "Chi-square test (interpret with care)",
                        "zh": "卡方檢定（謹慎解讀）"},
    "cross.chi_sparse": {
        "en": "{small} of {total} cells have an expected count below 5 (over the "
              "20% limit). The chi-square assumption is not met, so no p-value is "
              "reported; read the table descriptively instead.",
        "zh": "{small}/{total} 格期望次數 <5（超過 20% 上限），卡方前提不成立，"
              "因此不提供 p 值，請僅以描述性方式解讀交叉表。"},
    "cross.chi_ok": {"en": "Expected counts meet the assumption; p may be reported.",
                     "zh": "期望次數符合卡方前提，可報告 p 值。"},
    "cross.chi_nested": {
        "en": "p = {p}. Expected counts meet the assumption; independence does "
              "not \u2014 the {n} units in this table come from {k} respondents, so "
              "the same person is counted several times. Report this as a "
              "description of the pattern, or tick \u201cOne row per respondent\u201d "
              "for a table that meets both assumptions.",
        "zh": "p = {p}。期望次數符合前提；獨立性不符合——這張表的 {n} 個單位來自 "
              "{k} 位受訪者，同一個人被算了好幾次。請把它當作樣態的描述來報告，"
              "或勾選「每位受訪者只佔一列」取得兩個前提都符合的表。"},
    "cross.chi_case_note": {
        "en": "Each of the {k} respondents is counted once here, so the "
              "observations are independent. What limits this table is its "
              "size, not its design.",
        "zh": "這裡 {k} 位受訪者每人只算一次，觀察彼此獨立。限制這張表的是"
              "它的規模，不是它的設計。"},
    "cross.case_level": {"en": "One row per respondent",
                         "zh": "每位受訪者只佔一列"},
    "cross.case_level_help": {
        "en": "A chi-square test assumes independent observations, but coded "
              "units are nested within respondents: one person who made the "
              "same point seven times contributes seven observations. With "
              "this on, each respondent is counted once, under the category "
              "they were coded to most often (ties go to \u201cmixed\u201d), so the "
              "table total equals the number of respondents. Expect the test "
              "to be withheld more often \u2014 that is the honest result for a "
              "sample of this size.",
        "zh": "卡方檢定假設觀察彼此獨立，但編碼單元巢套在受訪者底下——"
              "同一個人講了七次同樣的話，就算成七個觀察。勾選後每位受訪者只算"
              "一次，歸到他最常被編到的那一類（平手歸「混合」），所以表的總數"
              "等於受訪者人數。檢定會更常被扣住——對這種規模的樣本，那才是"
              "誠實的結果。"},
    "cross.case_level_note": {
        "en": "Respondent level: N = {n} respondents, each under their most "
              "frequent category. Read the table for its pattern; whether a "
              "test can be reported is decided below, as always.",
        "zh": "受訪者層級：N = {n} 位受訪者，每人歸在他最常出現的類別。"
              "這張表看的是樣態；能不能報告檢定，照舊由下面的守衛決定。"},
    "cross.case_mixed": {"en": "Mixed", "zh": "混合"},
    "cross.chi_independence": {
        "en": "Note also that chi-square assumes independent observations, but "
              "one respondent contributes several codes. In qualitative samples, "
              "treat these statistics as pattern description, not inference.",
        "zh": "另請注意：卡方假設觀察值彼此獨立，但同一位受訪者貢獻多筆編碼會"
              "違反此假設。質性樣本下建議把統計量當作型態描述，而非顯著性推論。"},
    "cross.chi_too_small": {"en": "The table needs to be at least 2x2 to test.",
                            "zh": "交叉表需至少 2×2 才能檢定。"},
    "cross.chi_no_scipy": {"en": "scipy is not installed, so the chi-square test "
                                 "is unavailable (pip install scipy).",
                           "zh": "未安裝 scipy，無法執行卡方檢定（pip install scipy）。"},
    "cross.cooc_level": {"en": "Co-occurrence level", "zh": "共現層級"},
    "cross.level_segment": {"en": "Segment level (strict)", "zh": "段落層級（嚴格）"},
    "cross.level_case": {"en": "Respondent level (loose)", "zh": "受訪者層級（寬鬆）"},
    "cross.level_help": {
        "en": "Segment level = the same excerpt carries both codes. Respondent "
              "level = both codes appear somewhere in the same interview.",
        "zh": "段落層級＝同一段引文被標記兩碼；受訪者層級＝兩碼出現在同一人身上。"},
    "cross.matrix_value": {"en": "Matrix values", "zh": "矩陣數值"},
    "cross.diag_note": {"en": "The diagonal is each code's total number of segments.",
                        "zh": "對角線＝該編碼的總出現次數（段落數）。"},
    "cross.top_pairs": {"en": "Leading co-occurrence pairs", "zh": "主要共現配對"},
    "cross.no_cooc": {
        "en": "No co-occurrence found. If the data was migrated from an older "
              "version, only excerpts whose full text matched exactly were merged "
              "into multi-coded segments; re-code the transcript for complete "
              "co-occurrence data.",
        "zh": "目前沒有任何共現關係。若資料由舊版遷移而來，只有「完整原文完全相同」"
              "的引文才會被合併為多重編碼；要取得完整共現資料，需重新編碼逐字稿。"},
    "cross.jaccard_note": {
        "en": "Jaccard = co-occurrence divided by the union of the two codes, "
              "correcting for a code simply being frequent. Cross-dimension pairs "
              "are the theoretically interesting ones: two dimensions bound "
              "together in the same utterance.",
        "zh": "Jaccard = 共現次數 ÷ 兩碼聯集次數，可校正「某碼本來就很常出現」造成的"
              "假性強關聯。跨維度的配對最具理論意義，代表兩個維度在同一段陳述中"
              "結構性地綁在一起。"},
    "cross.multi_stat": {"en": "Multi-coded segments: {m} of {n}",
                         "zh": "多重編碼段落：{m} / {n}"},
    "cross.normalize_case": {"en": "Normalise per respondent (percentage)",
                             "zh": "以受訪者為單位標準化為百分比"},
    "cross.normalize_help": {
        "en": "Removes the effect of transcript length; without it, talkative "
              "respondents always look stronger.",
        "zh": "消除逐字稿長度差異；未標準化時話多的人看起來永遠訊號比較強。"},
    "cross.case_note": {
        "en": "Rows are respondents, columns are codes. Read across for a case "
              "profile, down for how a code is distributed. A near-empty column "
              "means that dimension lacks evidence in this sample, which is "
              "itself a finding worth reporting.",
        "zh": "列＝受訪者，欄＝編碼。橫向看是個案的編碼輪廓，縱向看是該編碼在樣本中的"
              "分布。整欄接近零代表該理論面向在本樣本中缺乏證據，這本身就是值得討論的"
              "發現。"},
    "cross.polarity_overall": {"en": "Overall polarity index", "zh": "整體極性指數"},
    "cross.polarity_by_dim": {"en": "Polarity index by dimension",
                              "zh": "維度別極性指數"},
    "cross.radar": {"en": "Radar comparison", "zh": "雷達圖比較"},
    "cross.radar_select": {"en": "Respondents to overlay", "zh": "選擇要疊圖比較的受訪者"},
    "cross.radar_centre_note": {
        "en": "The centre of this radar is −1, not 0, because the polarity "
              "index runs from −1 to +1. A shape that shrinks towards the "
              "centre on one axis means that dimension was framed "
              "**negatively** — not that it was rarely discussed. For how "
              "often it came up, read the total column in the table below.",
        "zh": "本圖圓心是 −1 而非 0，因為極性指數的值域是 −1 到 +1。"
              "某個軸向縮到接近圓心，代表該維度的陳述**偏負向**，"
              "不是「很少談到」。要看談得多不多，請對照下方表格的總數欄。"},
    "cross.polarity_note": {
        "en": "Polarity index = (P - N)/(P + N), normalised for coding volume and "
              "therefore comparable across cases. When a dimension has very few "
              "codes (<3) the index is highly unstable; check the total column.",
        "zh": "極性指數 =(P−N)/(P+N)。已對編碼總量標準化，可跨案例比較；"
              "但當某維度的編碼總數過少（如 <3），指數會非常不穩定，"
              "解讀時請對照「總數」欄。"},

    # ---------------------------------------------------------------- 匯出
    "export.title": {"en": "Download results", "zh": "下載分析結果"},
    "export.excel": {"en": "Excel (full cross-analysis)", "zh": "Excel（完整交互分析）"},
    "export.word": {"en": "Word report", "zh": "Word 報告"},
    "export.json": {"en": "Merged JSON", "zh": "合併 JSON"},
    "export.hint": {
        "en": "The Excel file contains the coded long table, descriptors, one "
              "sheet per cross-analysis, and a code reference. The long table is "
              "tidy data and can be loaded straight into SPSS, R or NVivo.",
        "zh": "Excel 含：編碼長表、受訪者屬性、四種交互分析各自的工作表、編碼對照表。"
              "長表可直接匯入 SPSS / R / NVivo 做進一步統計。"},
    "export.report_title": {"en": "Qualitative coding and cross-analysis report",
                            "zh": "質性編碼與交互分析報告"},
    "export.generated": {"en": "Generated", "zh": "產生時間"},
    "export.sample": {"en": "Sample", "zh": "樣本數"},
    "export.section_cross": {"en": "Part I — Cross-analysis summary",
                             "zh": "壹、交互分析摘要"},
    "export.section_cases": {"en": "Part II — Coding results by case",
                             "zh": "貳、逐案例編碼結果"},
    "export.no_codes": {"en": "(no coded data)", "zh": "（尚無編碼資料）"},
    "export.multi_mark": {"en": "multi-coded", "zh": "多重編碼"},
}

I.register(APP_STRINGS)

# ---------------------------------------------------------------- 編碼複核
REVIEW_STRINGS = {
    "rv.why": {"en": "Why this step exists", "zh": "為什麼需要這一頁"},
    "rv.why_body": {
        "en": "\"Interpretation should not be outsourced to a machine\" is an "
              "epistemological objection; no statistic answers it. Only a process "
              "does: the model performs a first pass, the researcher confirms, "
              "corrects or rejects every code, and adds segments the model missed. "
              "Every figure on this page is evidence for that claim.",
        "zh": "「質性詮釋不該外包給機器」是認識論上的反對，統計量回應不了，"
              "只能用流程回應：模型做初編碼，研究者確認、修正或刪除每一個編碼，"
              "並補入模型漏標的段落。本頁的每個數字都是這句話的證據。"},
    "rv.reviewer": {"en": "Reviewer name (recorded in the audit trail)",
                    "zh": "複核者姓名（寫入稽核軌跡）"},
    "rv.tab1": {"en": "Review segments", "zh": "逐段複核"},
    "rv.tab2": {"en": "Add segment", "zh": "人工新增"},
    "rv.tab3": {"en": "Verify quotations", "zh": "引文逐字驗證"},
    "rv.tab4": {"en": "Review report", "zh": "複核報表"},
    "rv.pending_only": {"en": "Pending only", "zh": "只顯示未審核"},
    "rv.filter_code": {"en": "Filter by code", "zh": "篩選編碼"},
    "rv.progress": {"en": "{who}: reviewed {done}/{total}",
                    "zh": "{who}　已複核 {done}/{total}"},
    "rv.nothing": {"en": "Nothing pending under the current filter.",
                   "zh": "目前篩選條件下沒有待複核的段落。"},
    "rv.ai_original": {"en": "AI original", "zh": "AI 原始"},
    "rv.quote_bad_full": {
        "en": "The full text cannot be matched back to the transcript — possible "
              "paraphrase or hallucinated quotation. Please check.",
        "zh": "完整原文對不回逐字稿——可能是模型改寫或幻覺引文，請務必檢查。"},
    "rv.quote_bad_brief": {"en": "The quote cannot be matched back to the transcript.",
                           "zh": "精簡引文對不回逐字稿。"},
    "rv.quote_ok": {"en": "Verbatim check passed", "zh": "引文逐字比對通過"},
    "rv.ai_rationale": {"en": "Rationale given by the model", "zh": "AI 給的理由"},
    "rv.confirm": {"en": "Confirm", "zh": "確認"},
    "rv.delete": {"en": "Delete", "zh": "刪除"},
    "rv.confirm_help": {
        "en": "Confirm applies any text or code edits made above. With no changes "
              "it is recorded as confirmed-unchanged.",
        "zh": "「確認」會一併套用你在上面改過的文字與編碼；沒有改動時記為確認未改。"},
    "rv.deleted_box": {"en": "Deleted segments ({n}) — kept and restorable",
                       "zh": "已刪除的段落（{n}）—— 保留可還原"},
    "rv.restore": {"en": "Restore", "zh": "還原"},
    "rv.add_hint": {
        "en": "This is the only operation that can improve recall. Pair it with "
              "the possible-under-coding list in the reliability tab.",
        "zh": "這是唯一能改善 recall 的操作，建議搭配信度頁籤的「疑似漏標」清單使用。"},
    "rv.add_to": {"en": "Add to respondent", "zh": "加到哪位受訪者"},
    "rv.add_text": {"en": "Full text (copy verbatim from the transcript)",
                    "zh": "完整原文（請自逐字稿逐字複製）"},
    "rv.add_reason": {"en": "Reason (recorded in the audit trail)",
                      "zh": "補入理由（寫入稽核軌跡）"},
    "rv.add_go": {"en": "Add segment", "zh": "新增段落"},
    "rv.add_need": {"en": "Please provide the text and at least one code.",
                    "zh": "請填入原文並至少選一個編碼。"},
    "rv.in_transcript": {"en": "This text appears verbatim in the transcript.",
                         "zh": "這段文字逐字存在於該受訪者的逐字稿。"},
    "rv.not_in_transcript": {"en": "This text was not found in the transcript.",
                             "zh": "這段文字在逐字稿中找不到，請確認是否逐字複製。"},
    "rv.no_transcripts": {
        "en": "No transcripts loaded yet. Upload them under Reliability > Build "
              "sampling frame; they will be reused here.",
        "zh": "尚未載入原始逐字稿。請到「信度檢定 → 建立抽樣框」上傳，載入後這裡會自動沿用。"},
    "rv.quote_rate": {"en": "Verbatim match rate", "zh": "逐字相符率"},
    "rv.needs_check": {"en": "Needs manual check", "zh": "需人工檢查"},
    "rv.all_verbatim": {"en": "All quotations match the transcript verbatim.",
                        "zh": "全部引文皆可逐字對回逐字稿。"},
    "rv.stat_ai": {"en": "AI segments", "zh": "AI 產出段落"},
    "rv.stat_rate": {"en": "Review rate", "zh": "複核率"},
    "rv.stat_modified": {"en": "Modified", "zh": "修改率"},
    "rv.stat_deleted": {"en": "Deleted", "zh": "刪除率"},
    "rv.stat_added": {"en": "Human-added", "zh": "人工新增"},
    "rv.pending_warn": {
        "en": "{n} segments still pending. To claim that every code was verified, "
              "the review rate must reach 100%.",
        "zh": "還有 {n} 段未複核。論文若要宣稱「全部編碼皆經人工確認」，複核率必須達 100%。"},
    "rv.all_done": {"en": "All AI segments have been reviewed.",
                    "zh": "全部 AI 段落皆已複核。"},
    "rv.methods_sentence": {"en": "Ready to paste into the methods section",
                            "zh": "可直接貼進方法章節"},
    "rv.code_changes": {"en": "Changes by code", "zh": "逐碼變動"},
    "rv.removal_note": {
        "en": "A high removal rate means the prompt's criteria for that code are "
              "too loose — a methodological reflection worth reporting, and the "
              "basis for the next prompt revision.",
        "zh": "移除率高的碼代表提示詞對該碼的判準太寬鬆——這是可寫進論文的方法反思，"
              "也是下一輪改提示詞的依據。"},
    "rv.changed": {"en": "Changed segments (before / after)", "zh": "變動段落前後對照"},
    "rv.trail": {"en": "Audit trail", "zh": "稽核軌跡"},

    # ---------------------------------------------------------------- 主題
    "th.disclaimer": {"en": "Methodological positioning (read before writing up)",
                      "zh": "方法論定位（撰稿前必讀）"},
    "th.disclaimer_body": {
        "en": "This produces a Gioia-STYLE data structure, but the analytic "
              "strategy is abductive and theory-driven, not classic grounded "
              "theory: the aggregate dimensions are specified a priori by the "
              "chosen framework, whereas in Gioia they emerge last. Do not write "
              "\"we used the Gioia methodology\" — say \"we present a "
              "Gioia-style data structure\" and state the difference explicitly.",
        "zh": "本頁產出的是 **Gioia 式**資料結構，但分析策略為溯因、理論驅動，"
              "而非古典紮根理論：聚合維度由所選框架先驗給定，Gioia 則是最後才浮現。"
              "不要寫「本研究採用 Gioia 方法論」，要寫「採 Gioia 式資料結構呈現」"
              "並明確交代此差異。"},
    "th.tab1": {"en": "Induce themes", "zh": "執行歸納"},
    "th.tab2": {"en": "Themes & matrices", "zh": "主題表與矩陣"},
    "th.tab3": {"en": "Data structure", "zh": "資料結構圖"},
    "th.tab4": {"en": "Export", "zh": "匯出"},
    "th.chunk": {"en": "First-order concepts per batch", "zh": "每批一階概念數"},
    "th.min_size": {"en": "Minimum concepts per theme", "zh": "主題最少一階概念數"},
    "th.min_size_help": {"en": "A theme supported by a single segment does not "
                               "stand (a basic Gioia requirement).",
                         "zh": "只有單一段落支撐的不成立主題（Gioia 的基本要求）。"},
    "th.run": {"en": "Induce second-order themes", "zh": "執行主題歸納"},
    "th.nomodel": {"en": "Without a model: group the codes by similarity",
                   "zh": "不用模型：依相似度把碼分群"},
    "th.nomodel_body": {
        "en": "Second-order themes do not have to come from a model. This "
              "groups the codes by agglomerative clustering — the same kind of "
              "help CAQDAS packages have offered for years — and stops there. "
              "**Naming the groups is left to you**, because the name of a "
              "second-order theme is the interpretation itself. The grouping "
              "is deterministic and reproduces exactly; who named each group "
              "is recorded. Nothing is sent anywhere.",
        "zh": "二階主題不一定要來自模型。這裡用凝聚式階層分群把碼分組——"
              "跟 CAQDAS 套件提供多年的輔助是同一類東西——然後就停在那裡。"
              "**命名留給你**，因為二階主題的名字就是詮釋本身。分群是確定性的，"
              "重跑會得到一模一樣的結果；誰命名的會記下來。全程不送出任何資料。"},
    "th.nomodel_need": {
        "en": "At least two codes must appear in the records before they can "
              "be grouped.",
        "zh": "紀錄裡至少要有兩個碼出現過才分得了群。"},
    "th.nomodel_basis": {"en": "Group by", "zh": "分群依據"},
    "th.basis_cooc": {"en": "Co-occurrence", "zh": "共現"},
    "th.basis_labels": {"en": "Label and definition text", "zh": "標籤與定義的文字"},
    "th.nomodel_basis_help": {
        "en": "Co-occurrence groups codes that are applied to the same passage; "
              "it needs passages carrying more than one code, and says so when "
              "there are too few. Label text compares the wording of the codes "
              "themselves — the right choice for a large inductive codebook, "
              "where each passage usually carries a single code.",
        "zh": "共現看的是「同一段話被標上哪些碼」，因此需要有帶不只一個碼的段落，"
              "太少的時候會直接講。標籤文字比的是碼本身的用字——"
              "碼簿很大的歸納式編碼要用這個，因為那種編碼多半一段一個碼。"},
    "th.nomodel_k": {"en": "Groups", "zh": "分成幾群"},
    "th.nomodel_go": {"en": "Group the codes", "zh": "分群"},
    "th.nomodel_build": {"en": "Build themes from these groups",
                         "zh": "用這些群建立主題"},
    "th.nomodel_built": {"en": "{n} theme(s) built. The theme tabs now work on them.",
                         "zh": "建立了 {n} 個主題。主題頁籤現在用的是它們。"},
    "th.nomodel_unnamed": {
        "en": "{n} group(s) still have no name. An unnamed theme is visibly "
              "unfinished in the report, which is the point — but finish it.",
        "zh": "還有 {n} 群沒有名字。沒有名字的主題在報表上看得出來是未完成的，"
              "這是刻意的——但還是請把它補完。"},
    "th.cluster_distance": {"en": "merge distance", "zh": "合併距離"},
    "th.cluster_distance_note": {
        "en": "Merge distance runs from 0 to 1: near 0 the codes belong "
              "together on the evidence, near 1 the group is an arrangement "
              "rather than a finding. Report it.",
        "zh": "合併距離從 0 到 1：接近 0 代表這些碼確實靠在一起，接近 1 代表"
              "這一群是湊出來的版面而不是發現。報告時把它寫出來。"},
    "th.cluster_no_basis": {
        "en": "Every group here has a merge distance near 1: almost no passage "
              "carries more than one code, so co-occurrence has nothing to work "
              "with. Group by label text instead.",
        "zh": "每一群的合併距離都接近 1：幾乎沒有段落帶超過一個碼，共現沒有東西"
              "可以依據。請改用標籤文字分群。"},
    "th.name_groups": {"en": "Name the groups", "zh": "為每一群命名"},
    "th.name_groups_note": {
        "en": "A second-order theme is an analytic claim, not a category label. "
              "Leave a group unnamed and it stays visibly unfinished.",
        "zh": "二階主題是一句分析性的主張，不是分類標籤。留空的群會一直顯示為未完成。"},
    "th.too_few": {
        "en": "Only {n} first-order concepts. Theme induction needs density; "
              "below about 30 the themes are unstable.",
        "zh": "目前只有 {n} 個一階概念。主題歸納需要足夠的資料密度，"
              "低於 30 個時歸納出的主題會很不穩定。"},
    "th.load": {"en": "Load previous themes", "zh": "載入上次的主題"},
    "th.clear": {"en": "Clear themes", "zh": "清除目前主題"},
    "th.debug": {"en": "Induction log", "zh": "歸納過程紀錄"},
    "th.orphans": {"en": "These provisional themes were not folded into any final "
                         "theme; the model may have dropped them.",
                   "zh": "下列暫定主題在合併階段未被納入任何最終主題，可能是模型漏掉了。"},
    "th.coverage": {"en": "Concept coverage", "zh": "一階概念覆蓋率"},
    "th.unassigned_count": {"en": "Unassigned themes", "zh": "未歸屬主題"},
    "th.thin": {"en": "Thin themes", "zh": "薄弱主題"},
    "th.coverage_note": {
        "en": "Coverage need not reach 100%. Segments that fit no pattern should "
              "be left out; forcing them in is over-interpretation.",
        "zh": "覆蓋率不必追求 100%。歸納不出模式的段落本來就該落單，硬塞是過度詮釋。"},
    "th.thin_warn": {
        "en": "These themes rest on a single respondent and are not persuasive; "
              "consider demoting them to case observations: {ids}",
        "zh": "下列主題只由單一受訪者支撐，說服力不足，建議降級為個案觀察：{ids}"},
    "th.filter_dim": {"en": "Filter by aggregate dimension", "zh": "篩選聚合維度"},
    "th.unassigned_note": {"en": "Theoretical implication of the unassigned themes",
                           "zh": "未歸屬主題的理論意涵"},
    "th.support": {"en": "Theme x respondent support", "zh": "主題 × 受訪者支持度"},
    "th.support_note": {
        "en": "This answers whether a theme rests on one voice. The higher the "
              "support rate, the sounder the theme.",
        "zh": "這張表在回答「這個主題是不是只有一個人在講」。支持率越高，主題越站得住。"},
    "th.by_code": {"en": "Inductive theme x deductive code", "zh": "歸納主題 × 演繹編碼"},
    "th.by_code_note": {
        "en": "Themes spanning several codes are the interesting ones: the pattern "
              "cuts across the framework's own boundaries.",
        "zh": "橫跨多個編碼的主題最值得注意——代表它切過了框架的分類邊界。"},
    "th.outside": {"en": "Concepts not in any theme ({n})", "zh": "未納入任何主題的一階概念（{n}）"},
    "th.max_fo": {"en": "First-order concepts shown per theme",
                  "zh": "每個主題最多顯示幾個一階概念"},
    "th.show_speaker": {"en": "Label concepts with respondent",
                        "zh": "在一階概念後標註受訪者"},
    "th.svg_note": {
        "en": "Dashed frame = unassigned dimension. A badge on a theme box marks "
              "it as extending or challenging the framework. SVG is vector; open "
              "it in Illustrator, Inkscape or PowerPoint to adjust type sizes.",
        "zh": "虛線框＝未歸屬聚合維度。主題框右上角標記者代表與框架有張力。"
              "SVG 為向量格式，可用 Illustrator／Inkscape／PowerPoint 微調字級。"},
    "th.download_svg": {"en": "Download SVG (vector, editable)",
                        "zh": "下載 SVG（向量圖，可再編輯）"},
    "th.export_note": {
        "en": "The first-order mapping sheet is what readers want most: one row "
              "per supporting quotation, fully traceable.",
        "zh": "「一階概念對照」是讀者最想看的東西——每個主題底下由哪些逐字引文支撐，"
              "一列一條，完整可回溯。"},

    # ---------------------------------------------------------------- 詞庫
    "lx.stance": {
        "en": "The lexicon is not used as a classifier. Keyword matching as the "
              "primary coding mechanism is exactly the bag-of-words paradigm that "
              "fails on Chinese. It is used for three other things: inducing "
              "feature terms from your own corpus, auditing the model, and "
              "serving as a dictionary baseline for comparison.",
        "zh": "詞庫在這裡不是分類器。拿關鍵詞當主要編碼機制，正是中文上會失敗的 "
              "bag-of-words 典範。它只做三件事：從你自己的語料反向誘導特徵詞、"
              "反過來稽核模型、以及當作對照用的詞典基準。"},
    "lx.lang_mismatch": {
        "en": "This lexicon is for {lex} but the framework/corpus language differs. "
              "A lexicon is language-specific and cannot be reused across languages.",
        "zh": "此詞庫適用於 {lex}，與目前語料語言不同。詞庫是語言相關資源，不能跨語言沿用。"},
    "lx.not_found": {
        "en": "No lexicon file for this framework and language yet ({path}). "
              "Feature-term induction can still run; it will create one.",
        "zh": "尚無對應此框架與語言的詞庫檔（{path}）。特徵詞誘導仍可執行，並會建立新檔。"},
    "lx.tab1": {"en": "Discover terms", "zh": "新詞發現"},
    "lx.tab2": {"en": "Induce feature terms", "zh": "特徵詞誘導"},
    "lx.tab3": {"en": "Dictionary vs model", "zh": "詞典 vs 模型對照"},
    "lx.tab4": {"en": "Lexicon contents", "zh": "詞庫檢視／匯出"},
    "lx.discover_note": {
        "en": "Character n-gram cohesion (PMI) plus left/right boundary entropy. "
              "Both thresholds must pass. This discovers terms absent from any "
              "dictionary rather than merely matching an existing word list.",
        "zh": "字元 n-gram 的凝固度（PMI）＋左右鄰字熵，兩個門檻都要過。"
              "這能發現詞典裡沒有的新詞，而不只是比對既有詞表。"},
    "lx.min_freq": {"en": "Minimum frequency", "zh": "最低出現次數"},
    "lx.min_pmi": {"en": "Cohesion threshold", "zh": "凝固度門檻"},
    "lx.min_entropy": {"en": "Boundary entropy threshold", "zh": "鄰字熵門檻"},
    "lx.max_n": {"en": "Maximum term length", "zh": "最長詞長"},
    "lx.run_discover": {"en": "Run term discovery", "zh": "執行新詞發現"},
    "lx.no_terms": {
        "en": "No candidates passed the thresholds. Lower them, or accumulate more "
              "transcripts — this is common with a small corpus.",
        "zh": "沒有詞通過門檻。試著調低門檻，或先累積更多逐字稿——語料量少時這很常見。"},
    "lx.pick_force": {"en": "Select terms to protect from segmentation",
                      "zh": "挑選要加入「強制詞」的術語"},
    "lx.add_force": {"en": "Add to protected terms and save", "zh": "加入強制詞並存檔"},
    "lx.induce_note": {
        "en": "Log-odds ratio with an informative Dirichlet prior (Monroe et al., "
              "2008). Unlike raw frequency or TF-IDF it suppresses terms common to "
              "all codes and is not misled by terms appearing once or twice. "
              "This table IS your data-driven lexicon.",
        "zh": "以整體語料為 Dirichlet 先驗的對數勝算比（Monroe et al., 2008）。"
              "比起詞頻或 TF-IDF，它會壓抑各碼共有的通用詞，也不會被罕詞誤導。"
              "這份表就是你的資料驅動詞庫。"},
    "lx.min_count": {"en": "Minimum total occurrences", "zh": "詞最低總次數"},
    "lx.top_n": {"en": "Top N per code", "zh": "每碼取前 N 名"},
    "lx.merge_z": {"en": "Merge threshold (z >=)", "zh": "合併門檻 z ≥"},
    "lx.run_induce": {"en": "Run feature-term induction", "zh": "執行特徵詞誘導"},
    "lx.select_code": {"en": "Select code", "zh": "選擇編碼"},
    "lx.merge_preview": {"en": "Merge preview: {n} terms would be added",
                         "zh": "合併預覽：共 {n} 個詞會被加入概念詞層"},
    "lx.merge_warn": {
        "en": "Review before merging. Statistical significance is not theoretical "
              "relevance — some high-scoring terms are simply the respondents' "
              "verbal tics, or your own interview wording.",
        "zh": "加入前請人工確認。統計顯著不等於理論上有意義——有些高分詞只是受訪者的"
              "口頭禪，或你自己的提問用語。"},
    "lx.merge_go": {"en": "Merge into lexicon and save", "zh": "合併進詞庫並存檔"},
    "lx.compare_note": {
        "en": "Runs the dictionary coder as a baseline and compares it with the "
              "model, code by code. Codes with low kappa are usually where "
              "dictionary methods fail on Chinese — negation, irony, reported "
              "speech — and those specific cases are the evidence for your paper.",
        "zh": "以詞典編碼器為基準，逐碼與模型比較。κ 偏低的碼通常正是詞典法在中文上"
              "失效之處（否定、反諷、轉述），那些具體案例就是論文要用的證據。"},
    "lx.threshold": {"en": "Dictionary decision threshold", "zh": "詞典判碼門檻"},
    "lx.neg_window": {"en": "Negation look-back window (chars)",
                      "zh": "否定詞回看視窗（字）"},
    "lx.miss_threshold": {"en": "Under-coding threshold", "zh": "疑似漏標門檻"},
    "lx.run_compare": {"en": "Run comparison and audit", "zh": "執行對照與稽核"},
    "lx.overall_kappa": {"en": "Overall kappa", "zh": "整體 κ"},
    "lx.per_code": {"en": "Agreement by code", "zh": "逐碼一致度"},
    "lx.per_code_note": {
        "en": "Precision and recall are measured against the model's coding; this "
              "does NOT mean the model is correct.",
        "zh": "Precision／Recall 以模型編碼為參照，這**不代表模型就是正確答案**。"},
    "lx.over": {"en": "Possible over-coding ({n})", "zh": "疑似過度詮釋（{n}）"},
    "lx.over_note": {
        "en": "The model assigned this code but the segment carries no lexical or "
              "syntactic evidence for it. It may have read meaning the dictionary "
              "cannot see, or it may be hallucinating. Judge case by case.",
        "zh": "模型標了這個碼，但該段落沒有對應的詞彙或句式證據。可能是模型讀出了詞典"
              "看不到的語意，也可能是幻覺。請逐條人工判讀。"},
    "lx.under": {"en": "Possible under-coding ({n})", "zh": "疑似漏標（{n}）"},
    "lx.under_note": {
        "en": "Strong dictionary evidence but the model did not code it. This is "
              "the material for estimating recall.",
        "zh": "詞典證據很強，但模型沒有標。這批是估計召回率的材料。"},
    "lx.layer": {"en": "Layer", "zh": "檢視層級"},
    "lx.reload": {"en": "Reload lexicon", "zh": "重新載入詞庫"},
    "lx.pattern_note": {
        "en": "Pattern rules carry their own dimension and polarity. Framework "
              "dimensions and lexicon dimensions must match, otherwise the rule "
              "is ignored.",
        "zh": "句式模板自帶維度與極性。框架維度與詞庫維度必須相符，否則該規則會被忽略。"},

    # ---------------------------------------------------------------- 信度
    "ir.trap1": {"en": "Trap 1 — the sampling frame must include uncoded units",
                 "zh": "陷阱一：抽樣框必須含未標記單元"},
    "ir.trap1_body": {
        "en": "Sampling only from segments the model already coded means a human "
              "coder never sees the text it ignored, so false negatives are "
              "structurally unobservable and the resulting kappa speaks only to "
              "precision. The frame is therefore built over every utterance unit "
              "in the source transcripts.",
        "zh": "只從模型已標記的段落抽樣，人類就永遠看不到它忽略的文字，漏標在結構上"
              "不可觀測，算出來的 κ 只反映 precision。因此抽樣框建立在原始逐字稿的"
              "全部發言單元上。"},
    "ir.trap2": {"en": "Trap 2 — do not report Cohen's kappa alone",
                 "zh": "陷阱二：別只報 Cohen's κ"},
    "ir.trap2_body": {
        "en": "Most units carry no code, so the labels are sparse and highly "
              "skewed. Under such marginals kappa is deflated — the kappa "
              "paradox. PABAK and Gwet's AC1 are reported alongside, and the "
              "interface flags when a low kappa is caused by prevalence rather "
              "than disagreement.",
        "zh": "多數單元沒有任何編碼，屬高度不平衡的稀有事件標記。這種邊際分布下 κ 會被"
              "壓低——即 kappa paradox。因此並陳 PABAK 與 Gwet's AC1，"
              "並在 κ 偏低源於盛行率而非不一致時主動標示。"},
    "ir.tab1": {"en": "Build sampling frame", "zh": "建立抽樣框"},
    "ir.tab2": {"en": "Sample & blind", "zh": "抽樣與盲測"},
    "ir.tab3": {"en": "Collect codings", "zh": "回收編碼"},
    "ir.tab4": {"en": "Reliability report", "zh": "信度報表"},
    "ir.source": {"en": "Build the frame from", "zh": "抽樣框的來源"},
    "ir.source_records": {"en": "The analyses loaded in the sidebar",
                          "zh": "側欄載入的分析"},
    "ir.source_files": {"en": "Transcripts I upload here (no model needed)",
                        "zh": "在這裡上傳的逐字稿（不需要模型）"},
    "ir.source_help": {
        "en": "Agreement between two human coders needs no model at all. Choose "
              "the second option to upload transcripts directly: the tool splits "
              "them into units, draws a blinded sample, issues a coding sheet "
              "for each coder, and computes the coefficients. Nothing is sent "
              "anywhere, and no analysis has to exist first.",
        "zh": "兩位人類編碼者之間的一致性完全不需要模型。選第二項可以直接上傳"
              "逐字稿：軟體會切成發言單元、抽出盲樣、為每位編碼者產生編碼表，"
              "最後算出係數。全程不送出任何資料，也不需要先有分析結果。"},
    "ir.human_only_ready": {
        "en": "{n} transcript(s) ready. The frame will contain no model codes, "
              "so the report will cover coder-to-coder agreement only.",
        "zh": "已就緒 {n} 份逐字稿。抽樣框裡沒有模型編碼，因此報表只會有"
              "編碼者之間的一致性。"},
    "ir.upload_own": {"en": "Upload transcripts (.docx)", "zh": "上傳逐字稿（.docx）"},
    "ir.human_only_frame": {
        "en": "Human-coding frame: no model codes in it. Every unit is available "
              "for sampling.",
        "zh": "人工編碼抽樣框：裡面沒有模型編碼，全部單元都可以被抽到。"},
    "ir.human_only_sample": {
        "en": "Stratification is off: with no model codes there are no strata to "
              "balance, so the sample is drawn at random from the whole frame.",
        "zh": "分層已關閉：沒有模型編碼就沒有層可以平衡，因此直接從整個抽樣框"
              "隨機抽取。"},
    "ir.to_records": {"en": "Turn these codings into an analysis",
                      "zh": "把這些編碼變成可分析的紀錄"},
    "ir.to_records_note": {
        "en": "Agreement is not the end of the work. Sending one coder's "
              "completed sheet into the workspace as records makes every "
              "analysis tab available — crosstabs, co-occurrence, the "
              "cross-case matrix, lexicon discovery, theme grouping and the "
              "exports — none of which calls a model.",
        "zh": "算完信度不是工作的終點。把一位編碼者填好的表送進工作區變成紀錄之後，"
              "交叉分析、共現、跨個案矩陣、詞彙探勘、主題分群與匯出就全部可用，"
              "而這些都不會呼叫模型。"},
    "ir.to_records_need": {
        "en": "No completed codings yet. Import a sheet above, or code here.",
        "zh": "還沒有填好的編碼。請在上面匯入編碼表，或直接在這裡編碼。"},
    "ir.to_records_who": {"en": "Whose codings", "zh": "用誰的編碼"},
    "ir.to_records_go": {"en": "Add to workspace", "zh": "加入工作區"},
    "ir.to_records_replace": {"en": "Replace", "zh": "取代現有紀錄"},
    "ir.to_records_replace_help": {
        "en": "Off: added alongside what is already loaded, skipping "
              "respondents that already have a record. On: the workspace is "
              "cleared first. Nothing on disk is touched either way — save "
              "from the sidebar if you want to keep the result.",
        "zh": "不勾：加在已載入的紀錄旁邊，已經有紀錄的受訪者會略過。"
              "勾選：先清空工作區。兩種都不會動到磁碟上的檔案——要留下來請從"
              "側邊欄儲存。"},
    "ir.to_records_done": {
        "en": "{n} record(s), {m} coded units, from {who}. Every analysis tab "
              "now works on them.",
        "zh": "{n} 筆紀錄、{m} 個已編碼單元，來自 {who}。現在每個分析頁籤都能用它們了。"},
    "ir.to_records_skipped": {
        "en": "{n} respondent(s) skipped: a record for them was already loaded.",
        "zh": "略過 {n} 位受訪者：工作區裡已經有他們的紀錄。"},
    "ir.to_records_empty": {
        "en": "That coder marked no units, so there is nothing to analyse.",
        "zh": "這位編碼者沒有標記任何單元，沒有東西可以分析。"},
    "ir.upload": {"en": "Upload original transcripts (.docx)",
                  "zh": "上傳原始逐字稿 (.docx)"},
    "ir.upload_note": {
        "en": "The original files are needed to obtain the passages the model did "
              "not code. Nothing is uploaded anywhere; parsing happens locally.",
        "zh": "需要原始檔才能取得模型沒標記的段落。檔案不會上傳到任何地方，只在本機解析。"},
    "ir.map_file": {"en": "Map files to respondents", "zh": "檔案對應受訪者"},
    "ir.unit_min": {"en": "Minimum unit length", "zh": "單元最短字數"},
    "ir.unit_max": {"en": "Maximum unit length", "zh": "單元最長字數"},
    "ir.build": {"en": "Build sampling frame", "zh": "建立抽樣框"},
    "ir.total_units": {"en": "Total units", "zh": "單元總數"},
    "ir.coded_units": {"en": "Coded by model", "zh": "模型已標記"},
    "ir.uncoded_units": {"en": "Uncoded", "zh": "未標記"},
    "ir.no_uncoded": {
        "en": "No uncoded units, so recall cannot be measured. Check that you "
              "uploaded the complete transcript.",
        "zh": "沒有未標記單元，這樣量不到 recall。請確認上傳的是完整逐字稿。"},
    "ir.unmatched": {
        "en": "Some model quotations cannot be matched back to the transcript. "
              "This may mean the quotation was rewritten (a hallucinated quote), "
              "or the uploaded file is a different version. This is itself a "
              "finding.",
        "zh": "部分模型引文對不回逐字稿。可能是引文被改寫（幻覺引文），"
              "或上傳的檔案版本不同。這本身就是一個發現。"},
    "ir.n_sample": {"en": "Sample size", "zh": "抽樣數"},
    "ir.seed": {"en": "Random seed", "zh": "亂數種子"},
    "ir.seed_help": {"en": "Record this; it belongs in the methods section and "
                           "makes the sample reproducible.",
                     "zh": "請記錄下來，論文方法章節要寫，也讓抽樣可重現。"},
    "ir.min_per_code": {"en": "Minimum per code", "zh": "每碼至少抽"},
    "ir.unmarked_share": {"en": "Share drawn from uncoded units",
                          "zh": "未標記層佔比"},
    "ir.coders": {"en": "Coder names (comma separated)", "zh": "編碼者名單（逗號分隔）"},
    "ir.create": {"en": "Draw sample and create blind session",
                  "zh": "抽樣並建立盲測階段"},
    "ir.need_two": {"en": "At least two coders are required.", "zh": "至少需要兩位編碼者。"},
    "ir.load_session": {"en": "Load previous session", "zh": "載入上次的盲測階段"},
    "ir.strata": {"en": "Stratification", "zh": "分層結果"},
    "ir.sheets": {"en": "Download a coding sheet for each coder",
                  "zh": "下載編碼表（給每位編碼者各一份）"},
    "ir.sheet_note": {
        "en": "The sheet deliberately omits the model's codes and the stratum, so "
              "the coding is blind. Mark a code with 1 (v, x and a tick also "
              "work); leave blank for no. Offline by design — a collaborator "
              "should not have to install anything.",
        "zh": "編碼表刻意不含模型編碼與分層資訊，確保雙盲。該碼成立就填 1"
              "（v、✓、x 也認得），不成立留空。刻意設計成離線填寫——"
              "合作者不該為了編碼去安裝任何東西。"},
    "ir.received": {"en": "{done}/{total} received", "zh": "已回收 {done}/{total}"},
    "ir.upload_sheet": {"en": "Upload the completed sheet for {who}",
                        "zh": "上傳 {who} 填好的編碼表"},
    "ir.import": {"en": "Import {who}", "zh": "匯入 {who}"},
    "ir.imported": {"en": "Imported {n} rows, {m} of them coded",
                    "zh": "匯入 {n} 列，其中 {m} 列有標記"},
    "ir.code_here": {"en": "Or code directly in the interface",
                     "zh": "或直接在介面上編碼"},
    "ir.as_coder": {"en": "Code as", "zh": "以哪位編碼者身分編碼"},
    "ir.page": {"en": "Page (10 per page)", "zh": "第幾頁（每頁 10 筆）"},
    "ir.save_page": {"en": "Save this page", "zh": "儲存這一頁"},
    "ir.no_codings": {"en": "No human codings yet.", "zh": "尚無人工編碼。"},
    "ir.coder_a": {"en": "Coder A", "zh": "編碼者 A"},
    "ir.coder_b": {"en": "Coder B", "zh": "編碼者 B"},
    "ir.pick_two": {"en": "Please choose two different coders.",
                    "zh": "請選兩位不同的編碼者。"},
    "ir.no_common": {"en": "These coders share no completed units.",
                     "zh": "兩位編碼者沒有共同完成的單元。"},
    "ir.common_units": {"en": "{n} units completed by both", "zh": "共同完成 {n} 個單元"},
    "ir.exact": {"en": "Units with identical code sets", "zh": "整組編碼完全相同的比例"},
    "ir.paradox": {
        "en": "Prevalence is high (most units are 'none' for both coders): a "
              "textbook kappa paradox. PABAK = {pabak} and AC1 = {ac1} are "
              "markedly higher. Report all three and explain that the low kappa "
              "reflects sparse labelling, not coder disagreement.",
        "zh": "盛行率偏高（多數單元雙方都判定為「無」），屬典型的 kappa paradox："
              "PABAK = {pabak}、AC1 = {ac1} 明顯較高。報告時應三個係數並陳，"
              "並說明 κ 偏低來自標記稀疏而非編碼者不一致。"},
    "ir.consistent": {"en": "PABAK = {pabak}, AC1 = {ac1}; all three agree in "
                            "direction.",
                      "zh": "PABAK = {pabak}、AC1 = {ac1}，三者方向一致。"},
    "ir.sparse_code_note": {
        "en": "Where a code was rarely applied by both coders, kappa is almost "
              "bound to look poor; rely on AC1 and raw agreement, and note the "
              "small n in the write-up.",
        "zh": "某碼「雙方皆標」次數很少時，κ 幾乎必然難看，此時應以 AC1 與一致率為主，"
              "並在論文中說明該碼樣本過少。"},
    "ir.confusion": {"en": "Dimension confusion matrix", "zh": "維度混淆矩陣"},
    "ir.polarity_agree": {"en": "Polarity agreement (units both assigned to the "
                                "same dimension)",
                          "zh": "極性一致度（雙方都判定屬該維度的單元）"},
    "ir.polarity_note": {
        "en": "Polarity disagreement is more serious than dimension disagreement: "
              "the two coders read opposite evaluative directions from the same "
              "sentence. That is where the codebook needs a sharper definition.",
        "zh": "極性分歧比維度分歧嚴重——代表雙方從同一句話讀出了相反的評價方向，"
              "這是編碼手冊需要補充定義的地方。"},
    "ir.disagreements": {"en": "Disagreements (agenda for the calibration meeting)",
                         "zh": "分歧清單（校準會議用）"},
    "ir.ai_pr": {"en": "Model precision / recall", "zh": "模型的 Precision / Recall"},
    "ir.ai_pr_ref": {"en": "Reference coding", "zh": "以誰的編碼為參照"},
    "ir.ai_pr_note": {
        "en": "Because the frame includes uncoded units, this recall is "
              "meaningful. The FN column is the number of segments the model "
              "missed — the figure readers ask for.",
        "zh": "因為抽樣框含未標記單元，這裡的 Recall 才是有效的。"
              "FN 欄就是模型漏標的數量——這正是讀者要的那個數字。"},
    "lx.framework_mismatch": {
        "en": "This lexicon was written for the framework '{lex_fw}', but the "
              "active framework is '{cur}'. Its terms are organised by "
              "dimension, so none of them apply here — every count on this "
              "page will be zero. This is a mismatch, not a malfunction.",
        "zh": "這份詞庫是為框架「{lex_fw}」撰寫的，但目前作用中的框架是"
              "「{cur}」。詞庫的詞條是按維度分層的，因此一條都對不上——"
              "本頁所有數字都會是 0。這是設定不符，不是程式故障。"},
    "lx.framework_mismatch_how": {
        "en": "Either switch back to the matching framework in the sidebar, or "
              "build a new lexicon for the current one: run Feature induction "
              "on your coded data and merge the results. The dictionary "
              "baseline and audit numbers below are meaningless until then.",
        "zh": "兩種解法：在左側切回相符的框架，或為目前的框架建一份新詞庫——"
              "用已編碼的資料跑一次「特徵詞誘導」再合併結果。"
              "在那之前，下方的詞典基準與稽核數字都沒有意義。"},
    "lx.backend_fallback": {
        "en": "No Chinese word segmenter is installed, so a built-in "
              "statistical fallback is being used. It has no linguistic "
              "knowledge of Chinese, so some entries below will be wrong "
              "word boundaries rather than real words. Curate the list before "
              "reporting anything from it.",
        "zh": "未安裝中文斷詞器，目前使用內建的統計後備演算法。"
              "它沒有中文的語言知識，因此下方會有一部分是切錯的詞邊界、"
              "而非真正的詞。要引用之前請先人工篩選。"},
    "lx.backend_how": {"en": "How to install a proper segmenter",
                       "zh": "如何安裝正式的斷詞器"},
    "lx.backend_install": {
        "en": "This module works without a segmenter, but the term lists are "
              "noticeably cleaner with one. CKIP is built by Academia Sinica "
              "specifically for Traditional Chinese.\n\n"
              "```\npip install ckip-transformers\n```\n\n"
              "It downloads a BERT model on first use (about 400 MB) and is "
              "slower, but the word boundaries are correct. Restart the app "
              "after installing; it is detected automatically.\n\n"
              "Note: the semantic coding on the Run tab does **not** depend on "
              "segmentation at all, so this only affects this tab.",
        "zh": "沒有斷詞器也能運作，但裝了之後詞表會乾淨很多。"
              "CKIP 是中央研究院專為繁體中文開發的斷詞器。\n\n"
              "```\npip install ckip-transformers\n```\n\n"
              "首次使用會下載 BERT 模型（約 400 MB），速度較慢，"
              "但詞邊界是正確的。安裝後重新啟動程式即可，會自動偵測。\n\n"
              "注意：「執行分析」頁籤的語意編碼**完全不經過斷詞**，"
              "因此這件事只影響本頁籤。"},
    "lx.backend_ok": {"en": "Segmenter in use: {name}", "zh": "使用中的斷詞器：{name}"},
    "ir.download_report": {"en": "Download reliability report", "zh": "下載信度檢定報表"},
    "ir.transcripts_ready": {
        "en": "Transcripts for all {n} respondents are already stored with "
              "their analyses. Nothing to upload.",
        "zh": "{n} 位受訪者的逐字稿都已隨分析結果一併保存，不需要重新上傳。"},
    "ir.transcripts_missing": {
        "en": "{have} transcripts are already stored, but {n} are missing. "
              "Records saved by older versions of this tool did not keep the "
              "transcript, so those need to be supplied once.",
        "zh": "已有 {have} 份逐字稿，另有 {n} 份缺漏。"
              "舊版本存下的紀錄沒有保存逐字稿原文，這幾份需要補上傳一次。"},
    "ir.attach": {"en": "Attach these transcripts", "zh": "補上這幾份逐字稿"},
    "ir.built_partial": {
        "en": "The frame was built from the transcripts available. {n} "
              "respondents were left out because their transcript is missing.",
        "zh": "抽樣框已依現有逐字稿建立。有 {n} 位受訪者因缺少逐字稿而未納入。"},
}

I.register(REVIEW_STRINGS)


# =====================================================================
# 框架建構（OpenAlex 檢索 → 草擬 → 人工核可）
# =====================================================================
FRAMEWORK_STRINGS = {
    "fw.tab1": {"en": "Active framework", "zh": "現用框架"},
    "fw.tab2": {"en": "1. Retrieve literature", "zh": "1. 檢索文獻"},
    "fw.tab3": {"en": "2. Draft & approve", "zh": "2. 草擬與核可"},
    "fw.tab4": {"en": "Import / export", "zh": "匯入／匯出"},

    "fw.principle": {
        "en": "A coding framework is the validity foundation of the whole study, "
              "so it is never taken from the model's memory. Literature is the "
              "source of knowledge; the model only summarises and drafts; you "
              "decide. Every dimension must cite works that were actually "
              "retrieved, and every dimension must be approved by a named person "
              "before it enters the framework.",
        "zh": "編碼框架是整份研究的效度根基，因此絕不取自模型的記憶。"
              "文獻是知識來源，模型只做摘要與草擬，決定權在研究者。"
              "每個維度都必須引用實際檢索到的文獻，"
              "且必須經具名研究者核可才會進入框架。"},

    # --- 現用框架 ---
    "fw.overview": {"en": "Framework overview", "zh": "框架概觀"},
    "fw.n_dimensions": {"en": "Dimensions", "zh": "維度數"},
    "fw.n_codes": {"en": "Codes", "zh": "編碼數"},
    "fw.polarity_model": {"en": "Polarity model", "zh": "極性模型"},
    "fw.polarity_on": {"en": "Two-pole", "zh": "雙極"},
    "fw.polarity_off": {"en": "None", "zh": "無"},
    "fw.origin": {"en": "Origin", "zh": "來源"},
    "fw.origin_builtin": {"en": "Built in", "zh": "內建"},
    "fw.origin_manual": {"en": "Hand written", "zh": "人工撰寫"},
    "fw.origin_draft": {"en": "OpenAlex draft (not yet approved)",
                        "zh": "OpenAlex 草稿（尚未核可）"},
    "fw.origin_approved": {"en": "OpenAlex, researcher approved",
                           "zh": "OpenAlex，已經研究者核可"},
    # 從資料歸納出來的框架必須跟從文獻讀出來的框架分得開——三個月後沒有人
    # 能從維度名稱看出差別，稽核軌跡要自己說得出來。
    "fw.origin_induced": {"en": "Induced from your corpus by open coding",
                          "zh": "由你的語料經開放編碼歸納而來"},
    "fw.definitions": {"en": "Dimension definitions", "zh": "維度定義"},
    "fw.indicators_for": {"en": "Indicators", "zh": "指標"},
    "fw.grounding": {"en": "Grounded in", "zh": "定義依據"},
    "fw.bibliography": {"en": "Works cited by this framework",
                        "zh": "本框架引用的文獻"},
    "fw.no_bibliography": {
        "en": "This framework carries no literature records. Frameworks written "
              "by hand can still be used, but readers may ask where the "
              "dimensions came from.",
        "zh": "此框架沒有文獻紀錄。人工撰寫的框架仍可使用，"
              "但讀者可能會追問維度的來源。"},
    "fw.provenance": {"en": "Provenance record", "zh": "出處紀錄"},
    "fw.methods_para": {"en": "Ready-made methods paragraph",
                        "zh": "可直接引用的方法段落"},
    "fw.methods_hint": {
        "en": "Every number below comes from the recorded build process, not "
              "from an estimate. Paste it into the methods section and adjust "
              "the wording to your house style.",
        "zh": "以下每個數字都取自實際的建構紀錄，並非估計值。"
              "可貼入方法章節，再依你的行文習慣調整措辭。"},

    # --- 檢索 ---
    "fw.theory": {"en": "Theoretical construct", "zh": "理論構念"},
    "fw.theory_ph": {"en": "e.g. responsible innovation",
                     "zh": "例如：responsible innovation"},
    "fw.theory_help": {
        "en": "Search in the language the literature is published in. For most "
              "constructs that means English, even if you will code Chinese "
              "transcripts.",
        "zh": "請用該理論文獻出版的語言檢索。多數構念是英文，"
              "即使你要編碼的是中文逐字稿也一樣。"},
    "fw.api_key": {"en": "OpenAlex API key", "zh": "OpenAlex API 金鑰"},
    "fw.api_key_help": {
        "en": "Free from openalex.org/settings/api. Required since 13 Feb 2026. "
              "Without a key you get 100 credits per day (about 10 searches), "
              "which is enough to try this out but not to work with.",
        "zh": "於 openalex.org/settings/api 免費申請。自 2026-02-13 起為必要。"
              "未設金鑰每日僅 100 credits（約 10 次檢索），足以試用但不足以實際工作。"},
    "fw.key_in_sidebar": {
        "en": "The OpenAlex key is entered in the sidebar, under the Gemini key.",
        "zh": "OpenAlex 金鑰請在左側欄輸入，就在 Gemini 金鑰下方。"},
    "fw.key_from_env": {
        "en": "Filled in from the OPENALEX_API_KEY environment variable.",
        "zh": "已自 OPENALEX_API_KEY 環境變數帶入。"},
    "fw.key_persist_hint": {
        "en": "To avoid retyping this each time, set it as the "
              "OPENALEX_API_KEY environment variable.",
        "zh": "若不想每次重打，可將它設為 OPENALEX_API_KEY 環境變數。"},
    "fw.find_topics": {"en": "Find matching topics", "zh": "尋找對應主題"},
    "fw.topics_hint": {
        "en": "Theory names are ambiguous. Narrowing to a topic keeps unrelated "
              "fields out of the retrieved set. Optional but recommended.",
        "zh": "理論名稱常有歧義，先限定主題可避免混入不相干領域的文獻。"
              "非必要，但建議先做。"},
    "fw.topic_none": {"en": "(no topic filter)", "zh": "（不限定主題）"},
    "fw.n_seminal": {"en": "Seminal works (by citation count)",
                     "zh": "奠基文獻（依被引次數）"},
    "fw.n_recent": {"en": "Recent works", "zh": "近年文獻"},
    "fw.recent_years": {"en": "Recent means the last N years", "zh": "近年的年數界定"},
    "fw.require_abstract": {"en": "Only keep works with an abstract",
                            "zh": "只保留有摘要的文獻"},
    "fw.require_abstract_help": {
        "en": "Works without an abstract cannot inform the draft, but they can "
              "still be cited. Keep them unless the retrieved set is noisy.",
        "zh": "沒有摘要的文獻無法作為草擬依據，但仍可列為引用。"
              "除非檢索結果太雜，否則建議保留。"},
    "fw.retrieve": {"en": "Retrieve literature", "zh": "開始檢索"},
    "fw.need_theory": {"en": "Enter the name of the theoretical construct first.",
                       "zh": "請先輸入理論構念的名稱。"},
    "fw.retrieving": {"en": "Searching OpenAlex…", "zh": "正在檢索 OpenAlex…"},
    "fw.retrieved": {"en": "Retrieved {n} works ({a} with an abstract)",
                     "zh": "已檢索到 {n} 篇文獻（其中 {a} 篇有摘要）"},
    "fw.relevance_ok": {
        "en": "{pct}% of the retrieved works mention the query in their title "
              "or abstract.",
        "zh": "檢索到的文獻中有 {pct}% 在標題或摘要提到查詢詞。"},
    "fw.relevance_mid": {
        "en": "Only {pct}% of the retrieved works mention the query in their "
              "title or abstract. Skim the list before drafting; consider "
              "narrowing the query or filtering by topic.",
        "zh": "檢索到的文獻只有 {pct}% 在標題或摘要提到查詢詞。"
              "草擬之前請先掃一遍清單，或考慮收窄查詢、加上主題限定。"},
    "fw.relevance_bad": {
        "en": "Only {pct}% of the retrieved works mention the query in their "
              "title or abstract. This retrieval is not usable — do not draft "
              "from it. Narrow the query, or pick a topic above and retry.",
        "zh": "檢索到的文獻只有 {pct}% 在標題或摘要提到查詢詞，"
              "這批結果不可用，請不要據以草擬。"
              "請收窄查詢，或在上方選定主題後重新檢索。"},
    "fw.query_widened": {
        "en": "The exact phrase matched only {n} works, so the query was "
              "widened to require all terms rather than the exact phrase. "
              "This is recorded in the retrieval log.",
        "zh": "完整片語只找到 {n} 篇，因此自動放寬為「所有詞都要出現」"
              "而非完整片語。此調整已記入檢索紀錄。"},
    "fw.retrieval_log": {"en": "Retrieval record (for the methods section)",
                         "zh": "檢索紀錄（供方法章節使用）"},
    "fw.retrieved_works": {"en": "Retrieved works", "zh": "檢索到的文獻"},
    "fw.no_results": {
        "en": "Nothing was retrieved. Try a broader query, remove the topic "
              "filter, or check the spelling of the construct.",
        "zh": "沒有檢索到任何文獻。請試著放寬查詢、取消主題限定，"
              "或確認構念名稱的拼寫。"},
    "fw.quota_hit": {"en": "OpenAlex quota problem", "zh": "OpenAlex 額度問題"},
    "fw.cache_note": {
        "en": "Responses are cached on this computer. The cache key does not "
              "contain your API key, so the cache folder can be shared with the "
              "project: another researcher can then reproduce this retrieval "
              "with no key and no network.",
        "zh": "檢索結果會快取在本機。快取鍵不含你的金鑰，"
              "因此快取資料夾可隨專案一起流通：其他研究者不需金鑰、不需連網，"
              "即可重現這次檢索。"},

    # --- 草擬 ---
    "fw.draft_from": {"en": "Draft dimensions from {n} retrieved works",
                      "zh": "依 {n} 篇檢索到的文獻草擬維度"},
    "fw.polarity_choice": {"en": "Polarity model", "zh": "極性模型"},
    "fw.polarity_auto": {"en": "Let the model decide from the literature",
                         "zh": "由模型依文獻判斷"},
    "fw.polarity_yes": {"en": "Require a two-pole model", "zh": "指定使用雙極模型"},
    "fw.polarity_no": {"en": "No polarity", "zh": "不使用極性"},
    "fw.polarity_choice_help": {
        "en": "A two-pole model asks whether each dimension is enacted or "
              "undermined. It only makes sense if the literature actually reads "
              "the construct that way; do not add it for richness.",
        "zh": "雙極模型問的是每個維度被彰顯還是被削弱。"
              "只有在文獻確實如此解讀該構念時才適用，不要為了豐富度而加。"},
    "fw.extra": {"en": "Additional instruction (optional)", "zh": "補充指示（選填）"},
    "fw.extra_ph": {"en": "e.g. keep the dimensions at the level of individual "
                          "practice rather than institutional policy",
                    "zh": "例如：維度請停留在個人實踐層次，不要拉到制度政策層次"},
    "fw.draft": {"en": "Draft framework", "zh": "草擬框架"},
    "fw.drafting": {"en": "Drafting from the abstracts…", "zh": "正在依摘要草擬…"},
    "fw.need_corpus": {"en": "Retrieve the literature first (step 1).",
                       "zh": "請先完成步驟 1 的文獻檢索。"},
    "fw.draft_failed": {"en": "The draft could not be used: {e}",
                        "zh": "草稿無法使用：{e}"},
    "fw.draft_ok": {"en": "Draft ready: {n} dimensions grounded in the retrieved "
                          "literature.",
                    "zh": "草稿完成：{n} 個維度，均以檢索到的文獻為依據。"},
    "fw.guard_blocked": {
        "en": "Hallucination guard: the model cited works that were never "
              "retrieved. Those citations were removed. This is the check that "
              "stops a framework being built on invented sources — read the "
              "detail below before approving anything.",
        "zh": "幻覺防護：模型引用了未被檢索到的文獻，這些引用已被移除。"
              "這道檢查正是防止框架建立在杜撰文獻上的機制——"
              "核可任何維度之前，請先讀下方細節。"},
    "fw.dropped": {"en": "Dimensions discarded before review", "zh": "審閱前已丟棄的維度"},
    "fw.warnings": {"en": "Warnings", "zh": "警告"},

    # --- 核可 ---
    "fw.approve_title": {"en": "Approve each dimension", "zh": "逐維度核可"},
    "fw.approve_hint": {
        "en": "Nothing enters the framework without an explicit decision. A "
              "dimension left undecided is treated as rejected: silence is not "
              "consent. Your decisions, edits and reasons are written into the "
              "framework file and can be reported in the methods section.",
        "zh": "沒有明確決定的維度不會進入框架。未做決定者視同退回——"
              "沉默不等於同意。你的決定、修改與理由都會寫入框架檔，"
              "可於方法章節報告。"},
    "fw.decision": {"en": "Decision", "zh": "決定"},
    "fw.dec_pending": {"en": "Not yet decided", "zh": "尚未決定"},
    "fw.dec_approve": {"en": "Approve as drafted", "zh": "原案通過"},
    "fw.dec_edit": {"en": "Approve with edits", "zh": "修改後通過"},
    "fw.dec_reject": {"en": "Reject", "zh": "退回"},
    "fw.dim_label_en": {"en": "Label (English)", "zh": "維度標籤（英文）"},
    "fw.dim_label_zh": {"en": "Label (Chinese)", "zh": "維度標籤（中文）"},
    "fw.dim_def_en": {"en": "Definition (English)", "zh": "維度定義（英文）"},
    "fw.dim_def_zh": {"en": "Definition (Chinese)", "zh": "維度定義（中文）"},
    "fw.dim_note": {"en": "Reason / note", "zh": "理由或說明"},
    "fw.dim_note_reject": {"en": "Why are you rejecting this dimension?",
                           "zh": "退回這個維度的理由是什麼？"},
    "fw.grounding_note": {"en": "What the model says this work contributes",
                          "zh": "模型說明該文獻的貢獻"},
    "fw.reviewer": {"en": "Approved by (your name)", "zh": "核可者（你的姓名）"},
    "fw.reviewer_help": {
        "en": "Approval has to be attributable. This name is written into the "
              "framework file and appears in the methods paragraph.",
        "zh": "核可必須可歸責。此姓名會寫入框架檔，並出現在方法段落中。"},
    "fw.new_id": {"en": "Framework file name", "zh": "框架檔名"},
    "fw.new_id_help": {
        "en": "Lowercase letters, digits and underscores. This becomes the file "
              "name and the identifier stored in every saved analysis.",
        "zh": "小寫英數與底線。此值會成為檔名，也會記錄在每一份分析結果中。"},
    "fw.approval_note": {"en": "Note on the framework as a whole (optional)",
                         "zh": "對整份框架的說明（選填）"},
    "fw.save": {"en": "Save approved framework", "zh": "儲存已核可的框架"},
    "fw.need_reviewer": {"en": "Enter your name: approval must be attributable.",
                         "zh": "請輸入姓名：核可必須可歸責。"},
    "fw.need_decision": {
        "en": "No dimension has been approved yet. Approve at least one.",
        "zh": "尚未核可任何維度，請至少核可一個。"},
    "fw.saved": {"en": "Saved as {id}. Select it in the sidebar to start coding "
                       "with it.",
                 "zh": "已儲存為 {id}。在左側選單選取後即可用它進行編碼。"},
    "fw.overwrite_warn": {
        "en": "A framework with this file name already exists. Saving will "
              "overwrite it, including its approval record.",
        "zh": "已存在同檔名的框架。儲存將覆蓋它，連同其核可紀錄一併覆蓋。"},
    "fw.summary_counts": {
        "en": "{a} approved as drafted, {e} approved with edits, {r} rejected, "
              "{p} still undecided",
        "zh": "原案通過 {a}、修改後通過 {e}、退回 {r}、尚未決定 {p}"},

    # --- 匯入匯出 ---
    "fw.export_active": {"en": "Download the active framework",
                         "zh": "下載現用框架"},
    "fw.export_hint": {
        "en": "A framework file is plain JSON. Share it as supplementary "
              "material so others can reproduce your coding scheme exactly.",
        "zh": "框架檔是純 JSON。可作為補充材料分享，"
              "讓其他人完整重現你的編碼架構。"},
    "fw.import": {"en": "Import a framework file (.json)",
                  "zh": "匯入框架檔（.json）"},
    "fw.import_ok": {"en": "Imported {id}. Select it in the sidebar to use it.",
                     "zh": "已匯入 {id}。在左側選單選取後即可使用。"},
    "fw.import_bad": {"en": "This file is not a valid framework: {e}",
                      "zh": "此檔案不是有效的框架：{e}"},
    "fw.installed": {"en": "Frameworks on this computer", "zh": "本機已安裝的框架"},
}

I.register(FRAMEWORK_STRINGS)


# =====================================================================
# 語言模型供應者
#
# 這一組字串在介面上的位置很前面（側欄最上方），措辭決定了使用者
# 對「資料會不會離開這台電腦」的理解。刻意寫得直白，不用「隱私友善」
# 這種模糊的行銷語彙——研究倫理審查文件要引用的是具體事實。
# =====================================================================
LLM_STRINGS = {
    "llm.provider": {"en": "Model provider", "zh": "模型供應者"},
    "llm.provider.gemini": {"en": "Google Gemini (cloud)",
                            "zh": "Google Gemini（雲端）"},
    "llm.provider.ollama": {"en": "Ollama (local)", "zh": "Ollama（地端）"},
    "llm.provider.openai_compat": {
        "en": "OpenAI-compatible endpoint (LM Studio, llama.cpp, vLLM…)",
        "zh": "OpenAI 相容端點（LM Studio、llama.cpp、vLLM…）"},
    "llm.provider_help": {
        "en": "A local provider keeps transcripts on this machine. Choose one "
              "if your ethics approval does not cover sending human-subject "
              "data to a third-party service, or if you need a model whose "
              "weights will still exist when someone tries to reproduce your "
              "study.",
        "zh": "選地端供應者，逐字稿就不會離開這台電腦。"
              "若你的研究倫理審查沒有涵蓋「把人類受試者資料傳給第三方服務」，"
              "或你需要一個三年後還存在、可供他人重現的模型權重，請選地端。"},

    "llm.base_url": {"en": "Server address", "zh": "服務位址"},
    "llm.base_url_help": {
        "en": "Ollama: http://localhost:11434 · LM Studio: "
              "http://localhost:1234/v1 · llama.cpp server: "
              "http://localhost:8080/v1 · vLLM: http://localhost:8000/v1",
        "zh": "Ollama：http://localhost:11434 · LM Studio："
              "http://localhost:1234/v1 · llama.cpp server："
              "http://localhost:8080/v1 · vLLM：http://localhost:8000/v1"},
    "llm.local_privacy": {
        "en": "This address is on your own machine. Transcripts are not sent "
              "over the network.",
        "zh": "這個位址在你自己的電腦上。逐字稿不會經由網路送出。"},
    "llm.remote_key": {"en": "API key for this endpoint",
                       "zh": "此端點的 API 金鑰"},
    "llm.remote_warning": {
        "en": "This address is not on your own machine. Transcripts will be "
              "sent to it. Check that your ethics approval covers this.",
        "zh": "這個位址不在你自己的電腦上，逐字稿會被送過去。"
              "請確認你的研究倫理審查涵蓋此一情形。"},
    "llm.model_placeholder": {
        "en": "e.g. llama3.1:8b-instruct-q4_K_M",
        "zh": "例如 llama3.1:8b-instruct-q4_K_M"},
    "llm.test": {"en": "Test connection", "zh": "測試連線"},

    "llm.num_ctx": {"en": "Context window (tokens)", "zh": "上下文長度（token）"},
    # 視窗預算攤開來。使用者調 num_ctx 卻不知道多少真的落到逐字稿上，
    # 只能靠撞牆時的錯誤訊息反推——而那時他已經選好模型、上傳好檔案了。
    "llm.budget": {
        "en": "Of {ctx} tokens: {out} reserved for the model's answer, "
              "**{room} left for the transcript** (roughly {chars} characters).",
        "zh": "{ctx} 個 token 之中：{out} 保留給模型的回答，"
              "**{room} 留給逐字稿**（約 {chars} 字元）。"},
    # SDK 沒裝時，模型欄位會退化成手打。這是可以行動的事，提示要放在
    # 撞到它的地方，而不是欄位下方一行小字。
    "llm.gemini_sdk_missing": {
        "en": "The Google SDK is not installed, so the list of available "
              "Gemini models cannot be fetched and the model has to be typed "
              "in by hand. Install it once and the field becomes a dropdown "
              "that always reflects what your key can actually reach — model "
              "names change, and a name typed from memory is the usual cause "
              "of a 404. Local providers never need this package.",
        "zh": "沒有安裝 Google SDK，所以查不到目前可用的 Gemini 模型清單，"
              "模型名稱只能手動輸入。裝一次之後這個欄位就會變成下拉選單，"
              "而且永遠反映你的金鑰實際叫得到什麼——模型名稱會變，"
              "憑記憶打上去正是 404 最常見的原因。地端供應者完全不需要這個套件。"},
    # 這幾條的存在理由：程式是雙擊啟動器打開的，畫面上沒有地方可以打指令。
    # 只印一行 pip 指令，對不寫程式的研究者而言是死路。
    "llm.gemini_sdk_install": {"en": "Install it now",
                               "zh": "現在安裝"},
    "llm.gemini_sdk_installing": {
        "en": "Installing… this downloads a few MB and takes under a minute.",
        "zh": "安裝中…會下載幾 MB，通常不到一分鐘。"},
    "llm.gemini_sdk_restart": {
        "en": "Installed. Close this window and start TACIT again — the model "
              "list appears once the program restarts.",
        "zh": "安裝完成。請關掉這個視窗、重新啟動 TACIT——重開之後模型清單就會出現。"},
    "llm.gemini_sdk_failed": {
        "en": "The install did not succeed. This is usually a network or "
              "permission problem. The command below does the same thing from "
              "a terminal, if you have someone who can run it for you.",
        "zh": "安裝沒有成功，通常是網路或權限的問題。下面這行指令做的是同一件事，"
              "如果有人能幫你在終端機執行的話可以用它。"},
    "llm.gemini_sdk_log": {"en": "Installation log", "zh": "安裝過程訊息"},
    "llm.num_ctx_help": {
        "en": "Must be large enough to hold the whole transcript. Ollama's own "
              "default is 4096 — far smaller than one interview — and a server "
              "that runs out of context truncates the input silently and still "
              "returns well-formed JSON. This tool therefore sets the value "
              "explicitly and refuses to send a prompt that would not fit. "
              "Raising it costs memory: roughly 0.5–2 GB per 32k tokens "
              "depending on the model.",
        "zh": "必須大到裝得下整份逐字稿。Ollama 的出廠預設是 4096"
              "——遠小於一份訪談——而 context 不夠時伺服器會**無聲截斷**輸入，"
              "卻照樣回傳格式完整的 JSON。因此本工具一律明確指定此值，"
              "並在提示詞放不下時直接擋下不送。調高會吃記憶體："
              "視模型而定，每 32k token 約需 0.5～2 GB。"},

    "run.need_model": {
        "en": "Choose a model first. If the list is empty, the model server is "
              "not reachable — check the address in the sidebar.",
        "zh": "請先選擇模型。若清單是空的，表示連不上模型服務，"
              "請檢查左側的服務位址。"},
}

I.register(LLM_STRINGS)


# =====================================================================
# 主題歸納：空維度警告
#
# 為什麼要獨立一則警告：Gioia 圖表只畫得出有主題的維度，所以少一個維度時
# 圖看起來完全正常。研究者會把它讀成「資料裡沒有這個面向」，而那可能只是
# 模型漏看了。這則警告的用途不是判定對錯，是讓研究者知道有這件事要判斷。
# =====================================================================
# =====================================================================
# 送出前的輸出約定探測。
#
# 這幾則的措辭有一條線不能越過：**工具不判定模型合不合格，只回報它做了
# 什麼。** 合不合用是研究者的判斷——把選擇擋掉，就是工具替他做了一個
# 方法學決定，而那正是這個軟體在別處批評的事。所以文案講的是「這顆模型
# 在這個約定上表現如何」，不是「這顆模型不好」；而且一定要附上模型實際
# 寫了什麼，否則使用者無從判斷。
# =====================================================================
CONTRACT_PROBE_STRINGS = {
    "th.contract_probing": {
        "en": "Checking whether the model can follow the output contract…",
        "zh": "正在確認模型照不照得住輸出約定…"},
    "th.contract_bad": {
        "en": "This model followed the output contract on **{n} of {total}** probe "
              "items ({pct}). Theme induction asks it to pick exactly one "
              "dimension identifier from a fixed list; a model that cannot do "
              "that reliably will still return themes, but they will arrive "
              "with unusable dimension values and be recorded as unassigned. "
              "That looks identical to a genuine finding about the data.",
        "zh": "這顆模型在探測的 {total} 題中照著輸出約定回答了 **{n} 題**（{pct}）。"
              "主題歸納要求它從固定清單裡挑出**恰好一個**維度識別碼；"
              "做不穩定的模型仍然會回傳主題，但維度值無法使用，會被記成未歸屬"
              "——那在畫面上跟「資料真的沒談到那個面向」長得一模一樣。"},
    "th.contract_advice": {
        "en": "Above is what the model actually wrote. A stronger model usually "
              "fixes this; the mapping step is harder than sentence-level coding. "
              "You can also run anyway — this is a report, not a gate, and the "
              "compliance figure is saved with the result either way.",
        "zh": "上表是模型實際寫出來的值。換一顆推理能力較強的模型通常就解決了"
              "——歸納這一步比逐句編碼難得多。你也可以照樣執行：這是回報而不是"
              "關卡，而且無論如何遵循度都會跟結果一起存下來。"},
    "th.contract_anyway": {"en": "Run anyway", "zh": "仍要執行"},
}

THEME_EMPTY_DIM_STRINGS = {
    "th.empty_dims": {
        "en": "No theme was assigned to: **{dims}**. Treat this as a question, "
              "not a finding. It may mean the data genuinely does not speak to "
              "that dimension — or that the model overlooked it. The data "
              "structure figure only draws dimensions that received themes, so "
              "a missing dimension looks identical to an absent one. Check the "
              "first-order concepts for that dimension in the Cross-analysis "
              "tab before reporting it, and consider re-running with a larger "
              "model.",
        "zh": "沒有任何主題被歸到：**{dims}**。這是一個要查證的問題，不是結論。"
              "有可能資料真的沒談到那個面向，也可能只是模型漏看了。"
              "資料結構圖只畫得出有主題的維度，所以「漏掉」跟「沒有」在圖上"
              "長得一模一樣。寫進論文之前，請先到交互分析頁籤看看該維度底下"
              "究竟有沒有一階概念，必要時換一個較大的模型重跑一次。"},

    "th.bad_dims": {
        "en": "The model wrote {n} aggregate-dimension value(s) that are not "
              "dimensions of the active framework, so those themes were placed "
              "in \"unassigned\". This is a format failure, not a judgement: "
              "smaller local models sometimes copy the whole enum "
              "(\"engagement|responsiveness\") instead of choosing one value. "
              "Re-run with a larger model before reading anything into the "
              "unassigned count.",
        "zh": "模型寫了 {n} 個不屬於現用框架的維度值，這些主題被放進「未歸屬」。"
              "這是格式沒遵守，不是它的判斷：較小的地端模型有時會把整串列舉"
              "原樣抄回來（\"engagement|responsiveness\"），而不是從中選一個。"
              "在對「未歸屬」的數字做任何解讀之前，請先換一個較大的模型重跑。"},
}

I.register(CONTRACT_PROBE_STRINGS)
I.register(THEME_EMPTY_DIM_STRINGS)
