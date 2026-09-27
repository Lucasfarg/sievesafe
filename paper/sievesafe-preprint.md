<!-- Draft for medRxiv. Every number comes from benchmark/results.md in the sievesafe repository (external validation: benchmark/external/results*.md).
     [[…]] marks what the author must fill before submission. References were checked against their sources on
     2026-09-27. -->

# A pre-specified exclusion threshold for zero-shot title and abstract screening: development on SYNERGY+ and external validation on CLEF TAR

Lucas Farias, Independent researcher, Caruaru, Pernambuco, Brazil · lucasfg.dev@gmail.com · ORCID 0009-0008-2666-766X (https://orcid.org/0009-0008-2666-766X)

## Abstract

**Background.** Screening tools can save reviewers a great deal of work, but letting a tool exclude records on its own
is only acceptable if it does not lose relevant studies. Most published evaluations of language-model screeners report
pooled sensitivity, often with thresholds chosen on the same reviews used to evaluate them.

**Methods.** For each record we asked a probabilistic language model (TypeSafe Jev, version jev-1.13.0) a single
zero-shot question: should this record go on to full-text review, given the review's title and eligibility criteria?
No labelled examples were used. We fixed an exclusion threshold on 20 reviews from SYNERGY+ v3 and applied it, unchanged,
to the 23 reviews in the dataset's test split (33,001 records, 597 finally included studies). We report recall per
review, the share of records below the threshold, leave-one-review-out stability over 43 reviews, agreement with human
title and abstract decisions, a comparison with ASReview 3.0.8, and run-to-run stability. We then tested the same
threshold on CLEF TAR, with each analysis plan committed to the project's git repository before any model call: 20 intervention and 8 diagnostic test accuracy Cochrane reviews from
2019, the intervention reviews a second time with only their objectives as criteria, and a random half (40) of the
2017–2018 reviews. Code, model answers and the frozen threshold are public.

**Results.** At the frozen threshold of 0.06, no finally included study fell below the threshold in any of the 23 test
reviews, while 29% of all records did (24% on average per review). In leave-one-review-out analysis the threshold ranged
from 0.06 to 0.08 and kept at least 98% of included studies in 43 of 43 reviews, and all of them in 42. Compared with
human title and abstract decisions (12 reviews), it kept 96% of the records humans passed on average (lowest 78%), and
none of the records it dropped was finally included. As a ranking, median work saved at 95% recall (WSS@95) was 0.758,
against 0.723 for ASReview started with one labelled record of each class; at 100% recall the figures were 0.791 and
0.711. Scores were stable between runs (correlation 0.996), and screening cost US$ 0.000047 per record. In the 26 CLEF
2019 reviews with included studies, none of the 510 intervention or 250 diagnostic studies fell below the threshold,
with 52% and 45% of records below it; with objectives alone there were again no losses, and 34% of records fell below.
In the 2017–2018 half, 848 of 849 included studies were kept (49% of records below). That set failed its pre-specified rule; the one study
lost may be a labelling error, which we could not confirm.

**Conclusions.** A threshold fixed in advance on a zero-shot probability carried over to 23 unseen SYNERGY+ reviews and
to three of four pre-specified CLEF TAR sets; the fourth failed its rule by one included study out of 849. Across 88
test reviews with included studies it lost that one study, while flagging between 29% and 52% of records. Vaguer criteria led the model to flag fewer records rather than to miss more studies.
The threshold is stricter than human title and abstract screening, not a replacement for it, and should be checked
locally before it is relied on. We release it as an open-source tool, sievesafe.

## Introduction

Screening titles and abstracts is one of the slowest parts of a systematic review. Machine learning has long been used
to *prioritise* records so that reviewers meet the relevant ones sooner, and active-learning tools such as ASReview [2]
learn from each decision as screening goes on. Having a tool *remove* records is harder to justify. The joint position
statement of Cochrane, the Campbell Collaboration, JBI and the Collaboration for Environmental Evidence, which endorses
the RAISE recommendations, accepts AI in evidence synthesis when authors can show that it does not compromise
methodological rigour, with human oversight and full reporting of the tool, its version, its validation and its
limitations [5, 6]. In practice the bar for automated exclusion is set review by review rather than on average.
Covidence, for example, set a minimum recall of 98% and withheld a classifier whose recall averaged 98.6% but fell as
low as 65.7% in individual reviews [7].

Language models can now screen from the eligibility criteria alone, and a growing number of studies report their
sensitivity and specificity [10, 12, 13]. Two things are usually missing before exclusion can be automated: a threshold
fixed before the evaluation data are seen, and evidence that it holds in each review and not only in the pooled data.
We report both for one model on public benchmarks, and all results can be regenerated from the repository.

## Methods

### Data

We used SYNERGY+ v3 [3], a collection of 114 systematic reviews with their search results and screening decisions,
downloaded with `synergy-dataset` 2.2. The dataset assigns 23 reviews to a test split. Labels are the final (full-text)
inclusion decisions, and 12 of the test reviews also publish the title and abstract decision. Every test record has an
abstract. The reviews come from medicine, software engineering and other fields, and according to the dataset's
metadata most restricted their searches to English-language publications.

### Model and question

Each record was scored with one request to TypeSafe Jev, a model that returns a probability for a yes/no question
(a "Noul") instead of generating text. The input held the review's title, its `eligibility_criteria` text as
distributed with SYNERGY+, and the record's title and abstract. The question asked whether the record should move on to
full-text review. A short policy told the model that a record should pass whenever it could meet every inclusion
criterion, including when the title and abstract do not say enough to tell, and that missing a relevant study is far
worse than reading an extra one. We used no labelled examples, no fine-tuning and no prompt changes between reviews;
the exact question is in the repository (`src/sievesafe/jev.py`). Test and calibration answers were requested in
September 2026 under the model alias `jev-latest`. The stability run, the external validation and the released tool
pin `jev-1.13.0`, the version current at the time; the stability analysis compares the two.

### Calibration

We scored 20 reviews from the SYNERGY+ train split, capped at 1,000 records each (all included studies plus a seeded
random sample of the rest, weighted back to the size of the review), for a total of 12,982 records and 818 included
studies. For recall targets of 95%, 98% and 100%, the threshold was the highest probability that kept that share of the
pooled included studies. The thresholds were saved to a file with a timestamp and the SHA-256 hash of the answers used,
before any test answer was compared with its label. That order is attested by the timestamp in the file, not by the git
history, which starts later.

After the evaluation we found a flaw in the calibration script. It looked scores up by record identifier across all 20
reviews, so 298 records that appear in two reviews (24 of them included studies) took the score that had been asked for
the other review. The released code reproduces the frozen file exactly with the original lookup, and it also implements
the corrected procedure. We kept the frozen thresholds as the pre-specified ones and report the test split at the
corrected 100% threshold as well (Table 1).

### Evaluation

For the 23 test reviews we report, per review and pooled, the recall of finally included studies at each threshold
(the share scoring at or above it) and the share of records below it, which is what exclude mode would remove. For
ranking we report the area under the ROC curve and work saved over sampling (WSS@95 and WSS@100): the share of records a
reviewer does not need to read, going down the ranked list, once 95% or 100% of the included studies have been found,
minus 0.05 or 0 [4]. Scores have two decimals, so ties are common; we broke them pessimistically, placing included
studies after the other records with the same score.

*Leave-one-review-out.* To see how much the threshold depends on the reviews used to set it, we held out each of the 43
answered reviews (23 test and 20 calibration) in turn, recalibrated on the other 42, and applied the result to the
held-out review. We report a one-sided 95% Clopper–Pearson upper bound [9] on the share of reviews that would lose at
least one included study. The folds share 41 of their 42 calibration reviews, so they are not independent, and the bound
should be read as approximate.

*Title and abstract decisions.* In the 12 test reviews that publish them, we measured the share of records passed to
full text by humans that score at or above the threshold, and checked whether any record lost this way was finally
included.

*ASReview.* We ran ASReview 3.0.8 simulations with its default model, one included and one excluded prior record and
seeds 1 to 3, each until every included study had been found, averaged WSS over the seeds and compared it with the
single zero-shot ranking.

*Stopping rules.* We compared reading every record above the threshold with the knee method [8] (at least 150 records
read, slope ratio of at least 6, 10% margin) on the same ranking.

*Stability.* We asked the model again about 2,000 randomly drawn test records, with the version pinned, and counted how
many scores crossed each threshold.

### External validation (pre-specified)

After the SYNERGY+ results we tested the frozen thresholds on CLEF TAR 2019 Task 2 [11], first on the Intervention test
topics: 20 Cochrane reviews and 41,996 records, with final (content-level) and title and abstract (abstract-level)
labels. The plan, including the success rule (at 0.06, every review with a final include keeps at least 98% of them,
with no retuning), was committed to the project's git repository before any record was sent to the model (`benchmark/external/PLAN.md`).
The plans were not lodged in a public registry, so their timing rests on the local git history.
The criteria were the OBJECTIVES and SELECTION CRITERIA sections of each review's abstract, taken from the latest
version published up to 2019, and records were retrieved from PubMed. For each review we kept every record included at
either level and a seeded random sample of the others up to 1,000 records, weighted back to the size of the review.

Three more conditions were specified in the same way, each before any call was made. In the second, the model saw only
the OBJECTIVES section, on every included record plus the first 300 other records of the same sample, so that every
record was scored under both conditions. The third applied the full criteria to the 8 diagnostic test accuracy (DTA)
test topics of the same task (30,521 records), with every included record and 300 others per review. The fourth used a
seeded random half (40) of the 79 CLEF TAR 2017–2018 [14, 15] topics not used above, with criteria from the latest
version of each review published up to the year of that CLEF edition, and every final include plus 200 other records
per review; title and abstract labels were not kept whole there, so we do not report their recall. As in the tool,
records without an abstract were never counted below the threshold, and the scores alone gave the same recall.

### Reporting

Reporting was informed by the TRIPOD-LLM guideline for studies using large language models [16], where its items apply
to a retrospective evaluation of a screening classifier [[attach the completed TRIPOD-LLM checklist as a supplementary file]], and the RAISE recommendations on reporting AI use in evidence
synthesis [6].

### Software and availability

sievesafe [[repository URL]] reads RIS, PubMed/MEDLINE, Web of Science and CSV exports, writes the results back in the
same format, and produces a report with the count for the PRISMA 2020 flow diagram [1] and a draft methods paragraph.
It never excludes records without an abstract, since the threshold was only validated on records that had one. The
`benchmark/` directory holds the scripts, the model answers (identifiers and probabilities only, without record text),
the frozen calibration and a manifest of the data, and `benchmark/results.py` regenerates every number in this paper.

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

At the frozen safe threshold, no finally included study fell below it in any review. The two looser thresholds met
their own target as a per-review floor in only 15 (95%) and 18 (98%) of the 23 reviews, and the corrected safe threshold
would have lost one included study in one review. The pooled AUC was 0.938; per review, the median AUC was 0.966 and
the median WSS@95 was 0.758.

### Leave-one-review-out

**Table 2. Threshold recalibrated on 42 reviews and applied to the remaining one, for each of 43 reviews.**

| recall target | threshold range (median) | reviews with 100% recall | reviews with ≥98% recall | 95% upper bound on reviews losing any include | mean recall (lowest) | mean records below (median) |
|:--|--:|--:|--:|--:|--:|--:|
| 100% | 0.06–0.08 (0.06) | 42/43 | 43/43 | 11% | 100.0% (99%) | 26% (18%) |
| 98% | 0.18–0.20 (0.18) | 32/43 | 34/43 | 39% | 97.8% (80%) | 60% (64%) |
| 95% | 0.23–0.28 (0.25) | 27/43 | 29/43 | 51% | 95.5% (63%) | 68% (72%) |

Only the 100% target kept at least 98% of the included studies in every review, and its threshold changed little
from one calibration set to another.

### Title and abstract decisions

In the 12 test reviews with published title and abstract decisions, the safe threshold kept on average 96% of the
records that humans passed to full text (lowest 78%). All 33 records it dropped were later excluded at full text. At the
corrected threshold the figures were 94% (lowest 72%).

### Comparison with ASReview

**Table 3. Work saved on the 23 test reviews (median over reviews).**

| | Jev, zero-shot, no labels | ASReview 3.0.8, default model, 1+1 priors |
|:--|--:|--:|
| WSS@95 | 0.758 | 0.723 |
| WSS@100 | 0.791 | 0.711 |

The zero-shot ranking saved as much work as ASReview, or more, in 18 of 23 reviews at 95% recall and in 18 of 23 at
100%.

### Stopping rules

Reading every record above the safe threshold found all included studies in 23 of 23 reviews and left 24% of records
unread on average (median 18%). The knee method left more records unread (mean 64%, median 70%), but its recall dropped
to 83.3% in the worst review and was complete in only 13 of 23. Combining the two did not help (13 of 23).

### Stability and cost

Across the 2,000 records asked twice, the correlation between runs was 0.996, the mean absolute change 0.011 and the
largest change 0.14. Sixty-three records (3.1%) crossed the safe threshold between runs, and none of them was an
included study. The test split took 33,001 requests, with 1,117 input tokens per record on average, at a total cost of
US$ 1.55 (US$ 0.000047 per record) and a median of 410 ms per request.

### External validation

**Table 4. CLEF TAR Cochrane reviews at the frozen threshold of 0.06: the 2019 intervention reviews (18 with a final
include, 510 finally included studies) under two sets of criteria, the 2019 DTA reviews (250 finally included studies)
and a random half of the 2017–2018 reviews (39 with a final include, 849 finally included studies).**

| | 2019 intervention, objectives and selection criteria | 2019 intervention, objectives only | 2019 DTA, objectives and selection criteria | 2017–2018 half, objectives and selection criteria |
|:--|--:|--:|--:|--:|
| reviews keeping every final include | 18/18 | 18/18 | 8/8 | 38/39 |
| final includes kept | 510 of 510 | 510 of 510 | 250 of 250 | 848 of 849 |
| records below the threshold (pooled, weighted) | 52% | 34% | 45% | 49% |
| records below the threshold (mean per review) | 42% | 19% | 30% | 33% |
| title/abstract includes kept (pooled; lowest review) | 99.7%; 96% | 100.0%; 100% | 99.1%; 94% | not measured |
| median WSS@95 / WSS@100 (weighted) | 0.888 / 0.936 | 0.855 / 0.883 | 0.731 / 0.650 | 0.884 / 0.931 |
| 95% upper bound on reviews losing any include | 15% | 15% | 31% | 12% |

The three CLEF 2019 sets met the pre-specified rule and the 2017–2018 half did not. In that set, the review *Blood CEA
levels for detecting recurrent colorectal cancer* (CD011134) kept 48 of its 49 final includes, which rounds to 98.0% but
is 97.96%, just under the 98% floor. The record it lost (PMID 16649724, score 0.02) is a study of NT-proBNP in
hypertrophic cardiomyopathy and may be a wrong identifier in the CLEF labels. We did not check it against the
review's reference list, and we report the set as a failure, as planned.

With full criteria on the 2019 intervention reviews, the corrected SYNERGY+ threshold (0.08) would have lost included
studies in 2 of 18 reviews (lowest 97%). On the 6,237 records scored under both sets of criteria, the scores correlated
at 0.874. With objectives alone, the mean score rose from 0.208 to 0.286 and the share of records below 0.06 fell from
38% to 18% (unweighted), and no final include moved from above the threshold to below it. The DTA reviews were ranked
less well than the intervention reviews (median AUC 0.937 against 0.984), yet the safe threshold still kept every
include. The four conditions cost US$ 0.595 (13,637 requests), US$ 0.244 (6,237 requests), US$ 0.114 (2,626 requests)
and US$ 0.365 (8,738 requests).

## Discussion

A threshold on a zero-shot probability, fixed on 20 reviews, flagged 29% of the records in 23 unseen reviews without
losing any study they finally included, and behaved much the same when each of 43 reviews was held out in turn. The
looser thresholds flagged many more records but fell below a per-review floor in several reviews. For that reason the
released tool offers only the safe threshold for automated exclusion and uses the scores otherwise for ranking.

The safe threshold does not replace human screening. It kept 96% of the records humans passed at the title and abstract
stage, so it drops some records that a person would have read, even though in this benchmark all of them were excluded
later at full text. It supports only a narrower claim: the records it removes rarely included studies that ended up in the
review in these benchmarks.

Used only as a ranking, with no labels at all, the model did as well as or better than an active-learning baseline
that starts from two labelled records, in most reviews. Published zero-shot results on the original SYNERGY reviews,
such as LGAR's WSS@95 of 0.652 macro-averaged over 26 reviews [10], are not directly comparable, because the review set
and the way results are averaged differ.

We see the external validation as the stronger evidence. The reviews, the wording of the criteria and the records all
came from a different source, and the success rule was written down before any record was scored. Of the 65 CLEF
reviews with included studies, one lost a study, which may be mislabelled. The objectives-only
condition also suggests how the method behaves with vaguer criteria: the model became more permissive and flagged fewer
records, but it did not start missing included studies. In this single comparison, fuller criteria mainly increased the share of records flagged.

## Limitations

- **Two collections and one failure.** We tested 23 SYNERGY+ reviews and 65 CLEF TAR reviews with included studies. One
  CLEF review lost one included study, possibly because of a labelling error that we did not confirm. Per set, the 95% upper bound on the share
  of reviews that could lose an included study is between 12% and 31%, and only half of the CLEF 2017–2018 topics were
  used. The criteria came from published reviews; the objectives-only condition is a single test of vaguer criteria,
  and a prospective study is still needed.
- **Sampling in the external validation.** Records that were not included were sampled and weighted, so the shares of
  records below the threshold are estimates there. Recall is exact, since every included study was scored.
- **Pre-specification.** The thresholds were fixed before the test answers were compared with labels, but the
  calibration script had the flaw described above, and the corrected procedure would have lost one included study. The
  external plans were committed to git before the model calls but not lodged in a public registry.
- **Leave-one-review-out.** At the 100% target one included study was lost in one of 43 reviews; the upper bound on the
  share of reviews that could lose one is 11%.
- **Language and abstracts.** Most reviews restricted their searches to English and all records had abstracts. The tool
  never excludes records without an abstract, and other languages have not been tested.
- **A proprietary model.** The scores come from a closed, paid model. The tool pins the version the threshold was
  calibrated on, and a new version would need a new calibration. The test answers were requested under a model alias,
  and we report their stability against the pinned version.
- **Title and abstract stage only.** Final labels were the reference standard, so a record excluded at full text for
  reasons not visible in its abstract counts as correctly removed.

## Ethics statement

Not applicable. The study used only public bibliographic records (titles and abstracts) and published screening
decisions from the SYNERGY+ and CLEF TAR datasets, and it involved no human participants, patient data or
interventions.

## Use of AI tools

The software, the analysis scripts and the first draft of this manuscript were written with the help of an AI coding
assistant (Claude, Anthropic), under the author's direction. The author designed the study, reviewed all code, numbers
and text, and takes full responsibility for the content. Every number in the manuscript is produced by the released
scripts. The model evaluated in the study (TypeSafe Jev) is a different system from the assistant.

## Author contributions

LF is the sole author and was responsible for conceptualisation, methodology, software, analysis and writing, and paid
for the model calls.

## Data and code availability

SYNERGY+ v3: DataverseNL, doi:10.34894/DDCVCV (CC0 1.0). CLEF TAR: github.com/CLEF-TAR/tar (commit dbc13d0, MIT
licence). The repository redistributes only record identifiers, model probabilities and token counts, not record text. Code, model answers,
the frozen calibration and the generated tables: [[repository URL, release tag and archive DOI]], AGPL-3.0-or-later.

## Competing interests

The author declares no competing interests. The author has no relationship with TypeSafe and received no payments or
services from any third party for any aspect of this work in the past 36 months. The model was used through its public,
paid API, at the author's expense.

## Funding

This work received no specific funding.

## References

1. Page MJ, McKenzie JE, Bossuyt PM, et al. The PRISMA 2020 statement: an updated guideline for reporting systematic reviews. BMJ 2021;372:n71.
2. van de Schoot R, de Bruin J, Schram R, et al. An open source machine learning framework for efficient and transparent systematic reviews. Nat Mach Intell 2021;3:125–133. doi:10.1038/s42256-020-00287-7.
3. Westerbeek E, van der Kuil T, de Bruin J, Neeleman R, van de Schoot R. SYNERGY+, version 3.0. DataverseNL, 2026. doi:10.34894/DDCVCV.
4. Cohen AM, Hersh WR, Peterson K, Yen PY. Reducing workload in systematic review preparation using automated citation classification. J Am Med Inform Assoc 2006;13(2):206–219. doi:10.1197/jamia.M1929.
5. Flemyng E, Noel-Storr A, Macura B, et al. Position statement on artificial intelligence (AI) use in evidence synthesis across Cochrane, the Campbell Collaboration, JBI and the Collaboration for Environmental Evidence 2025. Campbell Syst Rev 2025;21(4):e70074. doi:10.1002/cl2.70074 (also published in the Cochrane Database of Systematic Reviews, ED000178, and Environmental Evidence).
6. Thomas J, Flemyng E, Noel-Storr A, et al. Responsible use of AI in evidence SynthEsis (RAISE): recommendations and guidance. Open Science Framework, 2025. doi:10.17605/OSF.IO/FWAUD.
7. Covidence. Beyond evaluation: deciding when AI is appropriate in evidence synthesis. n.d. https://www.covidence.org/blog/beyond-evaluation-deciding-when-ai-is-appropriate-in-evidence-synthesis/ (accessed 27 September 2026).
8. Cormack GV, Grossman MR. Engineering quality and reliability in technology-assisted review. Proc SIGIR 2016:75–84.
9. Clopper CJ, Pearson ES. The use of confidence or fiducial limits illustrated in the case of the binomial. Biometrika 1934;26(4):404–413.
10. Jaumann C, Wiedholz A, Friedrich A. LGAR: zero-shot LLM-guided neural ranking for abstract screening in systematic literature reviews. In: Findings of the Association for Computational Linguistics: ACL 2025, pp. 7910–7927. doi:10.18653/v1/2025.findings-acl.412.
11. Kanoulas E, Li D, Azzopardi L, Spijker R. CLEF 2019 technology assisted reviews in empirical medicine overview. CEUR Workshop Proceedings 2019;2380.
12. Sanghera R, Thirunavukarasu AJ, et al. High-performance automated abstract screening with large language model ensembles. J Am Med Inform Assoc 2025;32(5):893–904. doi:10.1093/jamia/ocaf050.
13. Oami T, Okada Y, Nakada TA, et al. Optimal large language models to screen citations for systematic reviews. Res Synth Methods 2025;16(6):859–875. doi:10.1017/rsm.2025.10014.
14. Kanoulas E, Li D, Azzopardi L, Spijker R. CLEF 2017 technologically assisted reviews in empirical medicine overview. CEUR Workshop Proceedings 2017;1866.
15. Kanoulas E, Li D, Azzopardi L, Spijker R. CLEF 2018 technologically assisted reviews in empirical medicine overview. CEUR Workshop Proceedings 2018;2125.
16. Gallifant J, Afshar M, et al. The TRIPOD-LLM reporting guideline for studies using large language models. Nat Med 2025;31:60–69. doi:10.1038/s41591-024-03425-5.
