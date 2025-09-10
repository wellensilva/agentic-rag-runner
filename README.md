# Agentic RAG Runner (N2–N3)
Pronto para rodar no **GitHub Actions** via celular.

## Como usar
1. Suba estes arquivos na raiz do repositório:
   - `runner.py`
   - `policy.yaml`
   - `.github/workflows/main.yml`
2. Vá em **Actions → agentic-rag → Run workflow**.
3. Ao terminar, baixe **Artifacts**: `logs/` (jsonl) e `outputs/` (`summary.md` + `articles.csv`).

## Ajustes rápidos
- A query está focada em **memória** e **ferramentas**. Ajuste em `policy.yaml`.
- *Kill-switch*: defina `KILL_SWITCH="PAUSAR AGORA"` nas variáveis do job para abortar.