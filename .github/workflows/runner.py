#!/usr/bin/env python3
# runner.py — Agentic RAG (N2–N3) com fallback de policy e sumário .md
# Requisitos: requests, pyyaml, feedparser
# (o workflow já instala; se rodar local: pip install requests pyyaml feedparser)

import os, sys, json, re, argparse, datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
import yaml, requests, feedparser

# -------- util --------
def now_iso():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def ensure_dir(p): Path(p).mkdir(parents=True, exist_ok=True)

def save_jsonl(path, rows):
    ensure_dir(Path(path).parent)
    with open(path, "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def sanitize(t): return re.sub(r"\s+", " ", (t or "")).strip()

# -------- nível sugerido (termômetro) --------
@dataclass
class ThermometerScore:
    R:int; I:int; C:int; F:int; M:int; K:int
    def total(self): return self.R + self.I + self.C + self.F + self.M + self.K

def decide_level(score, th):
    tot = score.total()
    if tot <= th.get("N1_max", 7): return "N1"
    if tot <= th.get("N2_max", 13): return "N2"
    return "N3"

# -------- policy loader robusto --------
def default_policy():
    return {
        "logging": {"dir": "logs", "file_prefix": "run"},
        "search": {
            "source": "arxiv",
            "query": "(agentic OR \"multi-agent\" OR autonomous) (RAG OR retrieval) (creativity OR art OR poetry OR co-creation OR design OR music)",
            "max_results": 5,
            "days_back": 365
        },
        "limits": {"steps_max": 5, "timebox_min": 20},
        "thermometer_thresholds": {"N1_max": 7, "N2_max": 13, "N3_max": 18}
    }

def load_policy(p_hint: str):
    # tenta vários caminhos e extensões
    candidates = [
        Path(p_hint) if p_hint else Path("policy.yaml"),
        Path("policy.yaml"),
        Path("policy.yml"),
        Path(".github/workflows/policy.yaml"),
        Path(".github/workflows/policy.yml"),
    ]
    for c in candidates:
        if c.exists():
            return yaml.safe_load(c.read_text(encoding="utf-8"))
    # fallback mínimo
    return default_policy()

# -------- arXiv retrieval --------
def arxiv_search(query, max_results=5, days_back=365):
    base = "http://export.arxiv.org/api/query"
    url = (f"{base}?search_query=all:{requests.utils.quote(query)}"
           f"&start=0&max_results={max_results*3}&sortBy=submittedDate&sortOrder=descending")
    # usa requests com User-Agent pra evitar 403
    ua = {"User-Agent": "agentic-rag-runner/1.0 (+github actions)"}
    r = requests.get(url, headers=ua, timeout=45)
    r.raise_for_status()
    feed = feedparser.parse(r.text)

    items = []
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days_back)
    for e in feed.entries:
        up = getattr(e, "updated_parsed", None) or getattr(e, "published_parsed", None)
        dt = datetime.datetime(*up[:6]) if up else None
        if dt and dt >= cutoff:
            items.append({
                "id": e.get("id"),
                "title": sanitize(e.get("title")),
                "summary": sanitize(e.get("summary")),
                "authors": [a.name for a in getattr(e, "authors", [])] if hasattr(e, "authors") else [],
                "updated": dt.isoformat() + "Z",
            })
        if len(items) >= max_results * 2:
            break
    return items[: max_results * 2]

def keyword_score(text, kws):
    t = (text or "").lower()
    return sum(t.count(k.lower()) for k in kws)

def rerank(items, kws, top_k=3):
    scored = [(keyword_score(it["title"] + " " + it["summary"], kws), it) for it in items]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [it for _, it in scored[:top_k]]

def extract_bullets(summary, max_bullets=5):
    sents = re.split(r"(?<=[.!?])\s+", summary)
    out = []
    for s in sents:
        s = sanitize(s)
        if len(s) < 15: continue
        out.append(s[:280])
        if len(out) >= max_bullets: break
    if not out and summary:
        out = [summary[:280]]
    return out

def cite_id(url):
    m = re.search(r"arxiv\.org\/abs\/([\d\.v]+)", url or "")
    return m.group(1) if m else url

