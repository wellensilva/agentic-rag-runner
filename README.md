# Agentic RAG Runner — memória + ferramentas (Nível 2–3)

Pequeno laboratório para **agente com RAG, memória editável e cadeia de ferramentas**, rodando em **GitHub Actions** (funciona bem no celular).

## Como executar

1. Vá em **Actions → agentic-rag → Run workflow**  
2. Preencha os inputs:
   - **task**: `stub_v3` (demonstra memória) ou `papers` (busca no arXiv)
   - **profile**: `default`, `whatsapp_acolhedor` ou `email_formal`
   - **query**: texto livre (usado em `papers` e como pergunta no `stub_v3`)
3. Depois do run, baixe **Artifacts → agent-test-results** para ver:
   - `outputs/…` (resultados em JSON/MD)
   - `logs/runner.log`
   - `state/…` (memórias/KB)

## Fluxos de trabalho inclusos

- **agentic-rag** — execução principal (stubs/papers/demo)  
- **agent-tests-v2** — diagnóstico (lista arquivos, checa imports, roda testes rápidos)

## Pastas