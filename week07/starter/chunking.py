"""Recursive chunking for the Week 7 corpus.

Each chunk carries the source doc_id and section so the practical's gold set
can resolve section-level answers across chunking configurations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Pattern

from corpus_loader import Section, load_sections

TOKEN_PATTERN: Pattern[str] = re.compile(r"\w+|[^\w\s]", re.UNICODE)
SEPARATORS = ("\n\n", "\n", ". ", " ")


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    section: str
    text: str
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def key(self) -> tuple[str, str]:
        return (self.doc_id, self.section)

    @property
    def section_key(self) -> str:
        return f"{self.doc_id}::{self.section}"


def _token_count(text: str) -> int:
    return len(TOKEN_PATTERN.findall(text))


def _format_chunk_text(section: str, body: str) -> str:
    """Keep the section heading next to each body fragment."""
    return f"{section}\n{body}".strip()


def _split_preserving_separator(text: str, separator: str) -> list[str]:
    parts = text.split(separator)
    if len(parts) == 1:
        return parts
    return [
        part + separator if index < len(parts) - 1 else part
        for index, part in enumerate(parts)
    ]


def _recursive_split(text: str, size: int, separator_index: int = 0) -> list[str]:
    if _token_count(text) <= size:
        return [text]

    for index in range(separator_index, len(SEPARATORS)):
        separator = SEPARATORS[index]
        parts = _split_preserving_separator(text, separator)
        if len(parts) == 1:
            continue

        chunks: list[str] = []
        current = ""
        for part in parts:
            if _token_count(part) > size:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.extend(_recursive_split(part, size, index + 1))
            elif current and _token_count(current) + _token_count(part) > size:
                chunks.append(current)
                current = part
            else:
                current += part
        if current:
            chunks.append(current)
        return chunks
    return [text]


def _tail_tokens(text: str, count: int) -> str:
    tokens = list(TOKEN_PATTERN.finditer(text))
    if not tokens:
        return ""
    return text[tokens[max(0, len(tokens) - count)].start():]


def chunk_sections(sections: list[Section], size: int = 300,
                   overlap: int = 40) -> list[Chunk]:
    """Recursively chunk sections and preserve the corpus metadata.

    Decisions for this chunker: target 300 lexical tokens per body chunk
    (the requested 250-350 token range) and repeat the previous 40 lexical
    tokens (the requested 30-50 overlap range). The lexical counter treats
    each word and punctuation mark as a token so chunking needs no
    model-specific tokenizer dependency; the size and overlap arguments
    remain configurable for the practical's 300/600/1200 sweep.

    Split recursively with separators in this exact priority order:
    paragraph breaks (``\\n\\n``), line breaks (``\\n``), sentence endings
    (``. ``), then spaces. This keeps paragraphs together whenever possible
    and only descends to sentence/word boundaries when a paragraph exceeds
    the target size. A single unbroken token is retained rather than lost.

    Prefix every chunk's text with its section heading, and attach a copy
    of all YAML header metadata (including doc_id, title, version, status,
    language, and any future front-matter fields) to every chunk. Keep
    ``doc_id`` and ``section`` as explicit fields because the practical's
    gold set and scorer resolve answers by that stable pair, not chunk id.
    Chunk ids are deterministic within each (doc_id, section).
    """
    if size <= 0:
        raise ValueError("size must be positive")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must be non-negative and smaller than size")

    chunks: list[Chunk] = []
    for section in sections:
        heading = section.section
        heading_tokens = _token_count(heading)
        body_size = max(1, size - heading_tokens)
        body_chunks = _recursive_split(section.text.strip(), body_size)

        for index, body in enumerate(body_chunks):
            if index:
                body = _tail_tokens(body_chunks[index - 1], overlap) + body
            metadata = dict(section.metadata)
            metadata.setdefault("doc_id", section.doc_id)
            metadata.setdefault("title", section.title)
            metadata["section"] = section.section
            chunks.append(Chunk(
                chunk_id=f"{section.doc_id}::{section.section}::{index}",
                doc_id=section.doc_id,
                section=section.section,
                text=_format_chunk_text(heading, body),
                metadata=metadata,
            ))
    return chunks


def load_chunks(size: int = 300, overlap: int = 40) -> list[Chunk]:
    return chunk_sections(load_sections(), size=size, overlap=overlap)
