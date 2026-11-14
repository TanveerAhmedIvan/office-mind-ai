"""M1 ingestion: parse md + PDF into heading-aware chunks (tables kept intact)."""
from __future__ import annotations
import re, sys
from dataclasses import dataclass, asdict
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MAX_CHARS = 1200


@dataclass
class Chunk:
    id: str
    source: str
    section: str
    text: str
    superseded: bool = False
    lang: str = "en"


def _lang(text: str) -> str:
    bn = sum("ঀ" <= c <= "৿" for c in text)
    return "bn" if bn > len(text) * 0.2 else "en"


def _split_blocks(body: str) -> list[str]:
    """Split on blank lines, but never inside a table (consecutive '|' lines)."""
    return [b.strip() for b in re.split(r"\n\s*\n", body) if b.strip()]


def chunk_markdown(path: Path) -> list[Chunk]:
    text = path.read_text(encoding="utf-8-sig")
    superseded = "SUPERSEDED" in path.name.upper() or "superseded" in text[:600].lower()
    title = next((l[2:].strip() for l in text.splitlines() if l.startswith("# ")), path.stem)
    sections: list[tuple[str, list[str]]] = [(title, [])]
    for line in text.splitlines():
        m = re.match(r"^(#{2,3})\s+(.*)", line)
        if m:
            sections.append((f"{title} > {m.group(2).strip()}", []))
        elif not line.startswith("# "):
            sections[-1][1].append(line)
    chunks: list[Chunk] = []
    for sec, lines in sections:
        buf = ""
        for block in _split_blocks("\n".join(lines)):
            if buf and len(buf) + len(block) > MAX_CHARS:
                chunks.append(_mk(path, sec, buf, len(chunks), superseded))
                buf = ""
            buf = f"{buf}\n\n{block}" if buf else block
        if buf:
            chunks.append(_mk(path, sec, buf, len(chunks), superseded))
    return chunks


def _mk(path: Path, sec: str, text: str, n: int, superseded: bool) -> Chunk:
    return Chunk(f"{path.name}#{n}", path.name, sec, f"[{sec}]\n{text}", superseded, _lang(text))


def _table_to_md(table: list[list[str | None]]) -> str:
    rows = [[(c or "").replace("\n", " ").strip() for c in r] for r in table if any(r)]
    if not rows:
        return ""
    out = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * len(rows[0])]
    out += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return "\n".join(out)


def chunk_pdf(path: Path) -> list[Chunk]:
    import pdfplumber  # lazy: only needed for PDFs

    chunks: list[Chunk] = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            found = page.find_tables()
            tables = [_table_to_md(t.extract()) for t in found]
            # drop table regions from prose so the garbled copy isn't indexed twice
            prose = page
            for t in found:
                prose = prose.outside_bbox(t.bbox)
            text = prose.extract_text() or ""
            sec = f"{path.stem} p.{i}"
            if text.strip():
                chunks.append(_mk(path, sec, text.strip(), len(chunks), False))
            for t in filter(None, tables):  # tables again as clean markdown, own chunk
                chunks.append(_mk(path, f"{sec} table", t, len(chunks), False))
    return chunks


def ingest_all(data_dir: Path = DATA_DIR) -> list[Chunk]:
    chunks: list[Chunk] = []
    for p in sorted(data_dir.iterdir()):
        if p.suffix == ".md":
            chunks += chunk_markdown(p)
        elif p.suffix == ".pdf":
            chunks += chunk_pdf(p)
    return chunks


if __name__ == "__main__":
    for c in ingest_all():
        print(f"--- {c.id} | {c.section} | lang={c.lang} superseded={c.superseded}\n{c.text}\n")
    print(f"TOTAL chunks: {len(ingest_all())}", file=sys.stderr)
