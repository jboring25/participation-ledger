"""What we extract, and what each field means.

This is the only file with domain knowledge in it. If the study changes, it
changes here and nowhere else.

Note what is NOT here: the governing body. You already know which council's
minutes you are reading, so it is metadata you pass in, not a fact you extract.
Extracting things you already know just creates noise.

The definitions are not documentation. They go straight into the prompt, and
they are the difference between a model that guesses and one that does not.
"""

FIELDS = {
    "date":
        "Date the body voted on this item. Not the date the document was written.",
    "item":
        "The agenda item NUMBER only, e.g. '14'. Never the description.",
    "vote_yes":
        "How many members voted in favor. Integer.",
    "vote_no":
        "How many members voted against. Integer.",
    "consent_agenda":
        "true if the text says the item was placed on a consent agenda, even "
        "if it was later pulled for separate discussion. Otherwise false.",
    "comments_filed":
        "Total comment cards or speaker cards SUBMITTED on this item, whether "
        "or not the person ended up speaking. This is a count of paper "
        "submitted, not of people who talked.",
    "speakers":
        "How many people actually SPOKE ALOUD at the meeting on this item. "
        "Usually a subset of comments_filed. If the text only says cards were "
        "submitted, this is null.",
    "notice_radius_feet":
        "If the record states a distance within which nearby property owners "
        "were mailed notice of the hearing, that distance in feet. Integer. "
        "This is the physical size of the group the process treats as "
        "affected, and it is usually far smaller than the group that is.",
    "neighborhood_meeting_attendance":
        "If the record states how many residents attended a pre-hearing "
        "neighborhood or open-house meeting, that number. Integer. If several "
        "meetings are listed, the total across all of them.",
    "acres":
        "Size of the site in acres, as stated. Integer or decimal.",
    "megawatts":
        "Peak electrical demand at full build-out, in MW. Integer.",
    "water_acre_feet":
        "Annual water demand in acre-feet. Integer.",
    "cooling_type":
        "Cooling system type if stated: air-cooled, evaporative, closed-loop. "
        "Otherwise null.",
}
