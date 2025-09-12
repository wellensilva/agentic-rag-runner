
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
# Stub v3 — Memória + Preferências + Mini-KB com versões

**Objetivo:** demonstrar um agente “didático” com:
- **Mini base de conhecimento** versionada (v1 → v2 → …) e respostas que seguem a **linha do tempo**.
- **Memória de preferências** do usuário (canal, tom da mensagem etc.) que podem ser **editadas** em tempo real.

## Como rodar
Use o workflow **agentic-rag**:
- `task`: `stub_v3`
- `profile`: `default` | `whatsapp_acolhedor` | `email_formal`
- `query`: (opcional) uma pergunta; por padrão usamos “Qual é a política de fretes e prazo?”

## O que ele faz
1. Carrega/gera uma mini-KB (ex.: política de frete).
2. **Assimilate**: adiciona uma nova versão (ex.: v1 → v2).
3. **Accommodate**: ajusta a resposta à nova versão.
4. **Preferências**: grava/edita canal e tom (ex.: WhatsApp + acolhedor).
5. Escreve tudo em `outputs/` e estados em `state/`.

## Saídas
- `outputs/stub_v3_*.json` — respostas passo a passo:
  - `initial`, `after_assimilation`, `after_accommodation`
- `state/memory_store.sqlite` (ou `.json`) — preferências salvas
- `logs/runner.log` — execução

## Exemplos de uso
- **Pergunta:** “Qual é a política de fretes e prazo?”
- **Linha do tempo esperada:**
  - Inicial: frete grátis R$300 / 3–5 dias
  - Após v1: R$400 / 2–4 dias
  - Após v2: R$350 / 2–3 dias
- **Preferências:** `whatsapp_acolhedor` → respostas saem “no WhatsApp” e com tom acolhedor.

> Este stub é para **diagnóstico e treino** de memória/autonomia controlada (nível 2–3). Não depende de serviços externos.