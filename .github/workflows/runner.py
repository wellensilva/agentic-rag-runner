# runner.py
import argparse, json, time, pathlib

LOG_DIR = pathlib.Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
OUT = LOG_DIR / "run_summary.json"

def save(obj):
    OUT.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def run_demo(max_results):
    items = [
        {"title": "Agentic RAG: memória + cadeia de ferramentas (demo)", "score": 0.91},
        {"title": "Memória hierárquica para agentes (demo)", "score": 0.88},
        {"title": "Planejamento com ferramentas (demo)", "score": 0.85},
    ][:max_results]
    return items

def run_papers(query, max_results):
    import feedparser
    q = query or "agentic RAG memory tool use 2024 arXiv"
    url = f"https://export.arxiv.org/api/query?search_query=all:{q}&start=0&max_results={max_results}"
    feed = feedparser.parse(url)
    items = []
    for e in feed.entries:
        items.append({
            "title": e.get("title", "").strip(),
            "link": e.get("id", ""),
            "published": e.get("published", ""),
            "summary": e.get("summary", "").strip(),
            "authors": [a.get("name","") for a in e.get("authors", [])],
        })
    return items

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="demo", choices=["demo","papers"])
    ap.add_argument("--query", default="")
    ap.add_argument("--max_results", type=int, default=5)
    args = ap.parse_args()

    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "task": args.task,
        "query": args.query,
        "max_results": args.max_results,
        "results": [],
        "note": ""
    }

    if args.task == "papers":
        summary["results"] = run_papers(args.query, args.max_results)
        summary["note"] = "Busca no arXiv concluída."
    else:
        summary["results"] = run_demo(args.max_results)
        summary["note"] = "Modo demo (sem internet/dependências)."

    save(summary)
    print(f"OK → {OUT}")