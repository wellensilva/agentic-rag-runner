import json, os, time
from pathlib import Path

STATE_DIR = Path("state")
STATE_DIR.mkdir(exist_ok=True)
KB_PATH = STATE_DIR / "kb.json"
OUT_PATH = Path("active_rag_summary_v2.json")

def read_json(path: Path, default):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def query_kb(q, kb):
    q_words = {w.lower() for w in q.split()}
    hits = [d for d in kb if any(w in d.get("text","").lower() for w in q_words)]
    hits.sort(key=lambda d: d.get("ts",""), reverse=True)  # mais recente primeiro
    return hits[:1]

def answer(q, kb):
    top = query_kb(q, kb)
    if not top:
        return {"answer": "Sem política registrada."}
    return {"answer": f"Política vigente: {top[0]['text']}", "doc_id": top[0]["id"]}

def main():
    t0 = time.time()
    kb = read_json(KB_PATH, [])

    q = "Qual é a política de fretes e prazo?"

    a0 = answer(q, kb)

    # assimilar (primeira versão conhecida)
    assim = {
        "id": "pol.2025.fretes.v1",
        "ts": "2025-07-01",
        "text": "Frete grátis acima de R$200; prazo padrão de 7 dias úteis."
    }
    kb.append(assim)
    a1 = answer(q, kb)

    # acomodar (versão mais nova que substitui prática)
    acomo = {
        "id": "pol.2025.fretes.v2",
        "ts": "2025-09-01",
        "text": "Frete grátis acima de R$250; prazo padrão de 5 dias (10 em áreas remotas)."
    }
    kb.append(acomo)
    a2 = answer(q, kb)

    write_json(KB_PATH, kb)

    out = {
        "initial": a0,
        "after_assimilation": a1,
        "after_accommodation": a2,
        "kb_count": len(kb),
        "latency_ms": int((time.time() - t0) * 1000)
    }
    write_json(OUT_PATH, out)

if __name__ == "__main__":
    main()
