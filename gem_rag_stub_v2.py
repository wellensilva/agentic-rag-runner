
# tests/gem_rag_stub_v2.py
import re, time, pathlib, json
from collections import defaultdict
from tests._utils_io import write_json, read_json, stopwatch
from tests._metrics import precision_at_k

def tokenize(txt): return re.findall(r"[A-Za-zÀ-ÿ0-9]+", txt.lower())

# Load or init memory graph
graph_path = "state/memory_graph.json"
state = read_json(graph_path, {})
if not state:
    state = {
      "nodes": {
        "u:ana": {"type":"user","text":"Cliente Ana; prefere WhatsApp; histórico positivo"},
        "e:pedido_grande_2024": {"type":"event","text":"Ana fez pedido grande em 2024-09; ticket alto"},
        "d:upsell": {"type":"doc","text":"Guia de upsell com amostras e brindes"},
        "t:crm": {"type":"tool","text":"Ferramenta CRM-lookup"},
        "t:search": {"type":"tool","text":"Ferramenta RAG-search"}
      },
      "edges": [
        ["u:ana","e:pedido_grande_2024"],
        ["e:pedido_grande_2024","d:upsell"],
        ["u:ana","t:crm"],
        ["u:ana","t:search"]
      ]
    }

nodes = state["nodes"]; edges = [tuple(e) for e in state["edges"]]

def build_idx(nodes):
    idx = {k:i for i,k in enumerate(nodes.keys())}
    rev = {i:k for k,i in idx.items()}
    n = len(idx); adj = [[0]*n for _ in range(n)]
    for a,b in edges:
        ia, ib = idx[a], idx[b]
        adj[ia][ib] = 1; adj[ib][ia] = 1
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
                    if adj[i][j]: nv[j]+=share
        v = [ (1-damping)/n + damping*nv[i] for i in range(n) ]
        s = sum(v); 
        if s: v = [x/s for x in v]
    return v

def text_score(qt, text):
    toks = set(tokenize(text))
    inter = toks & set(qt)
    return len(inter)/max(1,len(set(qt)))

query = "Plano para atender a Ana hoje com upsell e próxima ação"
qt = tokenize(query)

# timing
with stopwatch() as sw:
    idx, rev, adj = build_idx(nodes)
    eig = eigen_centrality(adj)
    scored = []
    for key, meta in nodes.items():
        s = 0.7*text_score(qt, meta["text"]) + 0.3*eig[idx[key]]
        scored.append((s, key, meta))
    scored.sort(reverse=True)
    top = scored[:5]
    latency = sw()

retrieved_ids = [k for _,k,_ in top]
relevant_ids = ["u:ana","e:pedido_grande_2024","d:upsell"]
p_at_3 = precision_at_k(relevant_ids, retrieved_ids, k=3)

picked_tools = [k for k in retrieved_ids if nodes[k]["type"]=="tool"] or ["t:crm","t:search"]

out = {
  "query": query,
  "top_ids": retrieved_ids,
  "precision_at_3": p_at_3,
  "latency_s": round(latency, 6),
  "picked_tools": picked_tools
}

write_json("gem_summary_v2.json", out)
print("[gem_v2] ok -> gem_summary_v2.json")
