#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Runner simples para:
- task=demo: gera resultados fictícios (sem dependências)
- task=papers: busca no arXiv via feedparser (se instalado)
Salva logs em logs/run_summary.json
"""

import json, time, argparse, pathlib, urllib.parse, sys

def save_json(path, data):
    path.parent.mkdir(exist_ok=True, parents=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def search_arxiv(query, n=3):
    try:
        import feedparser  # import lazy: só carrega se necessário
    except Exception as e:
        raise RuntimeError("feedparser não instalado. Rode task=demo ou instale feedparser.") from e

    base = "http://export.arxiv.org/api/query"
    q = urllib.parse.quote(query)
    url = f"{base}?search_query=all:{q}&start=0&max_results={n}&sortBy=lastUpdatedDate&sortOrder=descending"
    feed = feedparser.parse(url)

    items = []
    for e in feed.entries[:n]:
        items.append({
            "title": getattr(e, "title", "").strip(),
            "link": getattr(e, "link", ""),
            "published": getattr(e, "published", ""),
            "summary": (getattr(e, "summary", "") or "").strip()[:600]
        })
    return items

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--task", default="demo")              # demo | papers
    p.add_argument("--query", default="")
    p.add_argument("--max_results", type=int, default=3)
    args = p.parse_args()

    logs_dir = pathlib.Path("logs")
    logs_dir.mkdir(exist_ok=True)

    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "task": args.task,
        "query": args.query,
        "max_results": args.max_results,
        "results": [],
        "note": ""
    }

    try:
        if args.task == "papers" and args.query:
            summary["results"] = search_arxiv(args.query, args.max_results)
            summary["note"] = "Busca no arXiv concluída."
        else:
            # Modo DEMO sem dependências externas
            demo = [
                {"title": "Agentic RAG: memória + cadeia de ferramentas (demo)", "score": 0.91},
                {"title": "Memória hierárquica para agentes (demo)", "score": 0.88},
                {"title": "Planejamento com ferramentas (demo)", "score": 0.85},
            ][: max(1, args.max_results)]
            summary["results"] = demo
            summary["note"] = "Modo demo (sem internet/dependências)."
    except Exception as e:
        summary["error"] = f"{type(e).__name__}: {e}"

    save_json(logs_dir / "run_summary.json", summary)
    print(f"[OK] logs/run_summary.json gerado com {len(summary['results'])} itens.")
    if "error" in summary:
        print(f"[WARN] {summary['error']}", file=sys.stderr)

if __name__ == "__main__":
    main()