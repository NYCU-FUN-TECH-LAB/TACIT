# TACIT

**Theory-Anchored Coding with Interpretive Transparency.**

A Streamlit application that codes interview transcripts against a *pluggable*
theoretical framework, keeps interpretive authority with the researcher, and
reports the statistics a reader will actually ask for — including inter-rater
reliability computed from genuine double-blind double coding.

Language models can run **entirely on your own machine**, so transcripts need
not leave it.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE.txt)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-20%20suites-brightgreen.svg)](#testing)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22882168.svg)](https://doi.org/10.5281/zenodo.22882168)

---

## What makes this different

Most qualitative tools treat a language model as an autocoder: feed it a
transcript, get codes back, accept them. This one refuses to work that way, for
four reasons.

**The framework comes from literature, not from the model's memory.**
A coding framework is the validity foundation of the whole study. Asking a model
to recall the dimensions of a theory produces output that is plausible and
partly invented, including citations to work that does not exist. Here you
retrieve literature from OpenAlex, the model drafts dimensions *from the
retrieved abstracts*, and a hallucination guard rejects any citation that was
not actually retrieved. You then approve the framework dimension by dimension,
under your own name.

**Interpretive authority stays with the researcher.**
Model coding is a draft. Every code can be confirmed, revised or deleted, and
you can add segments the model missed. Every change is written to an audit
trail, and the model's original judgement is retained — so "how often did the
model need correcting?" becomes a reportable number rather than an unknown.

**Anything computable is computed, not estimated.**
Reliability uses a sampling frame that *includes unmarked units*, so recall is
meaningful — without them, recall is identically 1 and the number is
meaningless. When the assumptions of a chi-square test fail, the tool refuses to
print a p-value rather than inviting a claim that cannot survive scrutiny.

**Your data does not have to leave your machine.**
Interview transcripts are human-subject data. Whether they may be sent to a
third-party service is decided by your ethics approval, and approvals written
before generative AI generally do not cover it. Point TACIT at a local model
server and nothing goes over the network. It also helps reproducibility: cloud
models get withdrawn, and the weights behind a version string change silently,
whereas a local model has a fixed weight file you can name in a paper.

---

## Try it

| | |
|---|---|
| **Manual (English)** | `docs/TACIT_User-Manual_en.pdf` |
| **Manual (中文)** | `docs/TACIT_User-Manual_zh.pdf` |
| **Demo corpora** | 80 witness transcripts from U.S. congressional hearings on AI governance (public domain) · 24 synthetic English interviews with reference codings · 6 Traditional Chinese |

The synthetic interviews ship with **a reference coding for every one of
them**, so you can open every tab and see real results with **no API key and
no local model**. The hearing transcripts are real speech you can check against
its source. See [Demonstration data](#demonstration-data).

---

## Evaluating TACIT without a model

You do not need a model to evaluate this software. There are three levels, and
the first two need nothing installed beyond the requirements.

**Level 1 — no model, no key, our data.** Install, launch, and in the sidebar
tick the shipped analyses under `analyses/`. Every analysis tab then works on
real coded material: cross-tabulations, co-occurrence, the cross-case matrix,
the audit trail in the coding-review tab, the reliability report, and the
Excel/Gioia exports. This exercises everything except the calls to the model
itself. The shipped codings are read-only — editing one saves a new file and
records what it was derived from, so the reference material cannot be
overwritten by accident.

**Level 2 — no model, no key, your own transcripts.** Open the reliability tab
and set *Build the frame from* to *Transcripts I upload here*. Upload your own
`.docx` files; TACIT splits them into speaking units, draws a blinded sample
from a seed you choose, and issues one coding sheet per coder. Take the
completed sheets back and you get percentage agreement, Cohen's κ, PABAK,
Gwet's AC1 and Krippendorff's α, per code and pooled, with the disagreement
list.

That is not the end of it. *Turn these codings into an analysis* sends a
coder's completed sheet into the workspace as ordinary records, and every
analysis tab then works on them: crosstabs by case descriptor with the
chi-square guard, co-occurrence, the cross-case matrix, lexicon discovery, the
Excel and Gioia exports — and theme grouping, which clusters the codes by
co-occurrence or by label similarity and leaves the naming to you. A complete
two-coder thematic analysis, from transcript to data structure, with no model
involved at any point and nothing leaving the machine.

**Level 3 — with a model.** Either a free Google Gemini key
(<https://aistudio.google.com/apikey>, no payment details required) or a local
Ollama model. See [Choosing a model provider](#choosing-a-model-provider).

One thing about the free Gemini tier is worth knowing before you plan a run,
because it is easy to misread as a broken key. **The daily request quota is per
project and per model, not per key**, so issuing a second key in the same
project changes nothing. The limit differs sharply between models: as of
September 2026 `gemini-3.6-flash` allowed 20 requests per day, which will not
finish a single transcript, while `gemini-3.5-flash-lite` completed a
12-transcript windowed run (149 requests) with room to spare. A 429 reply names
the quota it hit — look for `GenerateRequestsPerDayPerProjectPerModel` and the
`limit:` value — and TACIT reports quota errors separately from a busy server,
because waiting helps with the second and not with the first.

---

## Install

Requires Python 3.9+.

```bash
git clone https://github.com/NYCU-FUN-TECH-LAB/TACIT.git
cd TACIT
```

Then double-click the launcher for your platform:

| Platform | Launcher |
|---|---|
| Windows | `launch_windows.bat` |
| macOS | `launch_mac.command` |
| Linux | `launch_linux.sh` |

The launcher creates an isolated environment, installs dependencies, picks a
free port and opens a browser. First run takes 3–10 minutes.

Prefer to do it manually:

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run src/app.py
```

---

## Choosing a model provider

Pick the provider at the top of the sidebar. Everything downstream — coding,
theme induction, framework drafting — uses whichever you chose.

| Provider | Needs a key | Data leaves your machine | Extra Python package |
|---|---|---|---|
| **Ollama** | no | **no** | none |
| **OpenAI-compatible endpoint** (LM Studio, llama.cpp server, vLLM, LocalAI) | no, if it is on localhost | **no**, if it is on localhost | none |
| **Google Gemini** | yes | yes | `google-genai` (installed with the requirements) |

All three providers work straight after installation. The Google SDK is part
of `requirements.txt`, so a machine without Ollama or any other local model
server can use Gemini as soon as TACIT is installed. The local providers use
only the Python standard library.

The older `google-generativeai` package still works and is detected
automatically, but Google has ended support for it; the sidebar will say so and
point at the replacement.

### Local setup in three commands

```bash
ollama serve
ollama pull llama3.1:8b-instruct-q4_K_M
streamlit run src/app.py
```

Then choose **Ollama (local)** in the sidebar, set the address to
`http://localhost:11434`, and press **Test connection**.

### One thing you must get right: the context window

Ollama's default context window is 4,096 tokens. **One interview does not fit.**
A server that runs out of context truncates the input *silently* and still
returns well-formed JSON — so your coding looks complete while half the
transcript was never read. This is the most dangerous failure mode in local
deployment precisely because nothing goes wrong on screen.

TACIT therefore sets the context window explicitly (default 32,768), exposes it
in the sidebar, estimates the prompt length before sending, and **refuses to
send a prompt that would not fit**. Raise it for long transcripts; it costs
memory, roughly 0.5–2 GB per 32k tokens depending on the model.

### Batch and scripted runs

```bash
export TACIT_PROVIDER=ollama
export TACIT_MODEL=llama3.1:8b-instruct-q4_K_M
export TACIT_BASE_URL=http://localhost:11434
export TACIT_NUM_CTX=32768
```

The sidebar picks these up as defaults.

### What gets recorded

Every analysis record stores the **full endpoint descriptor**, not just the
model name — `ollama/llama3.1:8b-instruct-q4_K_M@http://localhost:11434` rather
than `llama3.1:8b`. The same short name means different quantisations on
different machines, and a record that only names the model cannot be
reproduced.

---

## Pluggable frameworks

Three frameworks ship with the tool, and they are deliberately unalike — each
one exercises a different part of the framework contract:

| Framework | Dimensions | Polarity | Field | What it tests |
|---|---|---|---|---|
| `ri_stilgoe_2013` | Anticipation, Reflexivity, Engagement, Responsiveness | yes, `P`/`N` → 8 codes | Responsible innovation | the default |
| `utaut_venkatesh_2003` | Performance expectancy, Effort expectancy, Social influence, Facilitating conditions | none → 4 codes | Technology acceptance | a framework with **no polarity model** |
| `esg_disclosure_probe` | Targets and baselines, Measurement and boundary, Governance and accountability, Stakeholder engagement | yes, `S`/`A` → 8 codes | Sustainability disclosure | polarity values that are **not** `P`/`N`; a non-interview corpus |

None of them is hard-coded. Dimensions, polarity values, descriptor fields and
interface labels live in a JSON file, and the analysis engines, prompts and
schema all derive from whichever framework is active. Switching to UTAUT
collapses codes from `ANT-P`/`ANT-N` to `PE`, and the polarity sub-tab
disappears because that analysis is meaningless without a polarity model.

The third framework guards against a specific failure: code that derives the *dimensions* from the active framework but still wrote the two
polarity values as the literals `"P"` and `"N"` in the polarity-balance
statistics and in the lexicon coder — which no test caught, because the only
other framework that shipped had no polarity model at all and skipped those code
paths entirely. `esg_disclosure_probe` names its poles `S` (substantiated) and
`A` (asserted), so it does exercise them. `tests/test_frameworks_shipped.py`
runs every framework in `frameworks/` through the full analysis pipeline for
exactly this reason: a pluggability claim is only worth as much as the least
similar framework you have actually run.

Any deductive coding scheme is in scope — template analysis, framework analysis,
theory-driven content analysis. Write a JSON file, or build one from retrieved
literature in the Framework builder tab.

---

## Demonstration data

Two corpora ship, and they are different kinds of thing. Do not mix them up.

| | Congressional hearings | Synthetic interviews | Synthetic, Chinese |
|---|---|---|---|
| Folder | `demo_data/hearings/` | `demo_data/en/` | `demo_data/zh/` |
| What it is | **real** testimony, public record | **fictional**, written by a language model | fictional |
| Transcripts | 80 witnesses, 22 hearings (24 form the paper's subset) | 24 | 6 |
| Sectors | industry, academia, government, civil society | the same four, six each | 4 |
| Reference codings | none | 24, in `analyses/` | — |
| Use it for | open coding, screenshots, anything you want a reader to be able to verify | statistics, agreement against a fixed standard, regression tests | CKIP segmentation, language routing |

**The hearings** are U.S. congressional hearings on artificial-intelligence
governance, March 2023 to June 2025, retrieved from
[govinfo.gov](https://www.govinfo.gov) and in the public domain under
17 U.S.C. § 105. The record was split at witness level, one file per speaker;
prepared statements reprinted in the record were left out because they are
written documents, not testimony. `manifest.json` gives the package identifier,
hearing title, date, chamber and source URL for every witness, the hand-assigned
sector, and the three witnesses excluded with the reason for each.

```bash
python src/make_hearing_corpus.py    # re-fetches from govinfo and rebuilds the corpus
```

**The synthetic interviews** are fictional. Transcripts and reference codings
alike were written by a language model (Claude) against the responsible-innovation
codebook, so every quotation is by construction a clean substring of a passage
that exemplifies its code. That is what makes them a fixed comparison standard,
and it is also why agreement measured against them is an **upper bound** —
expect lower figures on real transcripts. They must not be cited as empirical
data. Read `demo_data/en/00_ABOUT_THIS_DATA.txt` before using them.

```bash
python src/make_demo_data.py         # rebuilds the .docx files and reference codings
```

### Why twenty-four and not six

Six transcripts are enough to walk through the interface and not enough for a
single inferential statistic to run. In a 2×4 crosstab of institution type
against polarity, expected cell counts land around one or two, the chi-square
assumptions fail, and the tool correctly refuses to print a p-value. A newcomer
then opens the cross-analysis tab and sees a column of insufficient-data
notices — the part of the tool most worth examining shows nothing at all.

With 24 respondents the corpus produces:

| Quantity | Value |
|---|---|
| Coded segments | 148, of which 36 (24%) are coded more than once |
| Codes assigned | 184 (one per researcher judgement) |
| Analysis units | 181 distinct segment × dimension × polarity |
| Reliability sampling frame | 299 units, **174 of them unmarked** |
| Institution type × polarity | χ²(3) = 10.04, *p* = .018, *V* = .236, min. expected 18.1 |
| Institution type × dimension | χ²(9) = 7.19, *p* = .617, *V* = .115, assumptions met |
| Institution type × full code set | assumptions not met, p value withheld |

Those three rows are all deliberate: one significant, one null with assumptions
met, one withheld. A demonstration corpus in which every test came out
significant would be demonstrating the corpus, not the method.

The two code counts differ because they answer different questions. Three
segments carry two judgements on the same dimension and polarity, with
different rationales; the record keeps both, because a rationale is the
researcher's reasoning and not an annotation. The analysis layer counts each
segment once per dimension and polarity, because counting one passage twice
under the same code would inflate its co-occurrence and Jaccard weights.
Both numbers are correct; any report has to say which one it is using.

### About the reference codings

The codings in `analyses/` were **written alongside the transcripts**. They are
not the output of any particular model run and should not be read as evidence of
how well any model performs. They exist so every tab can be opened without an
API key.

Using them as a comparison set for reliability *is* a legitimate use: run the
coder yourself, then compare your run against this fixed, deliberately designed
scheme.

---

## Handling real interview data

**Keep confidential transcripts outside this folder.** `.gitignore` only
excludes files that are not already tracked; it is a safety net, not a
guarantee. A single `git add -f` defeats it.

```
project/
├── tacit/            ← this repository
└── research-data/    ← your transcripts and analyses, never committed
```

If your ethics approval does not permit sending transcripts to a third-party
service, use a local provider and verify the address is on `localhost`. The
sidebar states which case you are in.

---

## What's in each tab

| Tab | Purpose |
|---|---|
| Run analysis | Code transcripts against the active framework. The only step that uses model capacity |
| Data & descriptors | Edit respondent attributes; these drive every later comparison |
| Code review | Confirm, revise, delete or add codes. Full audit trail |
| Cross-analysis | Crosstabs, co-occurrence, cross-case matrix, polarity balance |
| Theme structure | Two-stage inductive theme induction with a model, or model-free grouping of the codes by co-occurrence or label similarity which you name yourself; Gioia data structure figure with SVG export |
| Lexicon induction | Term discovery, log-odds feature induction, dictionary baseline for auditing the model |
| Reliability | Sampling frame from records or from transcripts you upload, double-blind coding sheets, κ / PABAK / AC1 / Krippendorff α, confusion matrices, model precision and recall, and human codings turned back into analysable records |
| Export | Excel, Word, JSON |
| Framework builder | Retrieve literature from OpenAlex, draft dimensions, approve them individually |

---

## Reproducing the numbers in the paper

Every figure quoted in the SoftwareX article comes from one of the scripts
below, and each writes its raw output under `bench_out/`, which is kept in this
repository. Run them from the project root with the virtual environment active.

| What it produces | Command |
|---|---|
| Demonstration corpus and reference codings (Table 7) | `python src/make_demo_data.py` then `python run_tests.py demo` |
| Model comparison: segments, codes, κ against the reference codings, wall time (Table 6) | `python src/bench_models.py --provider ollama --models llama3:8b` |
| The same for a cloud model | `python src/bench_models.py --provider gemini --models gemini-3.5-flash-lite --api-key <key>` |
| Agreement against the reference codings on the 299-unit frame (Section 3) | `python src/bench_agreement.py bench_out/local_8b/records/llama3_8b/en` |
| Single-pass against windowed yield (Section 2.4) | `python src/bench_yield.py --model llama3:8b` |
| Open coding, one run on the twelve-transcript subset (Table 8) | `python src/bench_open_coding.py --corpus hearings --model llama3:8b --per-sector 3 --tag 12_run1` |
| The same with a cloud model | `python src/bench_open_coding.py --corpus hearings --provider gemini --model gemini-3.5-flash-lite --per-sector 3 --tag 12_run1` |
| Table 8 itself: median and range over the archived runs, no model needed | `python src/bench_open_summary.py` |
| Figure 2, computed from the shipped context formula | `python paper/make_fig2.py` |
| Figure 6, the three-level data structure | `python paper/make_fig6.py` |

Two caveats about exactness.

**The cloud row cannot be reproduced identically.** Weights behind a stable
version string change and older versions are withdrawn, which is one of the
arguments the article makes. The archived outputs under
`bench_out/cloud/` are therefore the record of what that run did; re-running
gives a comparable but not identical result.

**Runs vary between samples, by a lot.** On the same twelve transcripts, in the
same order, at the same temperature, the cloud model returned 89, 143 and 156
codes and the local 8B model 11, 27 and 108. One open-coding run is therefore
not a reportable number. Give each run its own `--tag` (the archived ones are
`12_run1`, `12_run2`, `12_run3`) so it lands in its own directory; `bench_open_summary.py` then reports the median and range, and
leaves out runs made by a different version of the code, saying which and why.

---

## Testing

```bash
python run_tests.py
```

Seventeen suites, **none requiring network access, an API key or a model
server**. The OpenAlex client is tested against offline fixtures, the provider
abstraction against fake transports, and the interface end-to-end with
Streamlit's `AppTest` in both languages and several frameworks.

`tests/test_frameworks_shipped.py` enumerates the real `frameworks/` directory
rather than a hard-coded list, and pushes every framework it finds through the
whole pipeline — schema, prompt, cross-tabs, co-occurrence, polarity balance,
lexicon, review, themes, reliability sampling and interface labels. Adding a
framework file adds it to the test run automatically. This suite exists because
the pluggability claim had been tested only against frameworks that happened to
resemble the default one.

Run one suite:

```bash
python run_tests.py demo
```

---

## Optional: Traditional Chinese segmentation

```bash
pip install ckip-transformers
```

Installed automatically by the launchers. Without it the lexicon module falls
back to an n-gram heuristic with no linguistic knowledge of Chinese, and some
entries will be wrong word boundaries. Semantic coding does not pass through
segmentation and is unaffected.

---

## Citation

If this tool contributes to published work, please cite it. See
[CITATION.cff](CITATION.cff); machine-readable metadata is in
[codemeta.json](codemeta.json).

Every release is archived on Zenodo. Version 1.0.0 is
[10.5281/zenodo.22882169](https://doi.org/10.5281/zenodo.22882169);
[10.5281/zenodo.22882168](https://doi.org/10.5281/zenodo.22882168) always resolves to
the latest version.

The built-in frameworks rest on:

- Stilgoe, J., Owen, R., & Macnaghten, P. (2013). Developing a framework for
  responsible innovation. *Research Policy, 42*(9), 1568–1580.
  https://doi.org/10.1016/j.respol.2013.05.008
- Venkatesh, V., Morris, M. G., Davis, G. B., & Davis, F. D. (2003). User
  acceptance of information technology: Toward a unified view. *MIS Quarterly,
  27*(3), 425–478. https://doi.org/10.2307/30036540

Statistical methods:

- Monroe, B. L., Colaresi, M. P., & Quinn, K. M. (2008). Fightin' words.
  *Political Analysis, 16*(4), 372–403.
- Gwet, K. L. (2008). Computing inter-rater reliability and its variance in the
  presence of high agreement. *British Journal of Mathematical and Statistical
  Psychology, 61*(1), 29–48.
- Gioia, D. A., Corley, K. G., & Hamilton, A. L. (2013). Seeking qualitative
  rigor in inductive research. *Organizational Research Methods, 16*(1), 15–31.

---

## Limitations

- Model coding is a draft, not ground truth. Unreviewed coding should not be
  written up as verified.
- Small local models produce noticeably fewer segments and follow the output
  format less reliably than large ones. If a model keeps failing to return
  parseable JSON, it is usually too small or is a base rather than an
  instruction-tuned model.
- **Theme induction under-covers dimensions, and which dimension it drops
  varies by model.** Running the shipped 24-transcript corpus through four
  local models gave four different answers: qwen2.5:7b covered 1 of the 4
  dimensions, llama3:8b missed anticipation, mistral:7b missed reflexivity,
  gemma3:12b missed responsiveness — even though the corpus contains 43–49
  codes in every dimension by construction. Do not read a missing dimension
  in the data structure figure as a finding. The Theme structure tab now says
  so explicitly when a dimension receives no themes; check the first-order
  concepts before concluding anything, and prefer the largest model you can
  run.
- Lexicon quality depends on the segmenter; without CKIP some Chinese entries
  will be wrong word boundaries.
- Many statistics are meaningless at small *n*. The tool withholds figures whose
  assumptions fail, but it cannot tell you whether twenty-four respondents
  support your conclusion.
- Framework construction depends on OpenAlex coverage. Niche fields,
  non-English literature and very recent work may not be retrievable.
- **This tool will not make a study rigorous.** It makes what you did traceable,
  reportable and checkable.

---

## License

MIT — see [LICENSE.txt](LICENSE.txt).
