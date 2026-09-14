# The Participation Ledger

A record of how much public participation actually precedes the decisions that
commit Arizona's power and water to data centers, built from primary sources.

---

## The finding

**Arizona law requires 24 hours of notice before a public meeting.**
[A.R.S. § 38-431.02](https://www.azleg.gov/ars/38/00431-02.htm), subsection (G)
for the agenda itself. One business day. That is the legal content of the
sentence *"the public had the opportunity to comment."*

**Chandler** posted its data center agenda on 2025-12-04 and voted 2025-12-11.
Seven days, seven times the floor, apparently voluntary. In that window:

| Date | Written comments filed |
|---|--:|
| Dec 5 | 2 |
| Dec 6 | 1 |
| Dec 7 | 7 |
| Dec 8 | 6 |
| Dec 9 | 6 |
| Dec 10 | 26 |
| **Dec 11 (vote)** | **80** |

129 submissions, 124 stating a position, 118 opposed. 41 speakers. Denied 7-0.

**62% of all participation arrived on the day of the vote.** The response was
still accelerating when the decision happened.

**Marana** met the 24-hour standard exactly. From the town's own staff report
for a 611-acre rezoning drawing up to 750 MW at full build:

> all property owners within 300 feet of the rezoning area were noticed by
> United States Mail

A 300-foot mailed-notice radius. Ten neighbors attended the pre-hearing
meeting. Approved unanimously.

Nothing was concealed in either case. Every requirement was met. That is the
point: **the legal standard for opportunity is 24 hours, and the observed time
for a public to assemble a response is longer than seven days.**

---

## What this repository is

The extraction pipeline that produces those records, plus the records
themselves and the method that governs them.

```
        ┌── extract ──┐   a language model reads prose
START ──┤             ├── verify ── commit ── emit ── record
        └── count ────┘   a parser counts forms
```

Five nodes on a LangGraph `StateGraph`. `extract` and `count` fan out from the
start, read the same document, answer different questions, and rejoin at
`verify`, where the parser's exact count is used to check the model's guess.
That convergence is the reason this is a graph and not a script.

## Four design decisions worth the time

**1. Quote grounding.** Every value the model returns must arrive with the
exact sentence it came from. The code then discards any value whose quote is
not a literal substring of the source.

```python
if value is not None and (not quote or _flatten(quote) not in flat):
    value, quote = None, None          # ungrounded, so discarded
```

A model can invent a number. It cannot invent a sentence that survives a
substring check. The consequence, stated plainly: a grounded value cannot be
wrong, but it can be missed.

**2. A parser counts; a model reads.** Asking a model to count 129 repeated
form blocks is asking it to approximate. Counting is arithmetic. So `tally.py`
parses the clerk's attachment format directly with no model involved, and owns
comment counts, position splits, submission dates, and speaker counts. The
model owns prose: who moved the motion, what staff recommended, what the vote
was.

**3. A validation tolerance declared before collection.** The model's comment
count may differ from the parser's exact count by at most 5%. Beyond that it is
recorded as a conflict, not averaged away. The number is in the source, above
the code that uses it, committed before the second city was collected. The
Eviction Lab publishes an 86–114% band for the same reason.

**4. Records refuse to overstate themselves.** A record is `verified` only when
it carries a vote and a posting date taken from the document. Anything less is
`partial`, says so in a callout at the top of its own note, and is marked not
citable. Any value supplied by hand rather than found in a source is tagged
`assumed` and demotes the record on its own.

Absence of conflict is not presence of evidence. A ledger that calls a
half-record verified is worse than a ledger with fewer rows, because the
overstatement is invisible at a glance.

## Running it

```bash
pip install -r requirements.txt
export GEMINI_API_KEY=...

# deterministic counting only, no model, no key needed
python tally.py records/chandler_full.txt 2025-12-04 2025-12-11

# the full graph
python graph.py records/chandler_full.txt Chandler 2025-12-04 2025-12-11 \
                records/chandler_item37.txt
```

`tally.py` runs with no API key and reproduces every count in the finding
above. That is deliberate: the numbers the argument rests on do not depend on a
model.

## Provenance

Every record carries a source URL, a retrieval date, and an MD5. A record
without all three is not citable and does not enter the ledger. See
[`records/SOURCES.md`](records/SOURCES.md).

The source PDFs are excluded from the repository for size (390 and 419 pages).
The URLs and checksums are in `SOURCES.md`; re-download and verify.

## Known limits

Published up front rather than discovered by a critic. Full list in
[`METHOD.md`](METHOD.md).

- Extraction is not deterministic across runs. One field returned on one run
  and missed on the next from identical source text. Because every value is
  quote-grounded this is a recall failure, never a precision failure. Planned
  fix is to run extraction twice and union the grounded results.
- Comment counts may include forwarded duplicates. No dedup rule yet.
- Speaker names carry PDF extraction artifacts. The count is auditable because
  every name is stored, not just the total.
- Structure discovery is per-jurisdiction. Chandler took about twenty minutes
  to learn. Every new city costs that again. This is the real cost of the
  project and better code does not reduce it.

## Status

| Decision | Notice window | Response latency | Submissions | Vote | Status |
|---|--:|--:|--:|---|---|
| Chandler 2025-12-11 | 7 d | 1 d | 129 | 7-0 deny | verified |
| Marana 2026-01-06 | — | — | 0 | — | partial |

Early. Two records. The method was written before the second city so that any
later change to the rules is visible rather than retroactive.

## License

MIT. The underlying records are public documents.
