#!/usr/bin/env python3
import json, time, argparse, pathlib, urllib.parse

def save_json(path, data):
    path.parent.mkdir(exist_ok=True, parents=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def search_arxiv(query, n=3):
    try:
        import feedparser  # só é carregado se realmente for usar
    except ImportError:
        raise RuntimeError("feedparser não instalado (use Solução B ou rode o modo demo).")
    base = "http://export.arxiv.org/api/query"
    q = urllib.parse.quote(query)
    url = f"{base}?search_query=all:{q}&start=0&max_results={n}&sortBy=lastUpdatedDate&sortOrder=descending"
    feed = feedparser.parse(url)
    items = []
    for e in feed.entries[:n]:
        items.append({
            "title": e.title,
            "link": e.link,
            "published": getattr(e, "published", ""),
            "summary": getattr(e, "summary", "")[:500]
        })
    return items

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--task", default="demo")
    p.add_argument("--query", default="")
    p.add_argument("--max_results", type=int, default=5)
    args = p.parse_args()

    logs = pathlib.Path("logs"); logs.mkdir(exist_ok=True)
    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "task": args.task,
        "query": args.query,
        "max_results": args.max_results,
        "results": []
    }

    try:
        if args.task == "papers" and args.query:
            summary["results"] = search_arxiv(args.query, args.max_results)
        else:  # DEMO sem dependências
            summary["results"] = [
                {"title": "Agentic RAG: memória e cadeias de ferramentas (demo)", "score": 0.91},
                {"title": "Memória hierárquica para agentes (demo)", "score": 0.88},
                {"title": "Planejamento com ferramentas (demo)", "score": 0.85},
            ][:args.max_results]
    except Exception as e:
        summary["error"] = str(e)

    save_json(logs / "run_summary.json", summary)
    print(f"[OK] logs/run_summary.json gerado com {len(summary['results'])} itens.")

if __name__ == "__main__":
    main()