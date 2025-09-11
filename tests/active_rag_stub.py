# tests/active_rag_stub.py
import json, time, pathlib

OUT = pathlib.Path("logs"); OUT.mkdir(exist_ok=True)

# Base inicial
kb = [
  {"id":"pol.2024.fretes","ts":"2024-08-01","text":"Frete grátis acima de R$300. Entregas: 3-5 dias."}
]

def query_kb(q, kb):
    # pega o doc mais novo que "bate" por palavra-chave
    hits = [d for d in kb if any(w in d["text"].lower() for w in q.lower().split())]
    hits.sort(key=lambda d: d["ts"], reverse=True)
    return hits[:1]

def answer(q, kb):
    top = query_kb(q, kb)
    if not top:
        return {"answer":"Sem política encontrada.", "source":None}
    pol = top[0]
    return {"answer": f"Política vigente: {pol['text']}", "source": pol["id"]}

# 1) Estado inicial
q = "Qual é a política de fretes e prazo?"
a0 = answer(q, kb)

# 2) ASSIMILAÇÃO — chega um documento novo
assim = {"id":"pol.2025.fretes.v1","ts":"2025-01-10","text":"Frete grátis acima de R$400. Entregas: 2-4 dias."}
kb.append(assim)
a1 = answer(q, kb)

# 3) ACOMODAÇÃO — chega um doc que corrige o anterior (mais novo)
acomo = {"id":"pol.2025.fretes.v2","ts":"2025-02-05","text":"Frete grátis acima de R$350. Entregas: 2-3 dias."}
kb.append(acomo)
a2 = answer(q, kb)

summary = {
  "q": q,
  "initial": a0,
  "after_assimilation": a1,
  "after_accommodation": a2,
  "kb_len": len(kb),
  "timeline": [d["id"] for d in kb],
  "consistency": (a2["source"]=="pol.2025.fretes.v2"),
  "ts": time.time()
}

path = pathlib.Path("active_rag_summary.json")
path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"[active] ok -> {path}")