# resumo_artifact.py
import sys, zipfile, json, csv, io

def safe_json(z, name):
    try:
        with z.open(name) as f:
            return json.loads(f.read().decode("utf-8", errors="replace"))
    except:
        return None

def add(rows, modulo, ok, detalhes):
    rows.append({"Módulo": modulo, "OK": "sim" if ok else "não", "Detalhes": detalhes})

def main(path):
    with zipfile.ZipFile(path, "r") as z:
        names = set(z.namelist())

        rows = []
        print("\n=== Resumo do artifact ===\n")

        # GEM-RAG v2
        gs = safe_json(z, "gem_summary_v2.json")
        if gs:
            p = gs.get("precision_at_3")
            tools = ", ".join(gs.get("picked_tools", []))
            lat = gs.get("latency_ms")
            detalhes = f"precision@3={p} • ferramentas={tools} • latência={lat}ms"
            add(rows, "GEM-RAG (v2)", True, detalhes)
            print("GEM-RAG (v2):", detalhes)
        else:
            add(rows, "GEM-RAG (v2)", False, "gem_summary_v2.json não encontrado")
            print("GEM-RAG (v2): gem_summary_v2.json não encontrado")

        # Editable Memory v2
        em = safe_json(z, "editable_memory_summary_v2.json")
        if em:
            after = em.get("after", {})
            ok = bool(em.get("adherence_ok", False))
            detalhes = f"canal={after.get('canal')} • tom={after.get('tom')} • adherence_ok={ok}"
            add(rows, "Editable-Memory (v2)", ok, detalhes)
            print("Editable-Memory (v2):", detalhes)
        else:
            add(rows, "Editable-Memory (v2)", False, "editable_memory_summary_v2.json não encontrado")
            print("Editable-Memory (v2): editable_memory_summary_v2.json não encontrado")

        # Active RAG v2
        ar = safe_json(z, "active_rag_summary_v2.json")
        if ar:
            final = ar.get("after_accommodation", {}) or {}
            src = final.get("source") or final.get("doc_id")
            lat = ar.get("latency_ms")
            detalhes = f"final={final.get('answer')} • fonte={src} • latência={lat}ms"
            add(rows, "Active-RAG (v2)", True, detalhes)
            print("Active-RAG (v2):", detalhes)
        else:
            add(rows, "Active-RAG (v2)", False, "active_rag_summary_v2.json não encontrado")
            print("Active-RAG (v2): active_rag_summary_v2.json não encontrado")

        # Extras
        rs = safe_json(z, "run_summary.json")
        if rs:
            print("\nrun_summary.json:", rs)

        # CSV
        with open("resumo.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["Módulo","OK","Detalhes"])
            w.writeheader()
            w.writerows(rows)
        print("\nArquivo gerado: resumo.csv")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python resumo_artifact.py agent-test-results.zip")
        sys.exit(1)
    main(sys.argv[1])
