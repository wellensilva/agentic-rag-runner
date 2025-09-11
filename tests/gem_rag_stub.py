# tests/gem_rag_stub.py
import json, math, time, pathlib, re
from collections import defaultdict, Counter

OUT = pathlib.Path("logs"); OUT.mkdir(exist_ok=True)

# --- Mini "grafo de memória" de exemplo ---
nodes = {
    "u:ana": {"type":"user","text":"Cliente Ana; prefere contato por WhatsApp; histórico positivo"},
    "u:bruno": {"type":"user","text":"Cliente Bruno; prefere email; histórico misto"},
    "e:pedido_grande_2024": {"type":"event","text":"Ana fez pedido grande em 2024-09; ticket alto"},
    "e:reclam_atraso": {"type":"event","text":"Bruno reclamou de atraso na entrega em 2025-01"},
    "d:reembolso": {"type":"doc","text":"Procedimento de reembolso e retenção de clientes valiosos"},
    "d:upsell": {"type":"doc","text":"Guia de upsell com amostras e brindes"},
    "t:crm": {"type":"tool","text":"Ferramenta CRM-lookup (consulta perfil e pedidos)"},
    "t:search": {"type":"tool","text":"Ferramenta RAG-search (busca docs internos)"},
}
edges = [
    ("u:ana","e:pedido_grande_2024"),
    ("u:ana","t:crm"),
    ("u:ana","t:search"),
    ("e:pedido_grande_2024","d:upsell"),
    ("u:bruno","e:reclam_atraso"),
    ("e:reclam_atraso","d:reembolso"),
    ("u:bruno","t:crm"),
    ("u:bruno","t:search"),
]

# --- util ---
def tokenize(txt):
    return re.findall(r"[A-Za-zÀ-ÿ0-9]+", txt.lower())

def build_adj(nodes, edges):
    idx = {k:i for i,k in enumerate(nodes.keys())}
    rev = {i:k for k,i in idx.items()}
    n = len(idx)
    adj = [[0]*n for _ in range(n)]
    for a,b in edges:
        ia, ib = idx[a], idx[b]
        adj[ia][ib] = 1
        adj[ib][ia] = 1
    return idx, rev, adj

def eigen_centrality(adj, iters=30, damping=0.85):
    n = len(adj)
    v = [1.0/n]*n
    for _ in range(iters):
        nv = [0.0]*n
        for i in range(n):
            deg = sum(adj[i])
            if deg:
                share = v[i]/deg
                for j in range(n):
                    if adj[i][j]:
                        nv[j] += share
        v = [ (1-damping)/n + damping*nv[i] for i in range(n) ]
        s = sum(v); 
        if s: v = [x/s for x in v]
    return v

def text_score(q_tokens, text):
    toks = tokenize(text)
    inter = set(q_tokens) & set(toks)
    return len(inter) / max(1,len(set(q_tokens)))

# --- consulta "stub" ---
query = "Plano para atender a Ana hoje com upsell e próxima ação"
q_tokens = tokenize(query)

idx, rev, adj = build_adj(nodes, edges)
eig = eigen_centrality(adj)

scored = []
for key, meta in nodes.items():
    i = idx[key]
    s_text = text_score(q_tokens, meta["text"])  # relevância textual
    s_eig  = eig[i]                              # importância estrutural
    score  = 0.7*s_text + 0.3*s_eig              # mistura simples
    scored.append((score, key, meta))

scored.sort(reverse=True)
top = scored[:5]

# Heurística bobinha p/ escolher ferramentas
picked_tools = [k for _,k,m in top if m["type"]=="tool"] or ["t:crm","t:search"]

answer_stub = {
    "query": query,
    "top_memories": [
        {"id":k, "type":m["type"], "text":m["text"], "score":round(s,4)}
        for s,k,m in top
    ],
    "picked_tools": picked_tools,
    "plan": [
        "1) Abrir CRM-lookup para revisar perfil e pedidos da Ana",
        "2) Usar RAG-search para buscar ofertas relacionadas a ticket alto",
        "3) Oferecer amostra/brinde (upsell) + agendar follow-up por WhatsApp"
    ],
    "ts": time.time()
}

path = pathlib.Path("gem_summary.json")
path.write_text(json.dumps(answer_stub, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"[gem] ok -> {path}")