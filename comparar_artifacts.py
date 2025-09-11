# comparar_artifacts.py
import sys, zipfile, json, csv, hashlib

FILES = [
    "gem_summary_v2.json",
    "editable_memory_summary_v2.json",
    "active_rag_summary_v2.json",
    "run_summary.json",
]

def load_json(z, name):
    try:
        with z.open(name) as f:
            return json.loads(f.read().decode("utf-8", errors="replace"))
    except:
        return None

def sha(obj):
    try:
        return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:12]
    except:
        return None

def field(o, path, default=None):
    cur = o
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur

def summarize_gem(d):
    if not d: return {}
    return {
        "precision_at_3": d.get("precision_at_3"),
        "picked_tools": ",".join(d.get("picked_tools", [])),
        "latency_ms": d.get("latency_ms"),
        "_hash": sha(d),
    }

def summarize_edit(d):
    if not d: return {}
    after = d.get("after", {}) or {}
    return {
        "adherence_ok": d.get("adherence_ok"),
        "canal": after.get("canal"),
        "tom": after.get("tom"),
        "_hash": sha(d),
    }

def summarize_active(d):
    if not d: return {}
    final = d.get("after_accommodation", {}) or {}
    return {
        "answer": final.get("answer"),
        "source": final.get("source") or final.get("doc_id"),
        "latency_ms": d.get("latency_ms"),
        "_hash": sha(d),
    }

def summarize_run(d):
    if not d: return {}
    return {
        "task": d.get("task"),
        "profile": d.get("profile"),
        "query": d.get("query"),
        "_hash": sha(d),
    }

SUMMARIZERS = {
    "gem_summary_v2.json": summarize_gem,
    "editable_memory_summary_v2.json": summarize_edit,
    "active_rag_summary_v2.json": summarize_active,
    "run_summary.json": summarize_run,
}

def main(old_zip, new_zip):
    with zipfile.ZipFile(old_zip) as z1, zipfile.ZipFile(new_zip) as z2:
        rows = []
        print("\n=== Diferenças entre artifacts ===\n")
        for name in FILES:
            d1 = load_json(z1, name)
            d2 = load_json(z2, name)
            s1 = SUMMARIZERS[name](d1) if d1 else None
            s2 = SUMMARIZERS[name](d2) if d2 else None

            if s1 is None and s2 is None:
                print(f"- {name}: ausente nos dois")
                rows.append({"Arquivo": name, "Mudou?": "não", "Antes": "", "Depois": "", "Campo": ""})
                continue
            if s1 is None:
                print(f"- {name}: **novo**")
                rows.append({"Arquivo": name, "Mudou?": "sim (novo)", "Antes": "", "Depois": json.dumps(s2, ensure_ascii=False), "Campo": ""})
                continue
            if s2 is None:
                print(f"- {name}: **removido**")
                rows.append({"Arquivo": name, "Mudou?": "sim (removido)", "Antes": json.dumps(s1, ensure_ascii=False), "Depois": "", "Campo": ""})
                continue

            # comparar campo a campo
            changed_any = False
            keys = sorted(set(s1.keys()) | set(s2.keys()))
            for k in keys:
                if s1.get(k) != s2.get(k):
                    changed_any = True
                    print(f"- {name} ▸ {k}: {s1.get(k)}  →  {s2.get(k)}")
                    rows.append({"Arquivo": name, "Mudou?": "sim", "Campo": k,
                                 "Antes": s1.get(k), "Depois": s2.get(k)})
            if not changed_any:
                print(f"- {name}: sem mudanças relevantes")
                rows.append({"Arquivo": name, "Mudou?": "não", "Campo": "", "Antes": "", "Depois": ""})

        # CSV
        with open("diff.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["Arquivo","Mudou?","Campo","Antes","Depois"])
            w.writeheader()
            w.writerows(rows)
        print("\nArquivo gerado: diff.csv\n")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python comparar_artifacts.py antigo.zip novo.zip")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
