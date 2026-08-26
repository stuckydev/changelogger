from __future__ import annotations

import re

MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
MD_CODE_RE = re.compile(r"`([^`]+)`")
MD_STRIKE_RE = re.compile(r"~~(.+?)~~")
MD_BOLD_RE = re.compile(r"\*\*(.+?)\*\*|__(.+?)__")


def strip_inline_markdown(text: str) -> str:
    cleaned = MD_LINK_RE.sub(r"\1", text)
    cleaned = MD_CODE_RE.sub(r"\1", cleaned)
    cleaned = MD_STRIKE_RE.sub(r"\1", cleaned)
    cleaned = MD_BOLD_RE.sub(lambda match: match.group(1) or match.group(2), cleaned)
    return cleaned.replace("**", "").replace("__", "")
