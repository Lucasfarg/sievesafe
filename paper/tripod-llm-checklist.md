# TRIPOD-LLM checklist

Supplementary file for *A pre-specified exclusion threshold for zero-shot title and abstract screening: development on
SYNERGY+ and external validation on CLEF TAR* (Lucas Farias). Checklist from Gallifant et al., Nat Med 2025 (fillable
version, tripod-statement.org). This study is an **evaluation (E)** of an existing LLM on a **classification (C)** task
in evidence synthesis; it involves no patients or EHR data. "Where" gives the section of the manuscript.

| Item | Checklist item (abridged) | Applies | Where / answer |
|:--|:--|:--|:--|
| 1 | Identify the study as developing, fine-tuning and/or evaluating an LLM; task, population, outcome | Yes | Title; Abstract |
| 2 | Abstract (TRIPOD-LLM for Abstracts) | Yes | Structured abstract (Background, Methods, Results, Conclusions); the abstract checklist was not completed separately |
| 3a | Context / use case and rationale, with existing approaches | Yes | Introduction |
| 3b | Target population, intended use and intended users | Yes (E) | Introduction; Software and availability; Discussion. Users are systematic reviewers screening search results |
| 4 | Objectives, including stage (development, fine-tuning, validation) | Yes | Introduction (last paragraph); Methods |
| 5a | Data sources for training, tuning and evaluation, with rationale | Yes | Methods: Data; Calibration; External validation. The model's own training data are not disclosed by its developer |
| 5b | Description of the data points and their distribution (source, language, country) | Yes | Methods: Data; Results tables; `benchmark/results.md` (per-review sizes and includes) |
| 5c | Dates of the oldest and newest text item used in development and evaluation | Yes | Not reported for the records. Datasets: SYNERGY+ v3 (2026 release) and CLEF TAR 2017–2019; review versions and years are listed in `benchmark/external/results*.md` |
| 5d | Pre-processing and quality checking | Yes | Methods: Data; External validation (records from PubMed, criteria sections extracted from abstracts); `benchmark/data-manifest.json` |
| 5e | Missing and imbalanced data; reasons for omitting data | Yes | Methods: External validation (records without abstract never counted below the threshold; weighted sampling of non-included records); Limitations |
| 6a | LLM name, version and last date of training | Yes | Methods: Model and question (TypeSafe Jev, `jev-1.13.0`, alias `jev-latest` in September 2026). Training date not disclosed by the developer |
| 6b | LLM development details (architecture, training, alignment) | No (M/D) | Not applicable: an existing model was used without any training or fine-tuning; details are not public |
| 6c | How text was generated: prompt engineering, consistency of outputs, inference settings | Yes (E) | Methods: Model and question (one fixed question and policy; the model returns a probability, with no sampling settings exposed); Results: Stability and cost (run-to-run consistency) |
| 6d | Initial and post-processed output | Yes | Methods: Model and question (probability of "yes"); Evaluation (records below the threshold) |
| 6e | Classification: how probabilities were determined and thresholds identified | Yes (C) | Methods: Calibration (threshold frozen on 20 reviews; disclosed flaw and corrected procedure); Results: Calibration |
| 7a | Quality metrics for generative outputs | No | Not applicable: classification task, no generated text |
| 7b | Relevance of the outcome metrics to the downstream task | Yes (E) | Introduction (per-review recall floor); Methods: Evaluation (recall per review, share of records removed, WSS) |
| 7c | Outcome definition, how predictions were computed (API), date of inference for closed models, metrics | Yes (E) | Methods: Model and question (API, September 2026); Evaluation; code in `src/sievesafe/jev.py` and `benchmark/` |
| 7d | Subjective outcome assessment: assessors, instructions, agreement | Yes | Reference labels are the screening decisions published by the original review teams (SYNERGY+, CLEF TAR); no new assessment was made, and assessor details are those of the source datasets |
| 7e | Comparison with other LLMs, humans or benchmarks | Yes | Methods: Evaluation (ASReview 3.0.8; human title/abstract decisions); Results: Comparison with ASReview; Title and abstract decisions |
| 8a | Annotation: how text was labelled, guidelines | No | Not applicable: no annotation in this study |
| 8b | Annotation: number of annotators, agreement | No | Not applicable |
| 8c | Annotation: background of annotators or labelling models | No | Not applicable |
| 9a | Prompt design, curation and selection | Yes | Methods: Model and question (pilot on four SYNERGY reviews, one of them in the test split; results without it reported); Limitations |
| 9b | Data used to develop the prompts | Yes | Methods: Model and question (Donners 2021, Meijboom 2021, Oud 2018, Sep 2021) |
| 10 | Pre-processing before summarisation | No (SS) | Not applicable |
| 11 | Instruction tuning / alignment | No (M/D) | Not applicable |
| 12 | Compute or proxies | Yes (E) | Results: Stability and cost; External validation (requests, tokens, cost, latency) |
| 13 | Ethics approval or waiver | Yes | Ethics statement (not applicable: public bibliographic data, no participants) |
| 14a | Funding and role of funders | Yes | Funding |
| 14b | Conflicts of interest | Yes | Competing interests |
| 14c | Protocol availability | H only | `benchmark/external/PLAN.md` (plans committed before the external runs); no protocol was prepared for the SYNERGY+ development |
| 14d | Registration | H only | Not registered in a public registry; see Methods: External validation and Limitations |
| 14e | Data availability | Yes | Data and code availability |
| 14f | Code availability | Yes | Data and code availability (GitHub, Zenodo doi:10.5281/zenodo.22992078) |
| 15 | Patient and public involvement | H only | No patient or public involvement |
| 16a–16d | Flow and characteristics of patient/EHR data | No | Not applicable: no patient or EHR data |
| 17 | Performance according to pre-specified metrics | Yes | Results (Tables 1–4) |
| 18 | Results of LLM updating | Yes | Not applicable: the model version was pinned; stability between the alias and the pinned version is reported (Results: Stability and cost) |
| 19a | Overall interpretation, including fairness, with previous studies | Yes | Discussion. Fairness was not assessed: the data describe publications, not people |
| 19b | Limitations: biases, uncertainty, generalisability | Yes | Limitations |
| 19c | Challenges of the data for the task and domain | Yes (E) | Limitations (language, abstracts, labels as reference standard, labelling error in CLEF) |
| 19d | Intended use: input, end user, autonomy and human oversight | Yes (E) | Discussion; Software and availability (rank mode by default; exclusion opt-in with local validation) |
| 19e | Handling of poor-quality or unavailable input | Yes (E) | Software and availability (records without an abstract are never excluded; unscored records are kept) |
| 19f | User interaction and required expertise | Yes (E) | Software and availability; README of the tool |
| 19g | Next steps for research | Yes | Limitations (prospective study, public registration, other languages) |
