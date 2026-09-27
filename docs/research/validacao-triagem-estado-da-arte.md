> **Note (2026-09-27):** research notes written before the final benchmark runs. Some figures here (for example tokens
> per record and total cost) are superseded; the current numbers are in `benchmark/results.md` and
> `benchmark/external/`.

# Is the Jev zero-shot screening result strong against the 2023–2026 state of the art?

Research date: 2026-09-27. Labels: **[M]** = measured by Lucas (from the brief, not re-run here); **[R]** = reported by the cited source; **[I]** = my inference or arithmetic.

---

## 0. Verdict (short)

- **Ranking quality is at or above the published zero-shot SOTA on SYNERGY-family data, and above ASReview's default model.** Median WSS@95 0.763 [M] vs LGAR (Llama-3.3-70B, ACL Findings 2025) mean WSS@95 0.652 on the 26 original SYNERGY reviews [R], and vs ASReview NB/LR+TF-IDF median 0.675/0.716 on the same 26 [R]. The aggregation differs (your median vs their mean) and so do the review sets (SYNERGY+ test vs SYNERGY v1). Read it as "same league, probably ahead", not a proven win.
- **As a yes/no classifier it is weaker than frontier LLMs with good prompts.** At 98% recall you auto-exclude 66% [M]. Recent GPT-4o/GPT-5/Gemini 2.5 papers report about 95–100% sensitivity at 92–98% specificity, on smaller and easier sets [R]. The cost is about 50–100× lower than GPT-4o [R/I], but only about 2× lower than gpt-4o-mini [R/I].
- **The new part is the protocol, not the accuracy.** You froze the threshold on 20 train reviews, it transferred to 23 unseen reviews, and it kept 100% recall in 23/23 [M]. The closest published result is Wang et al. (ECIR 2024): their calibrated zero-shot thresholds hit a 95% recall target in only about 50% of topics [R]. Nobody seems to have published anything on SYNERGY+ v3's official train/test split yet, because it was released on 2026-08-27 [R].
- **Safe claim:** "On the SYNERGY+ v3 test split, a threshold frozen on the train split transferred with no lost includes in 23/23 reviews while removing 29% of records unread. The same scores rank as well as or better than ASReview's default active learner, which needs labels, in most reviews, at about US$0.05 per 1,000 records." Do **not** claim "guaranteed recall". With 0/23 failures, the 95% upper bound on the per-review failure rate is still about 12% [I].

---

## 1. Your result, restated with derived numbers

