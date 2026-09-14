---
type: method
version: 0.3
updated: 2026-08-31
---

# How a record is made

Written before the second city, so that changing it later is visible.

## The unit

**One decision** that committed power, water, or a tax benefit to a data
center. Not a facility, not a company, not a meeting. A decision.

A meeting that votes on two linked items (a rezoning and its development
agreement, voted together) is one decision, because a resident had one chance
to speak on it.

## The two derived numbers

Neither appears in any source document. They are the reason this is research
and not a database.

**Notice window** — days from agenda posting to vote. This is how long the
decision was formally findable. It is the number that the sentence "the public
had the opportunity to comment" is actually making a claim about.

**Response latency** — days from agenda posting to the first written public
comment. This is how long it took somebody to react once reacting was
possible. It is the number that answers the apathy explanation, because a
small value shows the willingness was already there and only the visibility
was missing.

## What a model does and what a parser does

The split is not stylistic. It is the whole design.

| Question | Answered by | Why |
|---|---|---|
| Who moved the motion, what was the vote, what did staff recommend | model | prose, phrased differently every time |
| How many comments were filed, how many opposed, when they arrived | parser | a repeated structured form; this is arithmetic |
| How many people spoke | parser | the minutes name each speaker and never total them |

A model asked to count 129 repeated form blocks will approximate. A parser
cannot. So the parser counts, and the model's answer is checked against it.

## Grounding

Every value the model returns must arrive with the exact sentence it came
from. The code then discards any value whose quote is not a literal substring
of the source. A model can invent a number. It cannot invent a sentence that
survives a substring check.

Consequence worth stating plainly: **a grounded value cannot be wrong, but it
can be missed.** See the known limits below.

## Validation tolerance, declared in advance

The model's comment count may differ from the parser's exact count by at most
**5%**. Beyond that it is recorded as a conflict, not averaged away.

Declared here, before collection, on purpose. The Eviction Lab publishes an
86–114% band for the same reason. Deciding what counts as correct before you
look is what separates a method from a preference.

## When a record counts as evidence

A record is **verified** only when it carries a vote and a posting date taken
from the record itself. Anything short of that is **partial**, says so in a
callout at the top of its own note, and must not be quoted.

Absence of conflict is not presence of evidence. A ledger that calls a
half-record verified is worse than a ledger with fewer rows, because the
overstatement is invisible at a glance.

Any value supplied by hand rather than found in a document is tagged
`assumed` and demotes the record to partial on its own.

## The statutory floor

Arizona requires **24 hours** of notice (A.R.S. § 38-431.02, and subsection G
for the agenda). That is the legal meaning of "the opportunity to comment,"
and it is the number the study is really about. See [[The 24-hour floor]].

Notice window is therefore not just a per-decision measurement. It is a
measurement of how far above the floor a given body chose to go, and that
choice is the variable.

## Conflicts

Recorded, never resolved silently. A disagreement between two sources is a
finding about the record, which is the subject of the study.

## Known limits

- **Extraction is not deterministic across runs.** On the Chandler record,
  `cooling_type` was returned on one run and missed on the next, from the same
  source text. Because every value is quote-grounded, a missed field is a
  recall failure and never a precision failure. The planned fix is to run
  extraction twice and take the union of grounded values, which is safe
  precisely because a grounded value cannot be fabricated.
- **Comment counts may include forwarded duplicates.** The clerk's attachment
  includes emails forwarded internally. Not yet deduplicated. A dedup rule
  must be written and applied to every record, retroactively.
- **At least one submission arrived after the vote.** Chandler has a
  thank-you filed the following morning. It carries no position field, so it
  falls out of the oppose/support counts naturally, but an explicit inclusion
  rule is still needed.
- **Speaker names carry PDF extraction artifacts.** "TERESA WAR NICK" is one
  person whose surname broke across a line. The count is auditable because
  every name is stored, not just the total.
- **Structure discovery is per-jurisdiction.** Chandler took roughly twenty
  minutes to learn. Every new city costs that again, because clerks do not
  share a format. This is the real cost of the project and it does not
  shrink with better code.

## Provenance

Every record carries a source URL, a retrieval date, and an MD5. A record
without all three is not citable and does not go in the ledger.

---
Index: [[Ledger]]
