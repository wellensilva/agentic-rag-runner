# Colaborativo IA — API FastAPI

Este projeto expõe o Orquestrador (pesquisador → sintetizador → executor) via HTTP,
com memória curta/longa, loop opcional de feedback humano e guardião de segurança.

## 1) Preparar ambiente
```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # edite OPENAI_API_KEY e (opcional) LLM_MODEL
```

## 2) Rodar a API
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Acesse a documentação interativa:
- Swagger UI: http://localhost:8000/docs
- OpenAPI JSON: http://localhost:8000/openapi.json

## 3) Teste rápido
```bash
curl -X POST http://localhost:8000/run   -H "Content-Type: application/json"   -d '{"query":"Crie um plano de MVP em 1 página para o projeto Biblioteca Viva.","formato":"texto"}'
```

## 4) Fluxo com feedback humano
- Envie um feedback separado e reaplique no próximo `/run` com o mesmo `request_id`:

```bash
curl -X POST http://localhost:8000/feedback   -H "Content-Type: application/json"   -d '{"request_id":"abc123","feedback":"Refinar seção de riscos e incluir cronograma em 3 fases."}'
curl -X POST http://localhost:8000/run   -H "Content-Type: application/json"   -d '{"query":"Plano de MVP com entregáveis", "formato":"texto","request_id":"abc123","apply_feedback":true}'
```

## 5) Memória longa (opcional)
Se `chromadb` estiver instalado, os resumos finais são persistidos em `./chroma_store`.

## 6) Segurança
O `guardian_check` bloqueia conteúdos proibidos por palavras-sinal. Amplie com suas regras.