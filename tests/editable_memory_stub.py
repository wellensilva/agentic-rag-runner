# tests/editable_memory_stub.py
import json, time, pathlib

OUT = pathlib.Path("logs"); OUT.mkdir(exist_ok=True)

mem = [
  {"id":"pref.channel","key":"canal_contato","value":"email"},
  {"id":"pref.tone","key":"tom","value":"formal"},
  {"id":"pref.window","key":"janela_horario","value":"comercial"}
]

def respond(perg, mem):
    # regra boba: resposta lê preferências e as reflete
    canal = next((m["value"] for m in mem if m["key"]=="canal_contato"), "email")
    tom   = next((m["value"] for m in mem if m["key"]=="tom"), "neutro")
    jan   = next((m["value"] for m in mem if m["key"]=="janela_horario"), "qualquer")

    return {
      "resposta": f"Vou retornar no {canal} com tom {tom} dentro do horário {jan}.",
      "mem_usada": {"canal":canal, "tom":tom, "janela":jan}
    }

before = respond("Como devo contatar o usuário?", mem)

# Edição de memória (usuário altera preferências)
edit_ops = [
  {"op":"update","id":"pref.channel","value":"whatsapp"},
  {"op":"update","id":"pref.tone","value":"acolhedor"}
]
for op in edit_ops:
    for m in mem:
        if m["id"]==op["id"]:
            m["value"]=op["value"]

after = respond("Como devo contatar o usuário?", mem)

summary = {
  "before": before,
  "edits": edit_ops,
  "after":  after,
  "adherence_ok": (after["mem_usada"]["canal"]=="whatsapp" and after["mem_usada"]["tom"]=="acolhedor"),
  "ts": time.time()
}

path = pathlib.Path("editable_memory_summary.json")
path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"[edit] ok -> {path}")