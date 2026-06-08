from __future__ import annotations

import re

from markupsafe import Markup, escape

MTG_ARENA_KEYWORDS = ("Challenge", "Friends", "Draft", "Sealed", "Limited")

MTG_ARENA_KEYWORD_RE = re.compile(
    r"\b(" + "|".join(re.escape(word) for word in MTG_ARENA_KEYWORDS) + r")\b",
    re.I,
)


def highlight_mtg_terms(text: str) -> Markup:
    escaped = str(escape(text))
    highlighted = MTG_ARENA_KEYWORD_RE.sub(r'<mark class="feed-card__keyword">\1</mark>', escaped)
    return Markup(highlighted)
