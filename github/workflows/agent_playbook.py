# agent_playbook.py
# Orquestração mínima: planeja -> usa ferramenta -> autocritica -> loga -> (opcional) grava memória
from __future__ import annotations
from typing import Dict, Any
from memory_store import connect, upsert_memory
from experience import experience_log, auto_critique
from curator import curator_check
from retrieval import hybrid_retrieve

def plan_steps(objective: str) -> list[Dict[str,Any]]:
    # stub: decide entre recuperar contexto e usar uma "ferramenta"
    steps = [{"step":"retrieve", "tool":"memory.search", "input": objective}]
    # acrescente outras ferramentas aqui, ex: "web.search", "code.exec", etc.
    return steps

def run_step(step: Dict[str,Any]) -> str:
    if step["tool"] == "memory.search":
        res = hybrid_retrieve(step["input"])
        # compõe um "resumo" curtinho das top-3 memórias
        capsule = "\n".join([f"- ({n['score']:.2f}) {n['text'][:180]}" for n in res["nodes"][:3]])
        return capsule or "(sem memória relevante)"
    return "(tool não implementada)"

def run_objective(objective: str, persist_memory: bool = True) -> Dict[str,Any]:
    con = connect()
    timeline = []
    for s in plan_steps(objective):
        out = run_step(s)
        crit = auto_critique(objective, out)
        experience_log(objective, s["step"], s["tool"], s.get("input",""), out, crit["ok"], con)
        timeline.append({"step": s, "output": out, "critique": crit})

    # decide se memoriza algo sobre este objetivo (curadoria)
    summary = f"Objetivo: {objective}\nResultado:\n" + (timeline[-1]["output"] if timeline else "")
    verdict = curator_check(summary, con)
    mem_id = None
    if persist_memory and verdict["risk"] < 0.3 and verdict["utility"] > 0.25:
        mem_id = upsert_memory(con, summary, source="agent.play", meta={"curator": verdict})
    return {"objective": objective, "timeline": timeline, "memorized_id": mem_id}