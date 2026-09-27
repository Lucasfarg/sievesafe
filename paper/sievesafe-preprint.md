<!-- Draft for medRxiv. Every number comes from benchmark/results.md in the sievesafe repository (external validation: benchmark/external/results*.md).
     [[…]] marks what the author must fill before submission. References were checked against their sources on
     2026-09-27. -->

# A zero-shot, pre-registered safe threshold for automated exclusion in title/abstract screening: a benchmark on 23 held-out systematic reviews

Lucas Farias, Independent researcher, Caruaru, Pernambuco, Brazil · lucasfg.dev@gmail.com · ORCID 0009-0008-2666-766X (https://orcid.org/0009-0008-2666-766X)

## Abstract

**Background.** Automated tools can reduce the work of title/abstract screening, but automated *exclusion* is accepted
only when it demonstrably does not lose relevant studies. Most published evaluations of language-model screeners report
pooled sensitivity with thresholds chosen on the same reviews they are evaluated on.

**Methods.** We asked a probabilistic language model (TypeSafe Jev, version jev-1.13.0) one zero-shot question per record,
whether it should proceed to full-text review, given the review's title and published eligibility criteria, with no
labelled examples. We froze an exclusion threshold on 20 reviews from the SYNERGY+ v3 dataset and applied it unchanged to
the 23 reviews of the dataset's test split (33,001 records, 597 finally included studies). We report per-review recall,
the share of records below the threshold, leave-one-review-out stability over 43 reviews, agreement with human
title/abstract decisions, a comparison with ASReview 3.0.8, and run-to-run stability. We then tested the threshold,
unchanged and with a pre-registered plan, on 20 intervention and 8 diagnostic test accuracy Cochrane reviews from CLEF
TAR 2019, with criteria taken from each review's abstract, on the intervention reviews again with the objectives alone,
and on a random half (40) of the CLEF TAR 2017–2018 reviews. Code, model answers and the frozen threshold are public.

**Results.** At the frozen threshold (0.06), no finally included study fell below it in any of the 23 test reviews, while
29% of all records did (24% on average per review). Recalibrating with each of 43 reviews held out in turn, the
threshold ranged from 0.06 to 0.08 and kept at least 98% of included studies in 43 of 43 reviews and all of them in 42.
Against human title/abstract decisions (12 reviews), the threshold kept 96% of the records humans passed on average
(lowest 78%); none of the records it lost was finally included. As a ranking, the median work saved at 95% recall
(WSS@95) was 0.763, against 0.723 for ASReview with its default active-learning model and one labelled record of each
class; at 100% recall, 0.808 against 0.711. Scores were stable between runs (correlation 0.996). Screening cost
US$ 0.000047 per record. In the external validation no finally included study fell below the threshold in any of the 26
CLEF 2019 reviews with includes (510 intervention and 250 diagnostic studies), with 52% and 45% of records below it;
with the objectives alone, again none, with 34% below. In the CLEF 2017–2018 half, 848 of 849 included studies were
kept (49% of records below); the one lost, in one review, is an off-topic record that appears to be a labelling error,
but under the pre-registered rule this set failed.

**Conclusions.** A threshold frozen before evaluation, on a zero-shot probability, transferred to unseen reviews and to
another collection, losing one included study in 88 test reviews with includes (an apparent labelling error), and removed 29% to
52% of their records. Vaguer criteria made it
remove fewer records, not lose more studies. It is stricter than human title/abstract
screening, not equivalent to it, and should be validated locally before use. We release it as an open-source tool,
sievesafe.

## Introduction

Screening titles and abstracts is one of the most labour-intensive steps of a systematic review. Machine-learning tools
have long been used to *prioritise* records, so that reviewers find relevant studies earlier; active-learning tools such as
ASReview [2] learn from the reviewer's decisions as screening proceeds. Removing records *automatically* is a different
matter. The joint position statement of Cochrane, the Campbell Collaboration, JBI and the Collaboration for Environmental
Evidence, which endorses the RAISE recommendations, allows AI in evidence synthesis only when authors can show it does
not compromise methodological rigour, with human oversight and full reporting of tool, version, validation and
limitations [5, 6]. In practice the bar for automated exclusion has been set per review, not on average: Covidence
set a minimum recall of 98% and withheld a classifier whose recall averaged 98.6% but fell as low as 65.7% in individual
reviews [7].

Language models can now screen from the eligibility criteria alone, without labelled examples, and a growing literature
reports their sensitivity and specificity [10, 12, 13]. Two things are usually missing for automated
exclusion: a threshold fixed before the evaluation data are seen, and evidence that it holds review by review rather
than pooled. This study provides both for one model, on a public benchmark, with everything needed to reproduce it.

## Methods

### Data

We used SYNERGY+ v3 [3], 114 systematic reviews with their search results and screening decisions, obtained with
`synergy-dataset` 2.2. The dataset assigns 23 reviews to a test split. Labels are the final (full-text) inclusion
decisions; 12 of the test reviews also publish the title/abstract decision. Every test record has an abstract. The
reviews span medicine, software engineering and other fields; according to the dataset's metadata, most restricted
their searches to English-language publications.

### Model and question

Each record was scored with one request to TypeSafe Jev, a model that returns a probability for a yes/no question
("Noul") rather than generated text. The state contained the review's title and its `eligibility_criteria` text as
distributed with SYNERGY+, and the record's title and abstract. The question asked whether the record should move on to
full-text review, with a policy stating that a record passes when it could meet every inclusion criterion, including when
the title and abstract do not say enough to tell, and that missing a relevant study is far worse than reading an extra
one. No labelled examples, fine-tuning or per-review prompt engineering were used; the exact question is in the
repository (`src/sievesafe/jev.py`). Test and calibration answers were requested with the model alias `jev-latest` in
September 2026; the stability run and the released tool pin `jev-1.13.0`.

### Calibration

Twenty reviews from SYNERGY+'s train split were scored, each capped at 1,000 records (every included study plus a
seeded random sample of excluded records, weighted back to the review's size), for 12,982 records and 818 included
studies. For recall targets of 95%, 98% and 100%, the threshold was the highest probability that kept that share of the
pooled included studies. The resulting thresholds were written to a file with a timestamp and the SHA-256 hash of the
answers used, before the test answers were compared with their labels.

After the evaluation we found a flaw in the calibration script: it looked scores up by record identifier pooled across
the 20 reviews, so 298 records (24 of them included studies) that appear in two reviews carried the score asked for the
other review. The released code reproduces the frozen file exactly with the original lookup and also implements the
corrected procedure. We keep the frozen thresholds as the pre-specified ones and report the test split at the corrected
100% threshold as well (Table 1).

### Evaluation

On the 23 test reviews we report, per review and pooled: recall of finally included studies at each threshold (the share
scoring at or above it), and the share of records below it, which exclude mode would remove. For ranking we report the
area under the ROC curve and work saved over sampling (WSS@95 and WSS@100), the share of records a reviewer does not
read, reading in score order, when 95% or 100% of included studies have been found, minus 0.05 or 0 [4].

*Leave-one-review-out.* To see how much the threshold depends on which reviews it is calibrated on, each of the 43
answered reviews (23 test, 20 calibration) was held out in turn, the threshold recalibrated on the other 42, and applied
to the held-out review. We report a one-sided 95% Clopper–Pearson upper bound [9] on the share of reviews that would lose
at least one included study.

*Title/abstract decisions.* For the 12 test reviews that publish them, we report the share of records humans passed to
full text that score at or above the threshold, and whether any record lost this way was finally included.

*ASReview.* ASReview 3.0.8 simulations with its default model, one included and one excluded prior record, seeds 1 to 3,
each run until every included study was found; WSS was averaged over seeds and compared with the single zero-shot
ranking.

*Stopping rules.* We compared reading every record above the threshold with the knee method [8] (at least 150 records
read, slope ratio ≥ 6, 10% margin) applied to the same ranking.

*Stability.* 2,000 test records drawn at random were asked again with the model version pinned, and we counted records
whose score crossed each threshold.

### External validation (pre-registered)

After the SYNERGY+ results, we tested the frozen thresholds on CLEF TAR 2019 Task 2 [11], Intervention test topics: 20
Cochrane reviews, 41,996 records, with final (content-level) and title/abstract (abstract-level) labels. The plan,
including the success rule (every review with a final include keeps at least 98% of them at 0.06; no retuning), was
committed before any record was sent to the model (`benchmark/external/PLAN.md`). Criteria were the OBJECTIVES and
SELECTION CRITERIA sections of each review's abstract (latest version published up to 2019), and records were retrieved
from PubMed. Per review, every record included at either level was kept, plus a seeded random sample of the others up to
1,000 records, weighted back to the review's size. A second condition, also registered before any call, gave the model
the OBJECTIVES section alone, on every include plus the first 300 other records of the same sample, so that each record
was scored under both conditions. A third set, registered before any call, applied the full criteria to the 8 diagnostic
test accuracy (DTA) test topics of the same task (30,521 records), with every include plus 300 other records per review.
A fourth set, registered before any call, used a seeded random half (40) of the 79 CLEF TAR 2017–2018 [14, 15] topics not used
above, with criteria from the latest review version published up to the CLEF edition's year, every final include plus
200 other records per review; title/abstract labels were not kept whole there, so their recall is not reported. As in the tool, records without an abstract were never counted below the threshold;
the scores alone gave the same recall.

### Software and availability

sievesafe [[repository URL]] reads RIS, PubMed/MEDLINE, Web of Science and CSV exports, writes results back in the same
format, and produces a report with the count for the PRISMA 2020 flow diagram [1] and a methods paragraph. Records
without an abstract are never excluded, because the threshold was validated only on records with abstracts. The
`benchmark/` directory contains the scripts, the model answers (identifiers and probabilities, no record text), the
frozen calibration and a manifest of the data; `benchmark/results.py` regenerates every number in this paper from them.

## Results

### Calibration

The frozen thresholds were 0.26, 0.17 and 0.06 for 95%, 98% and 100% train recall, with 73%, 61% and 22% of train
records below them. The corrected procedure gives 0.28, 0.19 and 0.08 (74%, 64% and 34%).

### Test split

**Table 1. The 23 test reviews (33,001 records, 597 finally included studies) at each threshold.**

| threshold | reviews with 100% recall | reviews with ≥98% recall | reviews with ≥95% recall | lowest review recall | pooled recall | records below (pooled) | records below (mean per review) |
|:--|--:|--:|--:|--:|--:|--:|--:|
| 0.26 (frozen, 95%) | 14/23 | 15/23 | 15/23 | 74% | 93.5% | 76% | 69% |
| 0.17 (frozen, 98%) | 17/23 | 18/23 | 19/23 | 83% | 98.3% | 66% | 58% |
| **0.06 (frozen, 100%)** | **23/23** | **23/23** | **23/23** | **100%** | **100.0%** | **29%** | **24%** |
| 0.08 (corrected, 100%) | 22/23 | 23/23 | 23/23 | 99% | 99.8% | 41% | 34% |

At the frozen safe threshold no finally included study fell below it in any review. The two looser thresholds met their own
target as a per-review floor in only 15 (95%) and 18 (98%) of the 23 reviews. The corrected safe threshold would have lost one
included study in one review. The pooled AUC was 0.938; per review, the median AUC was 0.966 and the median WSS@95
0.763.

### Leave-one-review-out

**Table 2. Threshold recalibrated on 42 reviews and applied to the 43rd, for each of 43 reviews.**

| recall target | threshold range (median) | reviews with 100% recall | reviews with ≥98% recall | 95% upper bound on reviews losing any include | mean recall (lowest) | mean records below (median) |
|:--|--:|--:|--:|--:|--:|--:|
| 100% | 0.06–0.08 (0.06) | 42/43 | 43/43 | 11% | 100.0% (99%) | 26% (18%) |
| 98% | 0.18–0.20 (0.18) | 32/43 | 34/43 | 39% | 97.8% (80%) | 60% (64%) |
| 95% | 0.23–0.28 (0.25) | 27/43 | 29/43 | 51% | 95.5% (63%) | 68% (72%) |

Only the 100% target met a 98% per-review floor in every review; its threshold moved little between calibration sets.

### Title/abstract decisions

In the 12 test reviews with published title/abstract decisions, the safe threshold kept 96% of the records humans
passed to full text on average (lowest 78%). The 33 records it lost were all excluded at full text. At the corrected
threshold the figures were 94% (lowest 72%).

### Comparison with ASReview

**Table 3. Work saved on the 23 test reviews (median over reviews).**

| | Jev, zero-shot, no labels | ASReview 3.0.8, default model, 1+1 priors |
|:--|--:|--:|
| WSS@95 | 0.763 | 0.723 |
| WSS@100 | 0.808 | 0.711 |

The zero-shot ranking saved as much work or more than ASReview in 19 of 23 reviews at 95% recall and 18 of 23 at 100%.

### Stopping rules

Reading every record above the safe threshold kept all included studies in 23 of 23 reviews and left 24% of records
unread on average (median 18%). The knee method left more unread (mean 64%, median 71%) but its recall fell to 83.3% in
the worst review and was complete in only 13 of 23; combining the two did not help (13 of 23).

### Stability and cost

Across 2,000 re-asked records the correlation between runs was 0.996, the mean absolute change 0.011 and the largest 0.14.
Sixty-three records (3.1%) crossed the safe threshold between runs, none of them an included study. The test split took
33,001 requests, 1,117 input tokens per record on average, US$ 1.55 in total (US$ 0.000047 per record) and a median of
410 ms per request.

### External validation

**Table 4. CLEF TAR 2019 Cochrane reviews at the frozen threshold 0.06: 20 intervention reviews (18 with a final include,
510 finally included studies) and 8 DTA reviews (250 finally included studies).**

| | 2019 intervention, objectives and selection criteria | 2019 intervention, objectives only | 2019 DTA, objectives and selection criteria | 2017–2018 half, objectives and selection criteria |
|:--|--:|--:|--:|--:|
| reviews keeping every final include | 18/18 | 18/18 | 8/8 | 38/39 |
| final includes kept | 510 of 510 | 510 of 510 | 250 of 250 | 848 of 849 |
| records below the threshold (pooled, weighted) | 52% | 34% | 45% | 49% |
| records below the threshold (mean per review) | 42% | 19% | 30% | 33% |
| title/abstract includes kept (pooled; lowest review) | 99.7%; 96% | 100.0%; 100% | 99.1%; 94% | not measured |
| median WSS@95 / WSS@100 (weighted) | 0.889 / 0.936 | 0.861 / 0.904 | 0.733 / 0.660 | 0.886 / 0.934 |
| 95% upper bound on reviews losing any include | 15% | 15% | 31% | 12% |

The three CLEF 2019 sets met the pre-registered rule; the 2017–2018 half did not. In that set one review, *Blood CEA
levels for detecting recurrent colorectal cancer* (CD011134), kept 48 of its 49 final includes (98.0% rounded; 97.96%,
below the 98% floor). The record lost (PMID 16649724, score 0.02) is a study of NT-proBNP in hypertrophic
cardiomyopathy, which appears to be a wrong identifier in the CLEF labels; we did not check it against the review's
reference list, and we report the set as a failure, as planned. With full criteria, the corrected SYNERGY+ threshold (0.08) would have lost
included studies in 2 of 18 reviews (lowest 97%). On the 6,237 records scored under both conditions, the scores
correlated at 0.874; with the objectives alone the mean score rose from 0.208 to 0.286 and the share of records below
0.06 fell from 38% to 18% (unweighted), and no final include moved from above the threshold to below it. The four
cost US$ 0.595 (13,637 requests), US$ 0.244 (6,237 requests), US$ 0.114 (2,626 requests) and US$ 0.365 (8,738 requests). The DTA reviews ranked less
well than the intervention reviews (median AUC 0.937 against 0.984), but the safe threshold still kept every include.

## Discussion

A threshold on a zero-shot probability, frozen on 20 reviews, removed 29% of the records of 23 unseen reviews without
losing any study they finally included, and behaved similarly when each of 43 reviews was held out. The looser
thresholds removed far more records but failed a per-review floor in several reviews, which is why only the safe
threshold is offered for automated exclusion in the released tool; the others remain useful only as a ranking.

The safe threshold is not a substitute for human screening. Against human title/abstract decisions it kept 96% on
average, so it excludes some records a human would have read; in this benchmark all of them were later excluded at full
text. Its claim is narrower: records it removes are unlikely to contain studies that end up in the review.

As a ranking without any labels, the model matched or exceeded an active-learning baseline that starts with two
labelled records, in most reviews. Published zero-shot results on the original SYNERGY reviews (e.g. LGAR, mean WSS@95
0.652, macro-averaged over the 26 original SYNERGY reviews [10]) are not directly comparable to ours: the review set and
the aggregation differ.

The external validation matters more than the SYNERGY+ test split, because the reviews, the criteria text and the
records came from another source, and the success rule was fixed in advance. It also shows how the threshold degrades
when criteria are vague: the model becomes more permissive, so fewer records are removed, rather than losing studies.
Better criteria buy more work saved, not more safety.

## Limitations

- **Two collections, one failure.** 23 SYNERGY+ test reviews and 65 CLEF TAR reviews with includes; one CLEF review lost
  one include, apparently through a labelling error. Per set, the 95% upper bound on the share of reviews losing an
  include is 12% to 31%; only half of the CLEF 2017–2018 topics were used. The criteria came from published reviews;
  the objectives-only condition is one test of vaguer criteria, and a prospective review is still needed.
- **Sampling in the external validation.** Non-included records were sampled and weighted, so the shares of records
  below the threshold there are estimates; recall is exact, since every include was scored.
- **Pre-specification.** The thresholds were frozen before the test answers were compared with labels, but the
  calibration script had the flaw described above; the corrected procedure would have lost one included study.
- **Leave-one-review-out** lost one included study in one of 43 reviews at the 100% target; the upper bound on the share
  of reviews that could lose one is 11%.
- **Language and abstracts.** Most reviews restricted their searches to English, and all records had abstracts; the tool never excludes records
  without an abstract, and other languages are untested.
- **A proprietary model.** Scores depend on a closed, paid model; the tool pins the version the threshold was calibrated
  on, and a new version requires recalibration. The test answers were requested under a model alias; stability against
  the pinned version is reported.
- **Title/abstract stage only**, and final labels as reference standard: a record excluded at full text for reasons not
  visible in the abstract counts as correctly removed.

## Data and code availability

SYNERGY+ v3: DataverseNL, doi:10.34894/DDCVCV. CLEF TAR 2019: github.com/CLEF-TAR/tar (commit dbc13d0). Code, model answers, frozen calibration and generated tables: [[repository
URL, release tag and archive DOI]], AGPL-3.0-or-later.

## Competing interests

The author declares no competing interests and has no relationship with TypeSafe; the model was used through its
public, paid API.

## Funding

This work received no specific funding.

## References

1. Page MJ, McKenzie JE, Bossuyt PM, et al. The PRISMA 2020 statement: an updated guideline for reporting systematic reviews. BMJ 2021;372:n71.
2. van de Schoot R, de Bruin J, Schram R, et al. An open source machine learning framework for efficient and transparent systematic reviews. Nat Mach Intell 2021;3:125–133.
3. Westerbeek E, van der Kuil T, de Bruin J, Neeleman R, van de Schoot R. SYNERGY+, version 3.0. DataverseNL, 2026. doi:10.34894/DDCVCV.
4. Cohen AM, Hersh WR, Peterson K, Yen PY. Reducing workload in systematic review preparation using automated citation classification. J Am Med Inform Assoc 2006;13(2):206–219.
5. Flemyng E, Noel-Storr A, Macura B, et al. Position statement on artificial intelligence (AI) use in evidence synthesis across Cochrane, the Campbell Collaboration, JBI and the Collaboration for Environmental Evidence 2025. Campbell Syst Rev 2025;21(4):e70074. doi:10.1002/cl2.70074 (also published in the Cochrane Database of Systematic Reviews, ED000178, and Environmental Evidence).
6. Thomas J, Flemyng E, Noel-Storr A, et al. Responsible use of AI in evidence SynthEsis (RAISE): recommendations and guidance. Open Science Framework. doi:10.17605/OSF.IO/FWAUD.
7. Covidence. Beyond evaluation: deciding when AI is appropriate in evidence synthesis. n.d. https://www.covidence.org/blog/beyond-evaluation-deciding-when-ai-is-appropriate-in-evidence-synthesis/ (accessed 27 September 2026).
8. Cormack GV, Grossman MR. Engineering quality and reliability in technology-assisted review. Proc SIGIR 2016:75–84.
9. Clopper CJ, Pearson ES. The use of confidence or fiducial limits illustrated in the case of the binomial. Biometrika 1934;26(4):404–413.
10. Jaumann C, Wiedholz A, Friedrich A. LGAR: zero-shot LLM-guided neural ranking for abstract screening in systematic literature reviews. In: Findings of the Association for Computational Linguistics: ACL 2025, pp. 7910–7927.
11. Kanoulas E, Li D, Azzopardi L, Spijker R. CLEF 2019 technology assisted reviews in empirical medicine overview. CEUR Workshop Proceedings 2019;2380.
12. Sanghera R, Thirunavukarasu AJ, et al. High-performance automated abstract screening with large language model ensembles. J Am Med Inform Assoc 2025;32(5):893–904. doi:10.1093/jamia/ocaf050.
13. Oami T, Okada Y, Nakada TA, et al. Optimal large language models to screen citations for systematic reviews. Res Synth Methods 2025;16(6):859–875. doi:10.1017/rsm.2025.10014.
14. Kanoulas E, Li D, Azzopardi L, Spijker R. CLEF 2017 technologically assisted reviews in empirical medicine overview. CEUR Workshop Proceedings 2017;1866.
15. Kanoulas E, Li D, Azzopardi L, Spijker R. CLEF 2018 technologically assisted reviews in empirical medicine overview. CEUR Workshop Proceedings 2018;2125.
