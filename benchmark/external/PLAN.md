# External validation on CLEF TAR 2019: analysis plan

Written and committed before any record of this set was sent to Jev. Nothing below is tuned on these reviews.

## Question

Does the safe threshold frozen on SYNERGY+ (0.06, `benchmark/calibration.json`) keep the included studies of reviews
from another collection, with eligibility criteria taken from the reviews' own abstracts?

## Data

CLEF TAR 2019 Task 2, Intervention test topics: 20 Cochrane reviews, 41,996 records (commit pinned in `clef_fetch.py`).
Final labels: content-level qrels; title/abstract labels: abstract-level qrels. Per review, every record included at
either level is kept, plus a seeded random sample of the other records up to 1,000 records per review, weighted back to
the review's size. Titles and abstracts come from PubMed. The criteria given to the model are the OBJECTIVES and
SELECTION CRITERIA sections of the latest version of the review published up to 2019. Two reviews have no final
include; they count only for the share of records below the threshold.

## Scoring

Exactly the question and state of `sievesafe screen` (`src/sievesafe/jev.py`), with the pinned model `jev-1.13.0`: the
review's title and criteria, and each record's title and abstract. One call per record; answers in
`benchmark/answers/clef-<topic>.jsonl.gz`. Hard budget US$ 0.95 (`external/screen.py`).

## Endpoints, fixed now

Primary, at the frozen threshold 0.06, applying the product's rule that a record without an abstract (or missing from
PubMed) is never below the threshold:

1. number of reviews (of those with at least one final include) where every final include is kept;
2. number of those reviews with at least 98% of final includes kept (the per-review floor used by Covidence);
3. pooled recall of final includes, and the weighted share of all records below the threshold.

The result counts as a **successful external validation** if 2 holds in every review. It counts as a **failure** if any
review falls below 98%; in that case the threshold is not changed on this set, and the finding is reported as is.

Secondary: the same at 0.08 (corrected SYNERGY+ calibration), 0.17 and 0.26; recall of title/abstract includes;
recall from the score alone (without the no-abstract rule); weighted WSS@95 and WSS@100; AUC.
