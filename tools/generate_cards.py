# tools/generate_cards.py
from pathlib import Path
import json, textwrap, datetime as dt

def _mk(out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)

def _short(s, n=800):
    s = (s or "").strip().replace("\n", " ")
    return (s[:n] + "…") if len(s) > n else s

def build_markdown(papers: list) -> str:
    lines = []
    today = dt.date.today().isoformat()
    lines.append(f"# Cartões de Ação — Agentic RAG (papers)  \n_Gerado em {today}_\n")

    for i, p in enumerate(papers, 1):
        title   = p.get("title","").strip()
        authors = ", ".join(p.get("authors", []))
        date    = p.get("published","")
        pdf     = p.get("pdf","")
        abs_url = p.get("abs_url","")
        summary = _short(p.get("summary",""))

        lines += [
            f"## {i}. {title}",
            f"- **Autores:** {authors}",
            f"- **Data:** {date}",
            f"- **Links:** " + " | ".join([x for x in [f"[PDF]({pdf})" if pdf else "", f"[arXiv]({abs_url})" if abs_url else ""] if x]) or "—",
            "",
            "**Essência (1 linha):**",
            f"> {_short(summary, 280)}",
            "",
            "**Ações sugeridas:**",
            "- [ ] Extrair ideias acionáveis p/ memória (`state/memory.json`)",
            "- [ ] Propor mini-experimento (toolchain) a partir do paper",
            "- [ ] Atualizar `state/policies.json` se houver implicações",
            "- [ ] Registrar follow-up (perguntas para o time)",
            "",
            "**Riscos/limites:**",
            "- [ ] Anote trade-offs, vieses e ameaças ao uso prático",
            "",
            "---",
            ""
        ]
    return "\n".join(lines)

def main(in_json="outputs/papers.json", out_md="outputs/cards.md"):
    out_dir = Path("outputs")
    _mk(out_dir)
    p_in  = Path(in_json)
    p_out = Path(out_md)

    papers = []
    if p_in.exists():
        papers = json.loads(p_in.read_text(encoding="utf-8"))

    md = build_markdown(papers)
    p_out.write_text(md, encoding="utf-8")
    print(f"[cards] salvo em {p_out}")

if __name__ == "__main__":
    main()
