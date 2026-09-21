"""
manual_content_en.py — 操作手冊的英文內文
====================================
與 manual_content_zh 結構完全相同，供 製作使用手冊.py 讀取。

這不是逐句翻譯。中文版對台灣的研究生說話，英文版對國外的研究者與
指導教授說話——後者更在意方法論的辯護，較不需要安裝步驟的細節。
因此語氣與詳略有調整，但每一個技術主張、每一個數字都必須一致。
"""

BLOCKS = [
    ("h1", "TACIT — User Manual"),
    ("p", "A theory-driven qualitative coding tool. This manual walks from a "
          "single interview transcript to figures and statistics you can defend "
          "in a paper, and explains at each step <b>why the tool behaves the way "
          "it does</b> — because readers rarely ask which button you pressed. "
          "They ask what entitles you to the claim."),
    ("note", "All screenshots use <b>synthetic demonstration data</b> (a fictional "
             "smart-traffic-signal case) and contain no real interview material. "
             "Some screenshots show the Chinese interface; the tool is fully "
             "bilingual and the interface language is a per-user setting."),

    ("h2", "Before anything else: what this tool refuses to do"),
    ("p", "Most qualitative software treats an LLM as an autocoder: feed it a "
          "transcript, receive codes, accept them. This tool deliberately does not."),
    ("why", "<b>Three non-negotiable design commitments</b><br><br>"
            "① <b>The framework comes from literature, not from the model's memory.</b> "
            "A coding framework is the validity foundation of the entire study. "
            "Asking a model to recall the dimensions of a theory produces output that "
            "is plausible and partly invented. So framework construction here means: "
            "retrieve the literature, let the model summarise and draft from the "
            "retrieved abstracts, then approve it dimension by dimension yourself.<br><br>"
            "② <b>Interpretive authority stays with the researcher.</b> "
            "The model's coding is a <i>draft</i>. The review tab lets you confirm, "
            "revise, delete, or add segments the model missed, and every change is "
            "written to an audit trail.<br><br>"
            "③ <b>Anything computable is computed, not estimated.</b> "
            "Reliability comes from genuine double-blind double coding over a frame "
            "that includes unmarked units, so recall is meaningful; when the "
            "assumptions of a chi-square test fail, the tool refuses to print a p-value."),
    ("p", "If what you want is fast automatic coding, this tool will feel obstructive. "
          "It is built so that in a viva or a review you can account for every number."),

    ("h2", "0. Installation"),
    ("steps", [
        "Place the folder somewhere with a path free of unusual characters.",
        "Double-click <code>啟動_Windows.bat</code> (<code>啟動_Mac.command</code> on "
        "macOS, <code>啟動_Linux.sh</code> on Linux).",
        "First launch builds an isolated environment and installs dependencies "
        "(3–10 minutes), then installs a Chinese word segmenter (~400 MB). "
        "Failure of the segmenter step does not prevent use.",
        "A browser opens automatically. <b>Leave the console window open</b> — "
        "closing it stops the program.",
    ]),
    ("danger", "<b>Never copy the <code>.venv</code> folder.</b> A virtual environment "
               "records absolute paths at creation time; a copy fails with "
               "<code>Failed to import encodings module</code>, which gives no hint "
               "as to the real cause. Exclude <code>.venv</code> when moving the "
               "project. If you already copied one, just run the launcher — it "
               "detects the situation and rebuilds automatically."),
    ("shot", ("01_startup", "The nine tabs across the top are the whole workflow, and "
                            "left to right is roughly the order you work in.")),

    ("h3", "The sidebar"),
    ("shots", [
        ("02a_sidebar_top", "Upper half. The two language settings are <b>independent</b>: "
                            "interface language affects only labels, while analysis output "
                            "language controls what language the model writes its coding "
                            "rationales and theme names in. An English interface with "
                            "Chinese transcripts is a legitimate combination."),
        ("02b_sidebar_bottom", "Lower half: both API keys live here — Gemini for coding "
                               "and theme induction, OpenAlex for literature retrieval "
                               "in framework construction."),
    ]),
    ("note", "To avoid retyping the OpenAlex key, set it as the "
             "<code>OPENALEX_API_KEY</code> environment variable. It is then filled in "
             "automatically, and it does not travel with the project folder if you "
             "share the project."),

    ("h2", "1. Running an analysis"),
    ("p", "This is the only step that consumes API quota. Everything afterwards runs "
          "offline on your machine."),
    ("shot", ("03_run_upload", "Upload one or more .docx transcripts. The delay slider "
                               "sets the pause between files to avoid rate limits; "
                               "10 seconds is sensible on a free tier.")),
    ("shot", ("04_run_progress", "Each transcript is retried up to three times on "
                                 "malformed output or network failure.")),
    ("shot", ("05_run_done", "Six transcripts completed. Each reports the number of "
                             "coded segments and how many carry more than one code.")),
    ("why", "<b>Why multi-coding matters</b><br>"
            "A single passage evidencing two dimensions at once is normal in "
            "qualitative data, not noise. Forcing one code per segment destroys "
            "co-occurrence analysis — and co-occurrence is precisely where findings "
            "like \"these two dimensions are structurally bound together in "
            "respondents' accounts\" come from. The data structure here is flat: "
            "one segment may carry several codes."),
    ("warn", "<b>If quota runs out mid-run</b>, the batch stops and reports how many "
             "finished and how many never started. Swap in another key or wait for the "
             "quota to reset, keep the same file selection, and press Start again: "
             "completed transcripts are skipped automatically and are never billed twice."),

    ("h2", "2. Loading saved analyses"),
    ("shot", ("06_pick_records", "The picker lists each saved analysis with its segment "
                                 "count. Where a respondent has several saved runs, the "
                                 "filename is appended so the entries can be told apart.")),
    ("why", "<b>Why selective loading</b><br>"
            "Every analysis downstream is scoped to what is currently loaded. Loading "
            "twenty interviews at once makes crosstabs and co-occurrence matrices "
            "unreadable, and usually you want to compare three or four. Scanning is not "
            "loading: the workspace starts empty and fills only when you press Load."),

    ("h2", "3. Data and descriptors"),
    ("shot", ("07_data_descriptors", "Descriptors drive every later cross-analysis. The "
                                     "model fills them only from information the "
                                     "transcript <b>states explicitly</b>; anything not "
                                     "stated is left Unspecified. It never infers a "
                                     "descriptor from tone or topic, because inferred "
                                     "descriptors silently contaminate group comparisons.")),
    ("shot", ("08_data_health", "Data health. These figures tell you whether a transcript "
                                "can support downstream analysis at all: too few segments "
                                "or too few dimensions covered means there is little to "
                                "say under this framework.")),

    ("h2", "4. Code review: interpretive authority"),
    ("p", "Methodologically this is the most important tab. If the paper is to claim "
          "that all coding was human-verified, the review rate must reach 100% here."),
    ("shot", ("09_review_list", "Enter a <b>reviewer name</b> first — every change is "
                                "recorded against it. Approval must be attributable.")),
    ("shot", ("10_review_edit", "Expanding a segment shows the model's codes and its "
                                "stated rationale. You may confirm, re-code, or delete "
                                "the segment, and you may add segments the model missed.")),
    ("why", "<b>Why the model's original codes are retained</b><br>"
            "After a change, the model's original judgement remains in the record. This "
            "lets you answer a question readers reliably ask — how wrong was the model? "
            "The modification rate is itself a reportable figure. A rate around forty "
            "percent usually indicates the framework definitions need sharpening rather "
            "than that the model is unusable."),
    ("shot", ("11_review_audit", "The audit trail: who changed what, when, and from what "
                                 "to what. Exportable as an appendix.")),
    ("shot", ("12_review_stats", "Review statistics, with a ready-made methods paragraph "
                                 "in both languages. Every number comes from the recorded "
                                 "trail, not from an estimate.")),

    ("h2", "5. Cross-analysis"),
    ("h3", "5.1 Dimension × descriptor crosstabs"),
    ("shot", ("13_cross_crosstab", "Row percentages are shown by default rather than raw "
                                   "counts: groups differ in size, and raw counts cannot "
                                   "be compared across them.")),
    ("shot", ("14_cross_chisq", "Here the tool has determined that expected cell counts "
                                "are too low and <b>refuses to report a p-value</b>, "
                                "offering descriptive interpretation only.")),
    ("why", "<b>Why withholding the p-value is the right behaviour</b><br>"
            "Qualitative samples typically run from a handful to a few dozen respondents, "
            "so most cells fall below an expected count of 5 and the chi-square "
            "assumptions simply do not hold. Printing a p-value anyway invites a claim "
            "that cannot survive scrutiny. If a reader asks how a chi-square is "
            "justified at this n, there is no good answer — so the tool declines to "
            "produce one."),

    ("h3", "5.2 Code co-occurrence"),
    ("shots", [
        ("15a_cross_cooccur", "Switch between <b>segment level</b> (strict: both codes in "
                              "the same passage) and <b>case level</b> (loose: the same "
                              "respondent said both at some point)."),
        ("15b_cross_cooccur", "Pairs flagged <code>cross_dimension</code> carry the most "
                              "theoretical weight: two <b>different</b> dimensions bound "
                              "together within a single utterance."),
    ]),
    ("note", "<b>Why Jaccard rather than raw counts.</b> Jaccard is co-occurrence divided "
             "by the union of the two codes. A code that is simply frequent will "
             "co-occur often with everything, which is a spurious association; Jaccard "
             "removes that effect."),

    ("h3", "5.3 Cross-case matrix"),
    ("shot", ("16_cross_casematrix", "Respondent × code. Normalised, each cell is the "
                                     "share of that respondent's codes, which removes "
                                     "differences in how much each person talked.")),

    ("h3", "5.4 Polarity balance"),
    ("p", "Polarity is an extension specific to the responsible innovation framework: a "
          "dimension can be <b>enacted</b> (+) or <b>undermined</b> (−). Frameworks "
          "without polarity do not show this sub-tab at all."),
    ("shots", [
        ("17a_cross_polarity", "Polarity index = (P−N)/(P+N), bounded −1 to +1 and "
                               "normalised for coding volume, so cases are comparable."),
        ("17b_cross_polarity", "Per-dimension heatmap: where a respondent is markedly "
                               "negative becomes visible at a glance."),
        ("17c_cross_polarity", "Radar overlay, useful for contrasting group profiles."),
        ("17d_cross_polarity", "The long table. <b>Always read the index against the "
                               "total column</b> — with only one or two codes in a "
                               "dimension the index is extremely unstable."),
    ]),
    ("warn", "A polarity index of −1 does not mean a respondent is bad. It means every "
             "coded statement of theirs in that dimension fell on the undermining side. "
             "It is a property of the text, not an evaluation of a person, and the "
             "distinction belongs in the write-up."),

    ("h2", "6. Theme structure: Gioia-style data structure"),
    ("p", "Everything so far has been deductive — reading data through an existing "
          "framework. This tab inverts that: themes are induced from the data, then "
          "read back against the framework."),
    ("shot", ("18a_themes_stage1", "Two stages: first-order concepts are batched into "
                                   "provisional themes, then provisional themes are "
                                   "consolidated. The process log keeps every "
                                   "intermediate result for auditing.")),
    ("shot", ("18c_themes_stage1", "The <code>frame_relation</code> column is the one to "
                                   "read: <code>aligned</code> means the theme sits inside "
                                   "what the framework anticipates, <code>extends</code> "
                                   "means it exceeds the framework — which is where new "
                                   "contributions live.")),
    ("note", "<b>Coverage need not approach 100%.</b> Segments that form no pattern "
             "should remain unassigned; forcing them into a theme is over-interpretation. "
             "Unassigned first-order concepts are listed for inspection."),
    ("shot", ("18d_themes_stage1", "Induced themes × deductive codes. A theme spanning "
                                   "several codes is the interesting case: it cuts across "
                                   "the framework's own boundaries.")),
    ("h3", "The data structure figure"),
    ("shots", [
        ("19a_themes_structure", "First-order concepts, second-order themes, aggregate "
                                 "dimensions — the standard Gioia presentation."),
        ("19b_themes_structure", "Themes marked as extending the framework are the "
                                 "richest material for a discussion section."),
        ("19c_themes_structure", "Two themes under the engagement dimension."),
        ("19d_themes_structure", "The final section, with SVG export. SVG is vector, so "
                                 "it can be opened in Illustrator, Inkscape or PowerPoint "
                                 "to adjust type sizes before publication."),
    ]),
    ("warn", "Theme names follow the <b>analysis output language</b> set in the sidebar. "
             "With the setting on “follow the transcript”, Chinese material yields "
             "Chinese theme names."),
    ("shot", ("20_themes_matrix", "Theme × respondent support. Treat a low "
                                  "<code>support_rate</code> with suspicion — something "
                                  "only one respondent said is rarely a theme.")),

    ("h2", "7. Lexicon induction"),
    ("p", "The stance here is explicit: <b>a lexicon is not a classifier</b>. Keyword "
          "matching as a primary coding mechanism is a return to bag-of-words and "
          "performs poorly on Chinese. The lexicon is used for three things it is "
          "actually good at: discovering domain terms, inducing distinctive terms, and "
          "serving as a transparent baseline against which to audit the model."),
    ("shot", ("21_lex_discover", "Term discovery runs without any segmenter: pointwise "
                                 "mutual information filters loose combinations, and "
                                 "left/right neighbour entropy filters incomplete "
                                 "fragments.")),
    ("shots", [
        ("22a_lex_features", "Feature induction uses log-odds with an informative "
                             "Dirichlet prior (Monroe et al., 2008), which suppresses "
                             "terms common to all codes and is not misled by rare ones."),
        ("22b_lex_features", "Here every z falls below the merge threshold of 2.00, so "
                             "the merge preview contains no terms at all."),
    ]),
    ("note", "<b>The demonstration corpus is too small for significant feature terms</b>, "
             "which is itself instructive: terms with z below 2 do not belong in a "
             "lexicon. On a real corpus genuine domain vocabulary surfaces here."),
    ("h3", "Dictionary versus model"),
    ("shot", ("23_lex_audit", "This screenshot shows a <b>fault condition</b>: overall "
                              "κ = 0.0 and every <code>dict_count</code> is zero. The "
                              "dictionary coder produced nothing at all.")),
    ("danger", "<b>This screen means the loaded lexicon is empty.</b><br><br>"
               "The usual cause is a lexicon file whose name does not match the active "
               "framework and analysis language: the application finds nothing and "
               "starts from an empty lexicon. The built-in Chinese lexicon holds 239 "
               "concept terms and 17 syntactic patterns, so a count of zero means it "
               "was not read.<br><br>"
               "The application refuses to overwrite a non-empty lexicon with an empty "
               "one, so the file on disk is safe. A working installation shows real "
               "numbers here."),
    ("p", "In normal operation this page is diagnostic: codes with low κ are usually "
          "exactly where dictionary methods fail on Chinese — negation, irony, reported "
          "speech. Those concrete cases are the evidence for arguing that keyword "
          "methods are insufficient."),

    ("h2", "8. Inter-rater reliability"),
    ("shot", ("24_irr_setup", "The two collapsed panels at the top document the "
                              "methodological traps this page is built to avoid.")),
    ("why", "<b>Why the sampling frame must include unmarked units</b><br>"
            "If the second coder only sees passages the model already coded, recall is "
            "identically 1, because the frame contains nothing the model could have "
            "missed. Once unmarked units are included, anything the human coded and the "
            "model did not appears as a false negative. <b>That FN count is the "
            "\"how much did the model miss\" figure readers want.</b>"),
    ("shot", ("25_irr_sheet", "Stratification, and one downloadable coding sheet per "
                              "coder.")),
    ("shot", ("26_irr_sheet_excel", "The downloaded workbook contains quotations and "
                                    "blank code columns — <b>the model's answers are "
                                    "absent</b>. This is what makes the procedure "
                                    "genuinely blind.")),
    ("note", "The header of column C renders as repeated <code>texttexttext…</code> in "
             "this capture; the correct field name is <code>text</code>."),
    ("shot", ("27_irr_upload", "Completed sheets are uploaded back. Coding can also be "
                               "done directly in the interface.")),
    ("shot", ("28_irr_kappa", "Four coefficients side by side: observed agreement, "
                              "Cohen's κ, PABAK and Gwet's AC1.")),
    ("why", "<b>Why four coefficients rather than one</b><br>"
            "Cohen's κ is severely deflated when most units are judged absent by both "
            "coders — the kappa paradox — and qualitative coding meets this condition "
            "almost by construction, because marking is sparse. PABAK and AC1 are "
            "insensitive to prevalence, so reporting all three lets a reader judge "
            "whether a low κ reflects coder disagreement or sparse marking."),
    ("shot", ("29_irr_paradox", "When the paradox is detected the tool raises it "
                                "explicitly and states how to report it.")),
    ("shot", ("30_irr_confusion", "Dimension and polarity confusion are shown separately. "
                                  "<b>Polarity disagreement is the more serious kind</b>: "
                                  "the two coders read opposite evaluative directions from "
                                  "the same sentence, which means the codebook needs a "
                                  "sharper definition.")),
    ("shot", ("31_irr_disagree", "The disagreement list doubles as the agenda for a "
                                 "calibration meeting.")),
    ("shot", ("32_irr_recall", "Model precision and recall. <b>The FN column is the count "
                               "of segments the model missed</b>, and it is meaningful "
                               "only because the frame included unmarked units.")),

    ("h2", "9. Framework construction"),
    ("p", "This tab removes the constraint of the built-in framework: a coding framework "
          "can be constructed from literature with full provenance."),
    ("shot", ("34_fw_search", "The four sub-tabs: active framework, literature retrieval, "
                              "drafting and approval, import/export.")),
    ("h3", "Step 1 — retrieve"),
    ("shot", ("35_fw_results", "Retrieved works are numbered W1, W2 … and those "
                               "identifiers are what the hallucination guard operates on. "
                               "Here the exact phrase matched too few works, so the query "
                               "was widened to require all terms — a change recorded in "
                               "the retrieval log.")),
    ("warn", "<b>Keep the construct short.</b> Searching "
             "<code>responsible innovation</code> lets the dimensions emerge from the "
             "literature; adding <code>anticipation</code> presupposes the answer. "
             "Selecting a topic first is also worthwhile — the topic filter removes most "
             "cross-disciplinary noise."),
    ("note", "After retrieval the tool reports what share of results actually mention the "
             "query in title or abstract. Below 60% it refuses the batch outright. This "
             "guards against a specific failure: a loose query combined with citation "
             "sorting returns famous papers that merely happen to contain the words "
             "somewhere in their full text."),
    ("h3", "Step 2 — draft"),
    ("shot", ("38_fw_guard", "Retrieved abstracts are given to the model, which drafts "
                             "dimensions. The warnings panel is the hallucination guard's "
                             "output.")),
    ("why", "<b>What the hallucination guard blocks</b><br>"
            "Every reference the model cites must exist in the retrieved set. Invented "
            "citations are removed; if all citations in a draft are invented the draft "
            "fails outright rather than being partially salvaged. Each dimension must "
            "also carry at least one grounding reference or it is discarded.<br><br>"
            "The message that 23 of 30 retrieved works went unused is not an error. It "
            "reports that seventy percent of the retrieval did not inform any dimension "
            "— possibly the query was too broad, possibly the model overlooked "
            "something, and either way it is worth checking yourself."),
    ("h3", "Step 3 — approve"),
    ("shot", ("36_fw_draft", "Each dimension is presented with its definition, its "
                             "grounding references (★) and the model's account of what "
                             "each reference contributes.")),
    ("danger", "<b>A dimension with no explicit decision does not enter the framework. "
               "Silence counts as rejection, not consent.</b> Saving also requires a "
               "named approver: approval must be attributable."),
    ("shot", ("37_fw_approve", "Approval tally, approver name and framework filename. "
                               "Decisions, edits and stated reasons are all written into "
                               "the framework file.")),
    ("shot", ("33_fw_active", "The active framework lists every work it cites with role, "
                              "dimension and DOI.")),
    ("shot", ("39_fw_methods", "Dimension definitions with positive and negative "
                               "indicators and grounding literature. Each dimension of "
                               "the built-in responsible innovation framework carries "
                               "six to seven references, nearly all with DOIs.")),
    ("why", "<b>Why the provenance record matters</b><br>"
            "\"Dimensions an engineer chose from memory\" and \"dimensions retrieved "
            "systematically, ranked by citation, with recorded inclusion and exclusion "
            "and per-dimension named approval\" are different objects under review. The "
            "active framework page also generates a methods paragraph whose figures come "
            "from the recorded construction process."),

    ("h2", "10. Export"),
    ("shot", ("40_export", "Excel carries the full set of cross-analysis tables, Word is "
                           "an editable report draft, and JSON is the complete dataset, "
                           "suitable as supplementary material.")),

    ("h2", "11. Troubleshooting"),
    ("table", (
        ["Symptom", "Cause and remedy"],
        [
            ["<code>Failed to import encodings module</code> at launch",
             "The <code>.venv</code> folder was copied from elsewhere. Run the launcher "
             "again — it detects this and rebuilds — or delete <code>.venv</code> manually."],
            ["Model returns 404 or is not found",
             "That model has been retired. The tool queries the API for the current list; "
             "re-entering the key refreshes it."],
            ["Every figure on the lexicon tab is zero",
             "The lexicon does not match the active framework, or the file was not found. "
             "An explicit message appears on screen. Switch back to the matching "
             "framework, or build a lexicon for the current one."],
            ["Yellow warning at the top of the lexicon tab",
             "No Chinese segmenter is installed and the statistical fallback is in use, so "
             "some entries will be wrong word boundaries. Install with "
             "<code>pip install ckip-transformers</code> and restart."],
            ["Chi-square reports no p-value",
             "Deliberate. Expected counts are too low for the test's assumptions to hold."],
            ["Cohen's κ is low but agreement is high",
             "The kappa paradox, arising from sparse marking rather than coder "
             "disagreement. Report all three coefficients and explain."],
            ["Quota exhausted mid-analysis",
             "Swap keys, keep the same selection, press Start again. Completed files are "
             "skipped and never billed twice."],
            ["The reliability tab asks for transcripts again",
             "Only records saved by older versions need this. Transcripts analysed by this "
             "tool are carried automatically."],
        ])),

    ("h2", "12. Honest limitations"),
    ("p", "A credible description of a tool has to state what it cannot do."),
    ("bullets", [
        "<b>Model coding is not ground truth.</b> It is a draft. Coding that has not "
        "been human-reviewed should not be written up as verified.",
        "<b>Lexicon quality depends on the segmenter.</b> Without CKIP the statistical "
        "fallback has no linguistic knowledge of Chinese and will produce wrong "
        "boundaries. Semantic coding does not pass through segmentation and is unaffected.",
        "<b>Many statistics are meaningless at small n.</b> The tool withholds figures "
        "whose assumptions fail, but it cannot tell you whether six respondents support "
        "your conclusion. That is a research design question.",
        "<b>Framework construction depends on OpenAlex coverage.</b> Niche fields, "
        "non-English literature and very recent work may not be retrievable. The "
        "retrieval log records honestly how much was actually found.",
        "<b>This tool will not make a study rigorous.</b> It makes what you did "
        "traceable, reportable and checkable.",
    ]),

    ("h2", "13. References"),
    ("p", "The built-in responsible innovation framework rests on:"),
    ("bullets", [
        "Stilgoe, J., Owen, R., &amp; Macnaghten, P. (2013). Developing a framework for "
        "responsible innovation. <i>Research Policy, 42</i>(9), 1568–1580. "
        "https://doi.org/10.1016/j.respol.2013.05.008",
        "Owen, R., Macnaghten, P., &amp; Stilgoe, J. (2012). Responsible research and "
        "innovation. <i>Science and Public Policy, 39</i>(6), 751–760. "
        "https://doi.org/10.1093/scipol/scs093",
        "von Schomberg, R. (2013). A vision of responsible research and innovation. In "
        "<i>Responsible Innovation</i> (pp. 51–74). Wiley.",
    ]),
    ("p", "Statistical methods:"),
    ("bullets", [
        "Monroe, B. L., Colaresi, M. P., &amp; Quinn, K. M. (2008). Fightin' words. "
        "<i>Political Analysis, 16</i>(4), 372–403.",
        "Gwet, K. L. (2008). Computing inter-rater reliability and its variance in the "
        "presence of high agreement. <i>British Journal of Mathematical and Statistical "
        "Psychology, 61</i>(1), 29–48.",
        "Gioia, D. A., Corley, K. G., &amp; Hamilton, A. L. (2013). Seeking qualitative "
        "rigor in inductive research. <i>Organizational Research Methods, 16</i>(1), 15–31.",
    ]),
]
