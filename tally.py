"""Counting, with no model involved.

The extraction graph asks a language model to read prose. That is the right
tool for "who moved the motion" and the wrong tool for "how many comment cards
were filed," because the cards are a structured form repeated N times and
counting them is arithmetic, not reading.

So this file counts. It never guesses, it cannot hallucinate, and it produces
the ground truth that the model's answer gets checked against in verify().

The clerk's attachment format is a repeated block:

    Submitted on Fri, 12/05/2025 - 06:55 AM
    Submitted by: Anonymous
    Submitted values are:
    Name
    <name>
    Address
    <address>
    Agenda Item No.        <- optional, many leave it blank
    <free text>
    Support/Oppose         <- optional
    Oppose
    Comments               <- optional
    <body>

Fields are optional, which is why the counts do not all match. That is a
finding about the form, not an error in the parser, so all four counts are
reported separately and never collapsed into one number.
"""
import re
from collections import Counter
from datetime import date, datetime

# One submission begins at "Submitted on <Day>, MM/DD/YYYY". Nothing else in
# the record uses that string, which is what makes it a safe delimiter.
SUBMITTED = re.compile(r"^Submitted on\s+\w{3},\s+(\d{2})/(\d{2})/(\d{4})", re.M)


def _value_after(block: str, label: str):
    """Return the line following a field label, or None if the field is absent.

    The label must be the whole line. Matching a bare substring would catch
    'Support/Oppose' inside somebody's comment text and inflate the count.
    """
    lines = [ln.strip() for ln in block.splitlines()]
    for i, ln in enumerate(lines[:-1]):
        if ln == label:
            nxt = lines[i + 1].strip()
            return nxt or None
    return None


def tally(text: str) -> dict:
    """Count every written submission attached to the record."""
    starts = [(m.start(), date(int(m.group(3)), int(m.group(1)), int(m.group(2))))
              for m in SUBMITTED.finditer(text)]
    if not starts:
        return {"submissions": 0}

    # Each submission runs until the next one begins.
    bounds = [s[0] for s in starts] + [len(text)]
    blocks = [text[bounds[i]:bounds[i + 1]] for i in range(len(starts))]

    positions, names, by_day = Counter(), [], Counter()
    for (_, day), block in zip(starts, blocks):
        by_day[day] += 1
        if (p := _value_after(block, "Support/Oppose")):
            positions[p.strip().lower()] += 1
        if (n := _value_after(block, "Name")):
            names.append(n.strip().lower())

    return {
        "submissions": len(starts),
        "with_position": sum(positions.values()),
        "oppose": positions.get("oppose", 0),
        "support": positions.get("support", 0),
        "unique_names": len(set(names)),
        "repeat_submitters": sum(1 for _, c in Counter(names).items() if c > 1),
        "by_day": {d.isoformat(): n for d, n in sorted(by_day.items())},
        "first_submission": min(by_day).isoformat(),
        "last_submission": max(by_day).isoformat(),
    }


# Clerks introduce a speaker as an all-caps name, then an address that ends in
# the state. The minutes never state a total, so asking a model for one invites
# it to infer, which the prompt forbids and which we would have to trust. This
# is countable, so count it.
SPEAKER = re.compile(
    r"^([A-Z][A-Z'’.\- ]{3,40}?),\s+[^\n]{5,80}?,\s*(?:AZ|Arizona)\b",
    re.M)


def count_speakers(narrative: str) -> dict:
    """Count people who spoke aloud on this item, and keep their names so the
    number can be audited rather than believed."""
    names = []
    for m in SPEAKER.finditer(narrative):
        n = " ".join(m.group(1).split())
        if n not in names:          # a person who speaks twice is one speaker
            names.append(n)
    return {"speakers": len(names), "speaker_names": names}


def derive(t: dict, agenda_posted: str, vote_date: str) -> dict:
    """The numbers the source documents do not contain.

    notice_window_days
        Agenda posting to vote. This is how long the decision was formally
        findable. It is the number the phrase "the public had the opportunity
        to comment" is actually making a claim about.

    response_latency_days
        Posting to the first written comment. How long it took somebody to
        react once reacting was possible. A small number here kills the
        apathy explanation, because it shows the willingness was already
        there and only the visibility was missing.

    same_day_share
        Share of all submissions filed on the day of the vote itself. High
        values mean people found out at the last possible moment.
    """
    posted, voted = date.fromisoformat(agenda_posted), date.fromisoformat(vote_date)
    first = date.fromisoformat(t["first_submission"])
    same_day = t["by_day"].get(vote_date, 0)

    return {
        "notice_window_days": (voted - posted).days,
        "response_latency_days": (first - posted).days,
        "same_day_share": round(same_day / t["submissions"], 3) if t["submissions"] else None,
        "same_day_count": same_day,
        "oppose_ratio": (round(t["oppose"] / t["support"], 1)
                         if t.get("support") else None),
    }


if __name__ == "__main__":
    import json, sys
    if len(sys.argv) < 4:
        sys.exit("usage: python tally.py <record.txt> <agenda_posted> <vote_date>")
    t = tally(open(sys.argv[1]).read())
    print(json.dumps({**t, **derive(t, sys.argv[2], sys.argv[3])}, indent=2))
