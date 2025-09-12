import feedparser, urllib.parse, pathlib, json, datetime

OUT_DIR = pathlib.Path("outputs")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def run(query: str, max_results: int = 5):
    base = "http://export.arxiv.org/api/query"
    q = urllib.parse.urlencode({"search_query": query, "start": 0, "max_results": max_results})
    feed = feedparser.parse(f"{base}?{q}")

    items = []
    for e in feed.entries:
        items.append({
            "title": e.title,
            "authors": [a.name for a in getattr(e, "authors", [])],
            "summary": getattr(e, "summary", "").strip(),
            "link": getattr(e, "link", "")
        })

    stamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    md_lines = [f"# arXiv — resultados para: `{query}`\n"]
    for i, it in enumerate(items, 1):
        md_lines += [
            f"## {i}. {it['title']}",
            f"- Autores: {', '.join(it['authors'])}" if it["authors"] else "- Autores: —",
            f"- Link: {it['link']}",
            f"\n{it['summary']}\n"
        ]
    (OUT_DIR / f"papers-{stamp}.md").write_text("\n".join(md_lines), encoding="utf-8")
    (OUT_DIR / f"papers-{stamp}.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"query": query, "count": len(items), "items": items, "markdown": f"outputs/papers-{stamp}.md"}