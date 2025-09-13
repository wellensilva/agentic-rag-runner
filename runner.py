# runner.py — Agentic RAG mini-runner (stub_v3 / papers / demo)
# - CLI: --task / --profile / --query (ou env TASK/PROFILE/QUERY)
# - Pastas: outputs/, logs/, state/
# - Memória short/mid/long (state/memory.json)
# - Self-RAG gate (heurístico)
# - Loop ReAct minimalista (tools: arxiv, memory.read/write, crm.log)
# - Tarefas: stub_v3, papers (arXiv), demo
#
# Requisitos (já instalados no workflow):
#   arxiv, requests, beautifulsoup4, feedparser, pyyaml, tenacity

import json, os, sys, datetime, pathlib, logging, argparse
from typing import List, Dict, Any

# opcional (só é usado em task_papers/tool_search_arxiv)
try:
    import arxiv
except Exception:
    arxiv = None

BASE = pathlib.Path(".")
DIR_OUT = BASE / "outputs"
DIR_LOG = BASE / "logs"
DIR_STATE = BASE / "state"
for p in (DIR_OUT, DIR_LOG, DIR_STATE):
    p.mkdir(parents=True, exist_ok=True)

LOG_FILE = DIR_LOG / "run.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
)

def now_ts():
    return datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"

# ---------- Memória (short / mid / long) ----------
STATE_JSON = DIR_STATE / "memory.json"

def _load_state() -> Dict[str, Any]:
    if STATE_JSON.exists():
        try:
            return json.loads(STATE_JSON.read_text(encoding="utf-8"))
        except Exception:
            logging.exception("Falha ao ler memory.json; recriando.")
    return {"short": [], "mid": [], "long": {"prefs": {}, "facts": {}}}

def _save_state(st: Dict[str, Any]):
    STATE_JSON.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")

def memory_append_short(msg: str):
    st = _load_state()
    st["short"].append({"ts": now_ts(), "msg": msg})
    st["short"] = st["short"][-20:]  # mantém buffer curto
    _save_state(st)

def memory_add_lesson(lesson: str, utility: float):
    """Memória de médio prazo com 'score' e poda simples."""
    st = _load_state()
    st["mid"].append({"ts": now_ts(), "lesson": lesson, "utility": float(utility)})
    st["mid"] = sorted(st["mid"], key=lambda x: x["utility"], reverse=True)[:50]
    _save_state(st)

def prefs_get() -> Dict[str, Any]:
    return _load_state()["long"].get("prefs", {})

def prefs_update(**kv):
    st = _load_state()
    p = st["long"].get("prefs", {})
    p.update({k: v for k, v in kv.items() if v is not None})
    st["long"]["prefs"] = p
    _save_state(st)

# ---------- Perfis ----------
PROFILES = {
    "default": {"channel": "email", "tone": "neutro"},
    "whatsapp_acolhedor": {"channel": "whatsapp", "tone": "acolhedor"},
    "email_formal": {"channel": "email", "tone": "formal"},
}

def apply_profile(name: str):
    prof = PROFILES.get(name, PROFILES["default"])
    prefs_update(**prof)
    return prof

# ---------- Self-RAG gate (heurístico) ----------
def needs_retrieval(question: str, kb_hits: int, conf_gate: float = 0.6) -> bool:
    """
    Gate simples: se poucas evidências locais OU pergunta longa/específica → buscar fora.
    """
    if not question:
        return False
    specificity = min(len(question) / 80.0, 1.0)
    local_signal = 1.0 if kb_hits >= 1 else 0.2
    score = 0.5 * specificity + 0.5 * (1 - local_signal)
    want = score >= (1 - conf_gate)
    logging.info(f"[self-rag] question='{question[:60]}' kb_hits={kb_hits} specificity={specificity:.2f} gate={want}")
    return want

# ---------- Ferramentas (para ReAct) ----------
def tool_search_arxiv(query: str, k: int = 3) -> List[Dict[str, Any]]:
    items = []
    if arxiv is None:
        logging.warning("arxiv não instalado; pulando busca.")
        return items
    search = arxiv.Search(query=query, max_results=k, sort_by=arxiv.SortCriterion.Relevance)
    for r in arxiv.Client().results(search):
        items.append({
            "title": r.title,
            "authors": [a.name for a in r.authors],
            "date": r.published.date().isoformat(),
            "pdf": r.pdf_url,
            "abs": r.entry_id
        })
    logging.info(f"[tool:arxiv] {len(items)} achados para '{query}'")
    return items

