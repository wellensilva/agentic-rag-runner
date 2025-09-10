#!/usr/bin/env python3
import json, time, argparse, pathlib

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--task", default="demo")
    p.add_argument("--max_results", type=int, default=5)
    args = p.parse_args()

    logs = pathlib.Path("logs"); logs.mkdir(exist_ok=True)
    results = [
        {"title": "Agentic RAG: memória e cadeias de ferramentas (demo)", "score": 0.91},
        {"title": "Memória hierárquica para agentes (demo)", "score": 0.88},
        {"title": "Planejamento com ferramentas (demo)", "score": 0.85},
    ][:args.max_results]

    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "task": args.task,
        "max_results": args.max_results,
        "results": results,
    }
    (logs / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[OK] Gerado logs/run_summary.json com {len(results)} itens.")

if __name__ == "__main__":
    main()