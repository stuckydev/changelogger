from __future__ import annotations

import re

from markupsafe import Markup, escape

from app.ingestion.normalize import strip_inline_markdown


def highlight_terms(text: str, terms: tuple[str, ...]) -> Markup:
    text = strip_inline_markdown(text)
    if not terms:
        return Markup(escape(text))
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(word) for word in terms) + r")\b",
        re.I,
    )
    escaped = str(escape(text))
    highlighted = pattern.sub(r'<span class="feed-card__keyword">\1</span>', escaped)
    return Markup(highlighted)
