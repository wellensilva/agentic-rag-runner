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
## Perfis (preferências)

- `default` — email/tom formal (padrão)
- `whatsapp_acolhedor` — canal WhatsApp e tom acolhedor
- `email_formal` — força email/tom formal

## Troubleshooting

- **“Expected branch to point to … Pull and try again”**  
  O app está desatualizado. Descarte a edição e reabra o arquivo (puxe para atualizar) ou crie um novo arquivo via “Add file”.

- **“No event triggers defined in on”**  
  Falta o bloco `on:` no YAML. Copie exatamente como no exemplo.

- **`ModuleNotFoundError`**  
  Confirme `requirements.txt` na raiz e a etapa **Install deps** no workflow.

## Roadmap curto

- [ ] Guardar resultados `papers` em `state/` para reuso
- [ ] Adicionar “ferramenta” de sumarização
- [ ] Testes automatizados (PyTest leve) e badges