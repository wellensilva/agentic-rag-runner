
# tests/editable_memory_stub_v2.py
import json
from tests._utils_io import read_json, write_json, stopwatch

mem_path = "state/user_memory.json"
mem = read_json(mem_path, [
  {"id":"pref.channel","key":"canal_contato","value":"email"},
  {"id":"pref.tone","key":"tom","value":"formal"},
  {"id":"pref.window","key":"janela_horario","value":"comercial"}
])

def respond(mem):
    canal = next((m["value"] for m in mem if m["key"]=="canal_contato"), "email")
    tom   = next((m["value"] for m in mem if m["key"]=="tom"), "neutro")
    jan   = next((m["value"] for m in mem if m["key"]=="janela_horario"), "qualquer")
    return {"canal":canal,"tom":tom,"janela":jan}

before = respond(mem)

# edits
edits = [
  {"op":"update","id":"pref.channel","value":"whatsapp"},
  {"op":"update","id":"pref.tone","value":"acolhedor"}
]
for op in edits:
    for m in mem:
        if m["id"]==op["id"]:
            m["value"]=op["value"]

after = respond(mem)

write_json(mem_path, mem)

out = {
  "before": before,
  "after": after,
  "adherence_ok": (after["canal"]=="whatsapp" and after["tom"]=="acolhedor")
}
write_json("editable_memory_summary_v2.json", out)
print("[edit_v2] ok -> editable_memory_summary_v2.json")
