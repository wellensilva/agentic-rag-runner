import json, time, pathlib, datetime

STATE = pathlib.Path("state")
STATE.mkdir(parents=True, exist_ok=True)
KB_PATH = STATE / "kb_fretes.json"
PREF_PATH = STATE / "preferences.json"

def _now():
    return datetime.datetime.utcnow().isoformat()

def read_json(p, default):
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return default

def write_json(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def bootstrap_kb():
    kb = read_json(KB_PATH, [])
    if not kb:
        kb = [
            {"id": "pol.2024.fretes.v0", "ts": "2024-12-01", "text": "Frete grátis acima de R$300; prazo 3–5 dias."}
        ]
        write_json(KB_PATH, kb)
    return kb

def query_kb(q, kb):
    hits = [d for d in kb if any(w in d["text"].lower() for w in ["frete","prazo","dias","r$"])]
    hits.sort(key=lambda d: d["ts"], reverse=True)
    return hits[:1]

def answer(q, kb):
    top = query_kb(q, kb)
    if not top:
        return {"answer": "Sem política vigente."}
    return {"answer": f"Política vigente: {top[0]['text']}"}

def run(profile="default", query=""):
    kb = bootstrap_kb()
    a0 = answer(query, kb)

    # Assimilation (nova versão v1)
    assim = {"id":"pol.2025.fretes.v1","ts":"2025-01-10","text":"Frete grátis acima de R$400; prazo 2–4 dias."}
    kb.append(assim)
    a1 = answer(query, kb)

    # Accommodation (nova versão v2)
    acomo = {"id":"pol.2025.fretes.v2","ts":"2025-02-25","text":"Frete grátis acima de R$350; prazo 2–3 dias."}
    kb.append(acomo)
    a2 = answer(query, kb)

    write_json(KB_PATH, kb)

    # Preferências (memória editável)
    prefs = read_json(PREF_PATH, {"canal":"email","tom":"formal","janela":"horario_comercial"})
    if profile == "whatsapp_acolhedor":
        prefs.update({"canal":"whatsapp", "tom":"acolhedor"})
    elif profile == "email_formal":
        prefs.update({"canal":"email", "tom":"formal"})
    write_json(PREF_PATH, prefs)

    # Planejamento estilo GEM (simples)
    plano = [
        "Revisar CRM da cliente Ana",
        "Buscar ofertas e políticas atualizadas",
        f"Contato via {prefs['canal']} em tom {prefs['tom']} com brinde e agendar follow-up"
    ]

    return {
        "question": query,
        "policy": {"initial": a0, "after_assimilation": a1, "after_accommodation": a2, "kb_versions": len(kb)},
        "preferences_after": prefs,
        "plan": plano,
        "ts": _now()
    }