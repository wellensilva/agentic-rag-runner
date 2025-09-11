
# tests/active_rag_stub_v2.py
from tests._utils_io import read_json, write_json, stopwatch

kb_path = "state/kb.json"
kb = read_json(kb_path, [
  {"id":"pol.2024.fretes","ts":"2024-08-01","text":"Frete grátis acima de R$300. Entregas: 3-5 dias."}
])

def query_kb(q, kb):
    hits = [d for d in kb if any(w in d["text"].lower() for w in q.lower().split())]
    hits.sort(key=lambda d: d["ts"], reverse=True)
    return hits[:1]

def answer(q, kb):
    top = query_kb(q, kb)
    if not top: return {"answer":"Sem política encontrada.","source":None}
    return {"answer": f"Política vigente: {top[0]['text']}", "source": top[0]["id"]}

q = "Qual é a política de fretes e prazo?"
a0 = answer(q, kb)

# assimilate
assim = {"id":"pol.2025.fretes.v1","ts":"2025-01-10","text":"Frete grátis acima de R$400. Entregas: 2-4 dias."}
kb.append(assim)
a1 = answer(q, kb)

# accommodate
acomo = {"id":"pol.2025.fretes.v2","ts":"2025-02-05","text":"Frete grátis acima de R$350. Entregas: 2-3 dias."}
kb.append(acomo)
a2 = answer(q, kb)

write_json(kb_path, kb)

out = {
  "initial": a0,
  "after_assimilation": a1,
  "after_accommodation": a2,
  "consistency": (a2["source"]=="pol.2025.fretes.v2")
}
write_json("active_rag_summary_v2.json", out)
print("[active_v2] ok -> active_rag_summary_v2.json")
