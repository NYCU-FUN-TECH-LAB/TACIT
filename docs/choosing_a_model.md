# Choosing a model

TACIT does not ship an approved model list, and it will not stop you running
any model you have installed. This page explains why, and what it does instead.

## Why there is no allowlist

A hardcoded list of "good" models is wrong within weeks. Cloud models are
withdrawn — Gemini 2.5 Flash was retired in 2026, breaking every tool that had
its name baked in. Local users install whatever they like, and new open-weight
releases appear continuously. A name-based allowlist starts blocking good
models and admitting bad ones almost immediately.

More importantly, "good enough" is not a property of a model. It is a property
of *this model, on this task, with this framework, in this language*. The same
8B model can be adequate for sentence-level coding and useless for theme
induction — that combination is exactly what we measured (below).

And there is a case where a measurably weaker model is the *right* choice: if
your ethical approval does not permit transferring transcripts to a third-party
service, a local model that scores worse is not a compromise, it is the only
compliant option. A tool that hid it from you would be making a methodological
decision on your behalf.

So TACIT reports; you decide.

## What it does instead

**Before theme induction, the tool probes the output contract.** It sends six
short items and asks the model to map each to exactly one dimension identifier
from the active framework. This takes a few seconds. It scores what came back
and shows you the model's own words if the answer did not conform.

This is not a quality judgement. It tests one specific thing: whether the model
can pick a single value from a fixed list and return it as valid JSON. That is
the step where failures are silent and expensive.

A model that fails this probe will still produce themes. They will arrive with
unusable dimension values, be recorded as `unassigned`, and look on screen
exactly like a genuine finding that the data does not speak to those dimensions.
The probe costs seconds; discovering it afterwards costs the whole run and can
cost a wrong claim in a paper.

The compliance figure is stored in `themes.json` alongside the result, so the
methods section can report it.

## Measuring your own models

```
python bench_models.py --provider ollama --models llama3.1:8b,llama3.3:70b
python bench_models.py --probe-only --models a,b,c      # seconds, contract only
```

Writes `bench_out/bench_results.json` and a markdown table. It never touches
`analyses/` — the reference coding is part of the corpus, not something a
benchmark should overwrite.

What it measures:

| Column | Meaning |
|---|---|
| `contract` | Output-contract compliance, 0–1, and a verdict |
| `segments`, `codes` | Volume produced by sentence-level coding |
| `verbatim` | Share of quotations found verbatim in the transcript — a paraphrasing or fabricating model shows up here |
| `themes`, `unassigned` | Theme induction output |
| `dimensions covered` | How many of the framework's dimensions received at least one theme |
| `minutes` | Wall-clock, per corpus |

What it does **not** measure: which model is *more accurate*. The reference
coding shipped with the demonstration corpus was authored alongside the
transcripts. It is a fixed comparison scheme, not ground truth, and agreement
with it must not be reported as an accuracy rate.

## What the differences actually look like

Two things are worth knowing before you spend an evening on this.

**The two stages fail independently.** Sentence-level coding asks the model to
find passages and label them. Theme induction asks it to abstract across
hundreds of first-order concepts and then map each result onto a fixed
enumeration. The second is materially harder, and a model can be fine at the
first while failing the second completely. Benchmark both; do not generalise
from one.

**Failure is not gradual.** The observed pattern is not "slightly worse
themes". It is a model writing `engagement|responsiveness` — copying the format
line instead of choosing — into a field that accepts one identifier, so every
theme lands in `unassigned` and three of four dimensions read as empty. That is
a cliff, not a slope, which is why a few seconds of probing is worth more than
an intuition about model size.

## Practical guidance

- **Run the probe before any long job.** The tool does this for theme induction
  automatically; `--probe-only` covers the rest.
- **Use a stronger model for theme induction than for coding.** The interface
  already defaults the theme model to the largest one it can see, for this
  reason.
- **If you must stay local and your model fails the probe**, prefer a larger
  quantisation or a larger model before concluding the data lacks a dimension.
  Re-read the empty-dimension warning: it asks you to check, not to conclude.
- **Record what you used.** The full endpoint descriptor
  (`ollama/llama3.1:8b-instruct-q4_K_M@http://localhost:11434`) is written into
  every record. A model name alone is not reproducible: the same name covers
  different quantisations on different machines.
