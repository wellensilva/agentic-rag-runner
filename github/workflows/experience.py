# experience.py
# Log de experiências (cadeia de ferramentas) + autocritica simples + reuso
from __future__ import annotations
import sqlite3, re
from typing import Dict, Any, List
from memory_store import connect

def experience_log(objective: str, step: str, tool: str, input_s: str, output_s: str, ok: bool,
                   con: sqlite3.Connection = None) -> int:
    own = con or connect()
    own.execute("""INSERT INTO experiences(objective,step,tool,input,output,ok)
                   VALUES(?,?,?,?,?,?)""", (objective, step, tool, input_s, output_s, int(ok)))
    own.commit()
    return own.execute("SELECT last_insert_rowid()").fetchone()[0]

def auto_critique(objective: str, output_s: str) -> Dict[str,Any]:
    # heurística: overlap de palavras-chave do objetivo no output
    toks = lambda s: set(re.findall(r"[a-zA-ZÀ-ÿ0-9]+", s.lower()))
    o, out = toks(objective), toks(output_s)
    overlap = len(o & out) / (len(o) + 1e-6)
    ok = overlap >= 0.2
    return {"overlap": round(overlap,3), "ok": ok}

def reuse_playbook(objective_like: str, limit: int = 5, con: sqlite3.Connection = None) -> List[Dict[str,Any]]:
    own = con or connect()
    rows = own.execute("""SELECT objective, step, tool, input, output, ok, ts
                          FROM experiences
                          WHERE ok=1 AND objective LIKE ?
                          ORDER BY ts DESC LIMIT ?""", (f"%{objective_like}%", limit)).fetchall()
    return [{"objective":r[0],"step":r[1],"tool":r[2],"input":r[3],"output":r[4],"ok":bool(r[5]),"ts":r[6]}
            for r in rows]