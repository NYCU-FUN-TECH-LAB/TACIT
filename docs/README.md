# Documentation

This folder holds the user documentation and the source it is built from.

- `choosing_a_model.md` — how to choose between a cloud model and a local
  model, and how to read the connection probe.
- `manual_source/` — source of the user manual in English and Traditional
  Chinese. `make_manual.py` builds each manual as a single HTML file (add
  `--pdf` for a PDF) from `manual_content_en.py` and `manual_content_zh.py`.
  The generator reads screenshots from a `screenshots/` directory beside it
  and stops if the text refers to a screenshot that is not there.

Screenshots are taken on the demonstration corpus in `demo_data/`, which is
fictional, so no real interview text appears in the manual.

```bash
cd docs/manual_source
python make_manual.py --pdf
```