# -------- resumo humano (.md) --------
def write_summary_md(out):
    lines = [
        f"# Agentic RAG — {out['run_id']}\n",
        f"**Nível sugerido:** {out['level']}\n",
        f"**IDs citados:** {', '.join(r['id'] for r in out['results'])}\n\n",
        "## Artigos\n",
    ]
    for i, r in enumerate(out["results"], 1):
        lines.append(f"### {i}. {r['title']}\n")
        lines.append(f"- arXiv: {r['id']}  \n- Atualizado: {r['updated']}\n")
        for b in r["bullets"]:
            lines.append(f"  - {b}\n")
        lines.append("\n")
    ensure_dir("outputs")
    Path("outputs/summary.md").write_text("\n".join(lines), encoding="utf-8")

# -------- agente principal --------
def run_agentic_rag(policy, args):
    log_dir = policy["logging"]["dir"]; ensure_dir(log_dir)
    run_id = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    log_path = os.path.join(log_dir, f"{policy['logging']['file_prefix']}-{run_id}.jsonl")

    score = ThermometerScore(R=3, I=3, C=3, F=2, M=3, K=3)
    level = decide_level(score, policy.get("thermometer_thresholds", {}))
    plan = {
        "objective": "Mapear arXiv sobre Agentic RAG com foco em memória e orquestração p/ co-criatividade",
        "sources": "arXiv (últimos 12–18 meses)",
        "steps": ["retrieve", "rerank", "extract", "cite"],
        "success": "3–5 artigos + 5 bullets cada + IDs arXiv",
        "limits": policy.get("limits", {}),
        "level_suggested": level,
        "score": asdict(score),
        "started_at": now_iso(),
    }
    save_jsonl(log_path, [{"ts": now_iso(), "event": "plan", "data": plan}])

    # parâmetros vindos de args ou policy
    q = args.query or policy["search"]["query"]
    maxr = int(args.max_results or policy["search"]["max_results"])
    days = int(args.days_back or policy["search"]["days_back"])

    try:
        items = arxiv_search(q, max_results=maxr, days_back=days)
        save_jsonl(log_path, [{"ts": now_iso(), "event": "retrieve", "data": {"count": len(items), "query": q}}])
    except Exception as e:
        save_jsonl(log_path, [{"ts": now_iso(), "event": "retrieve_error", "data": {"error": str(e)}}])
        items = []

    kw = ["agentic","RAG","memory","tool","multi-agent","retrieval","planning","reflection","creativity","art","poetry","orchestration"]
    top = rerank(items, kw, top_k=maxr) if items else []
    save_jsonl(log_path, [{"ts": now_iso(), "event": "rerank", "data": {"kept": len(top), "keywords": kw}}])

    results = []
    for it in top:
        results.append({
            "id": cite_id(it["id"]),
            "title": it["title"],
            "updated": it["updated"],
            "bullets": extract_bullets(it["summary"], 5),
        })
    save_jsonl(log_path, [{"ts": now_iso(), "event": "extract", "data": {"count": len(results)}}])
    save_jsonl(log_path, [{"ts": now_iso(), "event": "cite", "data": {"ids": [r["id"] for r in results]}}])

    reflection = {
        "gap": "Falta checagem de duplicatas e classificação por subtópico (memória, ferramenta, orquestração).",
        "next_step": "Adicionar filtro de domínios criativos e sumarização cruzada.",
    }
    save_jsonl(log_path, [{"ts": now_iso(), "event": "reflection", "data": reflection}])

    out = {"run_id": run_id, "level": level, "score": asdict(score),
           "results": results, "reflection": reflection, "log_path": log_path}

    # sumário humano
    write_summary_md(out)

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return out

# -------- CLI --------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", default="policy.yaml")
    ap.add_argument("--task", default="agentic_rag")
    ap.add_argument("--query", default=None)
    ap.add_argument("--max_results", default=None)
    ap.add_argument("--days_back", default=None)
    args = ap.parse_args()

    # kill switch via variável de ambiente
    if os.environ.get("KILL_SWITCH", "").strip().upper() == "PAUSAR AGORA":
        print("Kill-switch acionado."); sys.exit(1)

    try:
        policy = load_policy(args.policy)
    except Exception as e:
        print("Aviso: erro ao carregar policy, usando fallback:", e)
        policy = default_policy()

    ensure_dir(policy["logging"]["dir"])

    if args.task == "agentic_rag":
        run_agentic_rag(policy, args)
    else:
        print("Tarefa desconhecida. Use --task agentic_rag")
        sys.exit(2)

if __name__ == "__main__":
    main()