| Item | Value | Tag |
|---|---|---|
| Test set | SYNERGY+ v3 test split: 23 reviews, 33,001 records, 597 includes (prevalence 1.81%) | [M]/[I] |
| t = 0.06 (frozen on train) | 100% recall in 23/23 reviews; 29% auto-excluded | [M] |
| t = 0.17 | 98% pooled recall (about 12 includes lost); 66% excluded | [M]/[I] |
| t = 0.26 | 93% pooled recall (about 42 lost; missed the 95% target); 76% excluded | [M]/[I] |
| Ranking | median AUC 0.966; median WSS@95 0.763; median WSS@100 0.808 | [M] |
| ASReview 3.0.8 default (ELAS u4 = SVM + TF-IDF bigrams), 1+1 random priors, 3 seeds | median WSS@95 0.723; WSS@100 0.711 | [M] |
| Jev ≥ ASReview | 19/23 (WSS@95) and 18/23 (WSS@100); two-sided sign-test p ≈ 0.003 and 0.011 | [M]/[I] |
| Cost | about 1,190 input tokens per record at US$0.042/Mtok, so about US$1.65 for all 33,001 records | [I] from [Jev price](https://docs.typesafe.ai/models.md) |
| Statistical bound, t = 0.06 | 0 misses in 23 reviews, so the 95% upper bound on "a new review loses ≥1 include" is 12.2%. Record level: 597/597 gives a 95% lower bound on recall of 99.5%, but includes cluster by review, so the review-level bound is the honest one | [I] |

Sanity note: median WSS@100 > WSS@95 looks odd but is expected. In reviews with fewer than 20 includes, "95% recall" rounds up to all includes, so WSS@95 = WSS@100 − 0.05 there [I]. Say this in any write-up.

---

## 2. Published LLM title/abstract screening results (2023–2026)

### 2.1 Directly comparable: zero-shot, uses eligibility criteria, SYNERGY or CLEF, ranking metrics

| Paper | Setup | Result | Tag |
|---|---|---|---|
| **LGAR**, Jaumann et al., ACL Findings 2025 ([arXiv 2505.24757](https://arxiv.org/abs/2505.24757), [ACL](https://aclanthology.org/2025.findings-acl.412/)) | Zero-shot. Llama-3.3-70B gives each paper a 0–19 relevance score from manually extracted criteria plus research questions, then a monoT5 dense re-ranker. **All 26 SYNERGY v1 reviews** plus the CLEF TAR2019 test split (31 SLRs). Macro-averaged. | SYNERGY: **WSS@95 65.2, WSS@100 49.3, TNR@95 67.0, MAP 40.7**. Replicated GPT-QA baseline (Akinseloyin et al.): WSS@95 59.5. BM25: 33.6. TAR2019: WSS@95 71.2, WSS@100 60.9. Qwen2.5-72B: TNR@95 68.5 on SYNERGY. Needs 70B-class GPUs (multi-A100). | [R] (Table 2/3, PDF) |
| **Wang et al.**, ECIR 2024 ([arXiv 2401.06320](https://arxiv.org/abs/2401.06320)) | Zero-shot 7–13B LLMs (LLaMA-2 etc.) on CLEF TAR 2017/18/19 and the Seed collection. **Calibrated threshold for a 0.95 recall target**, set leave-one-out from other topics' score distributions. | Calibrated ensemble (LLaMA2-7b-ins + 13b-ins + BioBERT): **success rate (topics reaching target) 0.49–0.52, WSS 0.50–0.54**. Uncalibrated LLaMA2-7b-ins: recall 0.87–0.92, WSS 0.40–0.59. | [R] |
| **Dennstädt et al.**, Systematic Reviews 2024 ([PMC11180407](https://pmc.ncbi.nlm.nih.gov/articles/PMC11180407/)) | Open LLMs on 10 ASReview datasets that overlap SYNERGY (Wilson, PTSD, …). Likert 1–5, "≥3" classifier. | Platypus2-70B: **97.6% sens / 38.3% spec**. Mixtral: 81.9 / 75.2. FlanT5: 94.5 / 31.8. | [R] |

**Reading [I]:** your t = 0.06 point (100% recall / 29% excluded) is in the same region as Dennstädt's recall-first classifiers. Your t = 0.17 point (98% / 66%) dominates them. Your ranking (median WSS@95 0.763) beats LGAR's SYNERGY mean (0.652) on its face. But LGAR is a **mean** over **26 v1 reviews**, and SYNERGY+ drops no-abstract records and small reviews. Recompute your mean, and ideally rerun on SYNERGY v1's 26 reviews, before claiming it.

### 2.2 Classification-style LLM studies (sensitivity/specificity), mostly medicine

| Paper | Model / data | Sens | Spec / work saved | Cost | Tag |
|---|---|---|---|---|---|
| Guo et al., JMIR 2024 ([arXiv 2305.00844](https://arxiv.org/abs/2305.00844)) | GPT-4, 6 reviews, >24k records | 0.76 (includes) | 0.91 (excludes) | n/a | [R] |
| Syriani et al., J. Comp. Lang. 2024 ([ScienceDirect](https://www.sciencedirect.com/science/article/pii/S2590118424000303)) | ChatGPT, SE reviews | high recall | up to 82% accuracy, low precision | n/a | [R] |
| Kohandel Gargari et al., BMJ EBM 2024 ([PubMed](https://pubmed.ncbi.nlm.nih.gov/37989538/)) | GPT-3.5 | max 0.69 | n/a | n/a | [R] |
| Khraisha et al., RSM 2024 ([Wiley](https://onlinelibrary.wiley.com/doi/10.1002/jrsm.1715)) | GPT-4, multilingual | "none to moderate" after chance correction | n/a | n/a | [R] |
| Tran et al., Annals 2024 ([ACP](https://www.acpjournals.org/doi/10.7326/M23-3389)) | GPT-3.5 Turbo, 5 reviews, 22,665 citations | 94.6–99.8% (sensitive rule) | 2.2–46.6% | n/a | [R] |
| Oami et al., JMIR Med Inform 2025 ([PMC11922487](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11922487/)) | GPT-4 Turbo, 5 sepsis CQs | 0.85 | 0.98 | n/a | [R] |
| Oami et al., RSM 2025 ([PMC12657656](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12657656/)) | GPT-4o / Gemini 1.5 Pro / Sonnet 3.5 / Llama 3.3-70B, 16,669 citations | 0.85 / 0.94 / 0.94 / 0.88 | 0.97 / 0.85 / 0.80 / 0.93 | **US$0.40 / 0.28 / 0.39 per 100 records**, i.e. about $0.003–0.004 per record | [R] |
| Sanghera et al., JAMIA 2025 ([PMC12012331](https://pmc.ncbi.nlm.nih.gov/articles/PMC12012331/)) | 6 LLMs, zero-shot, 23 Cochrane reviews (all of CDSR 2023 Issue 8), **119,695 records, final-inclusion labels** | GPT-4o: 0.904; Sonnet 3.5: 0.823; GPT-3.5 "heavy": 1.000 | GPT-4o spec 0.949; Sonnet 0.982; GPT-3.5 0.419. **Perfect-sensitivity ensembles save only 37.6–41.8%** | n/a | [R] |
| Cao et al., Annals 2025 ([doi](https://doi.org/10.7326/annals-24-02189)) | GPT-4-class models with tuned "ScreenPrompt" templates | 96% (validation) | 92.5% | reported low; not verified here | [R] |
| Sciurti et al., RSM 2025 ([PMC12873614](https://pmc.ncbi.nlm.nih.gov/articles/PMC12873614/)) | gpt-4o-mini / Llama 3.1-8B / Gemma 2-9B, zero-shot, 3 reviews (1.7k–21k records) | 74.5–93.1% | spec 79.9–92.7%, work saved 65.9–90.8% | gpt-4o-mini **US$0.14–1.93 per review**, about $0.00009 per record | [R]/[I] |
| Kim et al., JMAI 2025 ([JMAI](https://jmai.amegroups.org/article/view/10102/html)) | Own GPT-4o-mini tool | 100% | 81% | **US$0.00008 per record, 1.7 s** | [R] |
| Wang Y. et al., batch-size study, 2025/26 ([PMC13073229](https://pmc.ncbi.nlm.nih.gov/articles/PMC13073229/)) | Gemini 2.5 Pro / GPT-5 / GPT-5 mini / Gemini 2.5 Flash, **one** Cochrane review, 790 refs, 11.8% prevalence | 1.00 / 0.97 / 0.99 / 0.95 | 0.95 / 0.98 / 0.96 / 0.93 | n/a | [R] |
| otto-SR, Bobrovitz et al., medRxiv 2025 ([medRxiv](https://www.medrxiv.org/content/10.1101/2025.06.13.25329541v1.full)) | Agentic GPT-4.1/o3-class pipeline | 96.7% (humans 81.7%) | 97.9% | expensive (frontier models) | [R] |
| TiAb Review Plugin, 2026 ([arXiv 2604.08602](https://arxiv.org/abs/2604.08602)) | Gemini 3.0 Flash, 5 datasets, 0.5–2% prevalence | 94–100% | WSS@95 46.3–89.3% | n/a | [R] |
| Evaluating human vs LLM workflows, 2026 ([arXiv 2608.26885](https://arxiv.org/abs/2608.26885)) | GPT-5.4, Gemini 3.1, preregistered, one conceptually complex scoping review | 82–84% | keeps 42–57% of records; **two identical GPT-5.4 runs disagreed on 94 records, 29 of them eligible** | n/a | [R] |

### 2.3 Meta-analyses

- **Xie et al., medRxiv 2026-03** ([medRxiv](https://www.medrxiv.org/content/10.64898/2026.03.17.26348656v1.full)), 18 studies: title/abstract pooled **sens 0.92 (0.81–0.96), spec 0.94 (0.90–0.97)**, I² ≈ 96% for sensitivity. Few-shot/CoT prompts give 0.95 vs 0.86 without them [R].
- **Kim et al., JMAI 2025** ([JMAI](https://jmai.amegroups.org/article/view/10102/html)): pooled sens **0.812**, FPR 0.110 [R].
- **SESR-Eval, ESEM 2025** ([arXiv 2507.19027](https://arxiv.org/abs/2507.19027)): 9 LLMs, 24 SE reviews, 34,528 studies. **Between-review variation exceeds between-model variation** [R]. This is the strongest argument for your transfer-across-reviews framing.
- **LLM4SCREENLIT, Madeyski/Kitchenham/Shepperd 2026** ([arXiv 2511.12635](https://arxiv.org/html/2511.12635v2)): of 29 papers, 59% used accuracy as the primary metric, 24% gave full confusion matrices, 24% gave CIs, and only 1 used post-training-cutoff data. None of the 5 papers that claim workload savings cost the false negatives [R]. Their R1–R10 checklist is what a methods reviewer will apply to you.

**Reading [I]:**
- The "95% sens / 93% spec" headlines come from small sets with 5–12% prevalence and often tuned prompts. On large, realistic, low-prevalence sets, results fall back to your regime. Sanghera's 119,695 Cochrane records are the best like-for-like example: perfect-sensitivity ensembles saved about 40%, and GPT-4o alone lost about 10% of includes at 95% specificity.
- Your 100% recall / 29% saved sits a bit below that. Your 98% recall / 66% saved beats every single-model 98%+-recall result above, except small-set GPT-5/Gemini 2.5 figures that aren't comparable.
- No paper gives a calibrated threshold that transfers across reviews with measured per-review success. Everyone either tunes per review or reports one operating point.

---

## 3. Non-LLM baselines on SYNERGY: is 0.72 a fair ASReview number?

- **ASReview v2 paper** ([PMC12416088](https://pmc.ncbi.nlm.nih.gov/articles/PMC12416088/)):
  - ELAS-Ultra (the default; SVM + TF-IDF bigrams) was **hyperparameter-optimised with Optuna on 24 SYNERGY datasets**.
  - Mean loss: ELAS-Ultra 0.0623, ELAS-Heavy (mxbai + SVM) 0.0610, ELAS-Lang (E5 + SVM) 0.0640, v1 default NB 0.0821 [R].
  - So **the default is essentially as good as ASReview's best preset** (ELAS-Heavy gains about 2% loss). The Dory embedding presets "match or exceed" on SYNERGY per [ASReview](https://asreview.nl/ai/) [R].
- **Independent ASReview numbers on all 26 SYNERGY reviews** (AutoDiscover, [arXiv 2602.05087](https://arxiv.org/abs/2602.05087), Table 13): NB+TF-IDF WSS@95 **mean 0.626 / median 0.675**; LR+TF-IDF **mean 0.632 / median 0.716** [R]. Your 0.723 median for ELAS u4 is right in line [I].
- **Teijema et al. 2025**, 92 model combinations on SYNERGY ([IJDSA](https://link.springer.com/article/10.1007/s41060-025-00777-0), [PDF](https://research-portal.uu.nl/ws/portalfiles/portal/274259840/s41060-025-00777-0_1_.pdf)): variance across datasets dominates variance across models. No single model wins everywhere [R].
- A 2026 health-technology simulation reports SVM + TF-IDF bigrams at **average WSS@95 0.70 (95% CI 0.59–0.79)** ([ScienceDirect](https://www.sciencedirect.com/science/article/pii/S138650562600256X), as quoted in search results; I didn't open the full text) [R].

**Reading [I]:**
- ASReview 0.72 is a fair, near-best number for ASReview. Beating it zero-shot is meaningful, because ASReview gets human labels during screening and Jev gets none.
- Two caveats cut in opposite directions:
  - (a) ELAS-Ultra was **tuned on SYNERGY**, likely including some of your test reviews. That is leakage in the baseline's favour.
  - (b) 3 seeds × 1+1 priors is thin. The ASReview team uses 10 prior sets per dataset (v2 paper). Your baseline variance is under-estimated.
- The fair "strongest baseline" set to add: ELAS-Heavy (Dory/mxbai), LGAR-style LLM ranking, BM25 on criteria.

---

## 4. Calibration and stopping: is a transferable threshold a contribution?

**State of the art:**
- **Statistical stopping for active learning:**
  - Callaghan & Müller-Hansen 2020 hypergeometric test.
  - SAFE heuristic (Boetje & van de Schoot, Syst Rev 2024).
  - Point-process stopping (Stevenson & Bin-Hezam, TOIS 2024).
  - The call for robust, evaluated stopping criteria ([Syst Rev 2024](https://link.springer.com/article/10.1186/s13643-024-02699-7)).
  - SIGIR 2026 confidence-based ([arXiv 2606.15380](https://arxiv.org/html/2606.15380)) and decision-theoretic stopping ([arXiv 2606.07071](https://arxiv.org/html/2606.07071)) [R].
  - None of these use LLM probabilities as the ranking [R/I].
- **LLM calibration:**
  - Rahgozar & Mortezaagha 2026 ([arXiv 2608.14551](https://arxiv.org/abs/2608.14551)): instruction-tuned LLMs "lack adequate uncertainty calibration" and "cannot self-triage" (22% escalated, never revised) [R].
  - OLIVER ([arXiv 2512.20022](https://arxiv.org/abs/2512.20022)): single-model LLM screeners are consistently poorly calibrated; an actor-critic pair reduces calibration error [R].
  - Wang et al. 2024: a transferred score threshold reaches target recall in only about half of topics [R].
- **MetaScreener:** several repos use the name ([ChaokunHong/MetaScreener](https://github.com/ChaokunHong/MetaScreener), [metascreener.net](https://www.metascreener.net/llm_config), [Zenodo desktop app](https://zenodo.org/records/20126814)). They advertise "continuous calibration" and "adaptive thresholds", but I found no published recall-guarantee evaluation [R/I].
- **Conformal prediction for screening:** conformal risk control ([arXiv 2208.02814](https://arxiv.org/pdf/2208.02814)) is the right tool: control expected FNR with a threshold fitted on calibration reviews. I found **no screening paper applying it across reviews** [I, from searches].

**Is your result a contribution? Yes, with limits [I]:**
1. You get **23/23 success at the 100% target** versus Wang's ≈50% success at a 95% target. That is qualitatively different, and it supports the claim that Jev's scores are comparable across reviews. Uncalibrated LLM scores do not transfer like this.
2. But it is **one threshold, one split, n = 23 reviews**. The same frozen procedure **missed** at t = 0.26 (93% vs a 95% target), so the threshold-to-recall mapping does not transfer precisely. Only the very conservative end holds.
3. **The big lever is the gap between 29% (safe, transferable) and 81% (oracle WSS@100).** Close it without labels, or with a small labelled sample per review, while keeping a stated guarantee, and you have a real method paper. Candidates:
   - Conformal risk control on the train reviews at review level, with the FNR target and bound stated.
   - Jev ranking plus a statistical stopping rule (Callaghan/Müller-Hansen, SAFE) applied to the Jev order: a human screens top-down and stops when the test certifies 95% recall.
   - Per-review adaptive thresholds from score quantiles.

---

## 5. Competitors built on Jev (checked on GitHub 2026-09-27)

| Repo | What | Numbers | Quality / activity | Tag |
|---|---|---|---|---|
| [Saeedabdf/jev-screening-benchmark](https://github.com/Saeedabdf/jev-screening-benchmark) | Jev `choice` include/exclude/uncertain on Cohen 2006, abstract-stage labels, vs GLM-5.3-flash and Sonnet | 15 classes, 16,015 records: **recall 90.0%, spec 44.0%**. On 999 records: Jev 91.2/31.7 vs Sonnet 90.3/28.1. About $0.03 per 1k records | 1 commit, 1 star, created 2026-09-21. Weak design: a choice question plus a confidence recode, no ranking metrics, no held-out threshold | [R] |
| [Eliot5566/JEV-Paper-Radar](https://github.com/Eliot5566/JEV-Paper-Radar) | Daily arXiv radar with a **screening mode**: one Noul per criterion, geometric mean; `calibrate` fits thresholds to your labels | CLEF TAR 2019: 4 held-out reviews, 19,447 records, **96.9% recall, 78% pooled work saved, $0.60**. The 8 dev reviews did much worse (38–48% pooled). The README admits **thresholds are fitted on the same judgments they are scored against** | 27 commits, 16 stars, very active (created 2026-09-23). Honest README with a preregistration file. The closest competitor in spirit | [R] |
| [choxos/jev-reviewer](https://github.com/choxos/jev-reviewer) | **Data extraction** plus RoB 2/ROBINS-I/QUADAS-2 templates with verbatim quotes; has dedup and a screening-comparison sheet | No screening benchmark | 53 commits, 35 stars, created 2026-09-18. Adjacent (downstream stage), not a screening competitor | [R] |

**TypeSafe/Jevals facts:**
- Price US$0.042/Mtok, input only ([models](https://docs.typesafe.ai/models.md)).
- English is the primary language, other languages "not equally well".
- Known jaggedness: literalness, weak numeric reasoning, double negatives, context rot ([jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md)).
- **No screening or medical cookbook** in the [docs index](https://docs.typesafe.ai/llms.txt).
- Jevals (release 2026-09-18): PubMedQA Decision Score **Jev 69.0 vs Gemini 3.8 Flash 73.0** (ties on CI), Jev $0.029 per 1k decisions ([jevals-data](https://github.com/Jevals/jevals-data)).
- MedHallu: Jev 92.9% vs about 95% for GPT-5.6 Luna and Gemini 3.5 Flash Lite (significant); Jev about $0.03 vs $0.23–1.03 per 1k checks ([stperic/jev-medhallu-benchmark](https://github.com/stperic/jev-medhallu-benchmark)).

**Reading [I]:** none of the three uses a frozen train→test threshold on a standard split, and none reports ranking vs ASReview. Your protocol is clearly stronger than both screening benchmarks. Paper-Radar is the one to watch: it already has the CLI, criteria files and preregistration culture, and could add your protocol in a week.

---

## 6. Holes a reviewer will attack, and fixes

| # | Hole | Why it matters | Fix |
|---|---|---|---|
| 1 | **Labels = final inclusion (after full text)**, not abstract-stage | 100% recall on final includes is easier than on title/abstract includes, and "specificity" is understated because abstract-passes that fail at full text count as false positives. SYNERGY only has `label_included` ([README](https://github.com/asreview/synergy-dataset)). Defensible (Sanghera also uses final labels), but must be stated | Add **CLEF TAR 2017–2019** (abstract-level and content-level qrels) and **Cohen 2006** (both label levels). That also allows direct comparison with Wang, LGAR (TAR2019 WSS@95 71.2), Paper-Radar and Saeedabdf |
| 2 | **SYNERGY+ keeps only OA works with an abstract ≥20 words and drops reviews with <5 includes** ([synergy-dataset-py](https://github.com/asreview/synergy-dataset-py)) | Real searches have many no-abstract records (Paper-Radar measured 13/40 new PubMed records). Work saved is overstated for real use | Report the policy (no abstract → human pile) and recompute "work saved over all retrieved records" |
| 3 | **t = 0.26 missed its 95% target** | Shows the threshold-to-recall mapping is not calibrated across reviews | Report per-review recall distribution and **success rate** (share of reviews ≥ target) for each threshold. Add conformal risk control or a bootstrap over train reviews to pick thresholds with a stated confidence |
| 4 | n = 23 reviews, one split | 0/23 failures still allows about 12% per-review failure (95%) | Cross-validate over all SYNERGY+ reviews (leave-one-review-out or repeated train/test splits). Report CIs |
| 5 | Medians only | LGAR and others report macro means. Medians hide the bad tail, which is where safety lives | Report mean, median, min and a per-review table. Add nWSS/TNR@95 (Kusa) and MAP |
| 6 | **ASReview baseline thin**: default only, 3 seeds, 1+1 priors | The ASReview team uses 10 prior sets. ELAS-Heavy is marginally better. The baseline was **tuned on SYNERGY** (leakage in its favour, which is worth stating) | Run 10+ seeds, add ELAS-Heavy/Dory, and report Wilcoxon plus effect size, not only win counts |
| 7 | **No LLM baseline** | The field's question is "why not GPT-4o-mini / Gemini Flash / Llama-70B?" | Same prompt/criteria with 1–2 cheap LLMs (gpt-4o-mini or current nano/flash-lite; a local Llama/Qwen 8–70B), logprob-based scores, same frozen-threshold protocol. Report cost per record next to Jev |
| 8 | **Data contamination** | SYNERGY has been public (CC0, GitHub, OpenAlex) since 2023, and Jev's training data is undisclosed. LLM4SCREENLIT R8 asks for a leakage statement and temporal safeguards | Add a **temporal hold-out**: reviews published after Jev 1.13's release (for example Cochrane 2026 issues rebuilt from their searches), or at least a statement plus a "criteria-perturbation" check |
| 9 | English-only, mostly medicine/psychology | Jev docs say non-English is weaker | Scope the claim. Optionally test a multilingual SYNERGY subset |
| 10 | Model versioning and determinism | `jev-latest` moves. LLM run-to-run disagreement is documented (29 eligible studies flipped between identical GPT-5.4 runs) | Pin `jev-1.13.0`, rerun twice, report the flip rate |
| 11 | Criteria-writing freedom | Results depend on how criteria are phrased (Delgado-Chaves PNAS 2025; Paper-Radar's 10% → 0.1% after splitting criteria). Who wrote the question, and was it tuned on test? | Use the dataset's own `eligibility_criteria` verbatim with one fixed template. Publish it. Do a sensitivity run with a paraphrase |
| 12 | Reporting standards | LLM4SCREENLIT R1/R4 | Full confusion matrices per review, MCC or WMCC, lost evidence per review, the missed studies by ID |

**Minimum for a credible preprint (arXiv cs.IR / medRxiv, or a short paper at SIGIR/ECIR/CLEF or Research Synthesis Methods) [I]:**
1. Leave-one-review-out or repeated splits on SYNERGY+.
2. CLEF TAR 2019 test split, for direct comparison with LGAR and Wang.
3. One cheap-LLM baseline and a stronger ASReview baseline (10 seeds, ELAS-Heavy).
4. Per-review success rate and CIs.
5. One guarantee method: conformal risk control, or Jev order plus a stopping rule.
6. A contamination statement.

About 1–2 weeks of work at Jev's cost (well under US$20 of API) [I].

---

## 7. Honest verdict

- **How good relative to the field [I]:**
  - Ranking: top tier for a zero-shot method on SYNERGY-type data, and better than ASReview's default in most reviews without any labels.
  - Classification: middle of the pack. Frontier LLMs have much higher specificity at similar recall on smaller sets.
  - Cost: excellent versus frontier models (≈50–100× cheaper than GPT-4o per record), but only modestly cheaper than mini/flash models (about 2×) or free local 8B models.
- **What is genuinely new [I]:**
  - (1) Among the first results on the SYNERGY+ v3 official split (released 2026-08-27).
  - (2) A **train-frozen threshold that transferred to unseen reviews with zero lost includes in 23/23**. Published calibrated zero-shot thresholds hit target in about 50% of topics.
  - (3) A no-label ranker that beats a label-using active learner in about 80% of reviews at about $0.05 per 1k records.
- **What is not new:** LLM screening per se, recall-first thresholds, cheap-model screening (gpt-4o-mini tools already report $0.00008 per record).
- **Safest claim (copy-ready):**

```
On the SYNERGY+ v3 test split (23 reviews, 33,001 records, 597 final includes), a Jev score threshold chosen on the 20 training reviews and frozen before testing retained every included study in all 23 test reviews while removing 29% of records from manual screening. Used as a ranker without any labelled examples, the same scores achieved a median WSS@95 of 0.76, versus 0.72 for ASReview's default active-learning model, and matched or beat ASReview in 19 of 23 reviews, at roughly US$0.05 per 1,000 records. Recall is measured against final (full-text) inclusion decisions on records with abstracts; the zero-miss result is compatible with up to ~12% of future reviews losing at least one include (95% bound).
```

- **Do not claim:** "guaranteed/calibrated recall", "better than LLMs", "replaces a human screener", or superiority over LGAR/SOTA until mean-based and same-dataset comparisons are done.
