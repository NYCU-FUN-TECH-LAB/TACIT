# Documentation

## Status — read this first

| File | State |
|---|---|
| `TACIT_User-Manual_en.pdf` | **STALE — regenerate before submission** |
| `TACIT_User-Manual_zh.pdf` | **STALE — regenerate before submission** |
| `manual_source/` | Current. Text updated for TACIT; screenshots not retaken |
| `three_axis_codebook_v0.1.md` | Current |
| `manual_source/screenshot_list.md` | The shot list to work from |

The two PDFs were built for the previous version of this software and are
carried over so the repository is not left without a manual. They are wrong in
three ways and must be rebuilt before the SoftwareX submission goes out:

1. They call the software **RI-AutoCoder PRO** throughout.
2. Every screenshot shows the old sidebar, which had a single "Gemini API key"
   field. The current sidebar leads with a **model provider** selector and shows
   server address, context window and a connection test for local providers.
   This is the main new feature, and the manual does not mention it.
3. They describe **one** built-in framework. There are now two, and the second
   (`utaut_venkatesh_2003`) has no polarity model, which visibly changes the
   interface.

## Rebuilding

```bash
cd docs/manual_source
python make_manual.py
```

The generator reads its text from `manual_content_en.py` and
`manual_content_zh.py` — both already updated — and its images from a
`screenshots/` directory beside it, which does not exist yet. Take the shots
listed in `screenshot_list.md`, using the demonstration corpus rather than any
real interview data:

```bash
python make_demo_data.py
streamlit run app.py
```

Load the 24 reference codings from the sidebar and every tab will have content
to photograph without an API key.

New shots the old list does not cover:

- Sidebar with **Ollama** selected: server address, context window, Test connection
- Sidebar with an OpenAI-compatible endpoint on a **remote** host, showing the
  ethics warning
- The context-overflow error raised when a prompt will not fit the window
- Framework selector showing both frameworks
- Cross-analysis under UTAUT, with the polarity sub-tab absent

## A note on screenshots and research ethics

Manuals circulate — to supervisors, colleagues, students. Screenshots containing
verbatim quotations from real interviews exceed the scope of any realistic
informed-consent agreement. Use `demo_data/`, which is entirely fictional. The
old manual was built this way and the new one should be too.
