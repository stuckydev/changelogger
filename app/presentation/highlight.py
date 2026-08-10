from __future__ import annotations

import re

from markupsafe import Markup, escape


def highlight_terms(text: str, terms: tuple[str, ...]) -> Markup:
    if not terms:
        return Markup(escape(text))
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(word) for word in terms) + r")\b",
        re.I,
    )
    escaped = str(escape(text))
    highlighted = pattern.sub(r'<mark class="feed-card__keyword">\1</mark>', escaped)
    return Markup(highlighted)