def tool_crm_log(note: str):
    path = DIR_OUT / "crm_log.json"
    log = []
    if path.exists():
        log = json.loads(path.read_text(encoding="utf-8"))
    log.append({"ts": now_ts(), "note": note, "prefs": prefs_get()})
    path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    logging.info("[tool:crm] anotado.")

def tool_memory_write(key: str, value: Any):
    prefs_update(**{key: value})
    logging.info(f"[tool:memory.write] {key}={value}")

def tool_memory_read(key: str) -> Any:
    return prefs_get().get(key)

# ---------- ReAct loop (mínimo viável) ----------
def react_plan_and_act(goal: str, max_steps: int = 3) -> Dict[str, Any]:
    trace = []
    for step in range(1, max_steps + 1):
        thought = f"Passo {step}: Para '{goal}', checar memória e, se preciso, buscar apoio externo."
        action = None
        result = None
        # heurística simples de escolha de ferramenta
        if "upsell" in goal.lower() and step == 1:
            action = ("memory.read", "tone")
            result = tool_memory_read("tone") or "desconhecido"
        elif "plano" in goal.lower() and step <= 2:
            action = ("crm.log", f"Preparar oferta personalizada ({prefs_get().get('tone','neutro')})")
            tool_crm_log(action[1]); result = "anotado"
        else:
            action = ("search.arxiv", "agent tool memory")
            result = tool_search_arxiv(action[1], k=1)
        trace.append({"thought": thought, "action": action, "result": result})
    return {"goal": goal, "trace": trace}

# ---------- Tasks ----------
def task_stub_v3(profile: str, query: str = "") -> Dict[str, Any]:
    logging.info("[task] stub_v3")
    prof = apply_profile(profile)

    # mini-KB com versões de política (simulação de assimilação/acomodação)
    kb = []

    def answer(q: str) -> Dict[str, Any]:
        if not kb:
            return {"answer": "Sem política definida."}
        latest = sorted(kb, key=lambda x: x["ts"])[-1]
        return {"answer": f"Política vigente: frete grátis acima de R${latest['min']}, prazo {latest['prazo']}."}

    q = "Qual é a política de fretes e prazo?"
    a0 = answer(q)  # inicial (vazio)

    # assimilar v1
    kb.append({"id":"pol.2025.fretes.v1","ts":"2025-01-10","min":400,"prazo":"2–4 dias"})
    a1 = answer(q)

    # acomodar v2
    kb.append({"id":"pol.2025.fretes.v2","ts":"2025-03-05","min":350,"prazo":"2–3 dias"})
    a2 = answer(q)

    # gate & react demo
    gate = needs_retrieval(q, kb_hits=1)
    react = react_plan_and_act("Plano para atender a Ana hoje com upsell e próxima ação", max_steps=3)

    out = {
        "profile_applied": prof,
        "qa": {
            "question": q,
            "initial": a0,
            "after_assimilation": a1,
            "after_accommodation": a2
        },
        "gate_would_search": gate,
        "react_trace": react["trace"],
    }
    (DIR_OUT/"stub_v3.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    memory_add_lesson("Responder políticas com versão mais recente e registrar próxima ação", 0.85)
    return out

def task_papers(profile: str, query: str) -> Dict[str, Any]:
    logging.info("[task] papers")
    apply_profile(profile)
    if not query:
        query = "agentic rag memory toolchain"
    items = tool_search_arxiv(query, k=5)
    (DIR_OUT/"papers.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"query": query, "results": items}

def task_demo(profile: str, query: str) -> Dict[str, Any]:
    logging.info("[task] demo")
    apply_profile(profile)
    react = react_plan_and_act(query or "Preparar atendimento padrão", max_steps=2)
    (DIR_OUT/"demo.json").write_text(json.dumps(react, ensure_ascii=False, indent=2), encoding="utf-8")
    return react

TASKS = {
    "stub_v3": task_stub_v3,
    "papers": task_papers,
    "demo": task_demo,
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", default=os.getenv("TASK","stub_v3"))
    parser.add_argument("--profile", default=os.getenv("PROFILE","default"))
    parser.add_argument("--query", default=os.getenv("QUERY",""))
    args = parser.parse_args()

    task = TASKS.get(args.task)
    if not task:
        raise SystemExit(f"Tarefa desconhecida: {args.task}. Opções: {list(TASKS)}")

    logging.info(f"=== runner start :: task={args.task} profile={args.profile} ===")
    result = task(args.profile, args.query)

    summary = {
        "ts": now_ts(),
        "task": args.task,
        "profile": args.profile,
        "query": args.query,
        "result_keys": list(result.keys()),
    }
    (DIR_OUT/"summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    logging.info("OK. Artefatos em outputs/, logs/, state/.")

if __name__ == "__main__":
    main()