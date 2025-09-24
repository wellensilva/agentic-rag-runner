#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8000}"
HOST="0.0.0.0"
BASE="http://localhost:${PORT}"

echo "==[1/7]== Ativando venv e instalando dependências"
if [ ! -d ".venv" ]; then
  python -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f ".env" ]; then
  echo "⚠️  .env não encontrado. Copiando .env.example..."
  cp .env.example .env || true
fi

if ! grep -q "OPENAI_API_KEY=" .env; then
  echo "⚠️  Abra o arquivo .env e preencha o OPENAI_API_KEY antes de continuar."
  exit 1
fi

echo "==[2/7]== Subindo a API no background (porta ${PORT})"
# Mata uvicorn antigo (se existir)
pkill -f "uvicorn app:app" 2>/dev/null || true
uvicorn app:app --host "${HOST}" --port "${PORT}" --reload > uvicorn.log 2>&1 &
UV_PID=$!
echo "PID do uvicorn: $UV_PID"

echo "==[3/7]== Aguardando /health ficar OK"
RETRIES=40
until curl -sf "${BASE}/health" >/dev/null || [ $RETRIES -eq 0 ]; do
  sleep 0.5
  RETRIES=$((RETRIES-1))
done
curl -s "${BASE}/health" && echo

echo "==[4/7]== Teste /run (JSON)"
curl -s -X POST "${BASE}/run" \
  -H "Content-Type: application/json" \
  -d '{"query":"Crie um plano de MVP em 1 página para o projeto Biblioteca Viva.","formato":"texto"}' \
  | tee out_run.json | head -c 800 && echo -e "\n…(JSON completo salvo em out_run.json)"

echo "==[5/7]== Teste /run_pdf (gera colabIA_resultado.pdf)"
curl -s -X POST "${BASE}/run_pdf" \
  -H "Content-Type: application/json" \
  -d '{"query":"Crie um plano de MVP em 1 página para o projeto Biblioteca Viva.","formato":"texto"}' \
  --output colabIA_resultado.pdf
[ -s colabIA_resultado.pdf ] && echo "✅ PDF gerado: colabIA_resultado.pdf" || (echo "❌ Falha ao gerar PDF" && exit 1)

echo "==[6/7]== Subindo política vigente no RAG e consultando"
# Upsert KB
curl -s -X POST "${BASE}/kb_upsert" \
  -H "Content-Type: application/json" \
  -d '{
    "doc_id": "pol.2025.fretes.v2",
    "text": "Política de fretes — vigente (2025 v2):\n• Frete grátis para pedidos ≥ R$350\n• Prazo de entrega: 2–3 dias\n• Fonte: pol.2025.fretes.v2\n• Validade: até nova atualização",
    "meta": {"kind":"policy","year":"2025","version":"v2"}
  }' | tee out_kb_upsert.json && echo
# Pergunta que deve usar essa política
curl -s -X POST "${BASE}/run_pdf" \
  -H "Content-Type: application/json" \
  -d '{"query":"Qual é a política de fretes e prazo?","formato":"texto"}' \
  --output colabIA_fretes.pdf
[ -s colabIA_fretes.pdf ] && echo "✅ PDF fretes: colabIA_fretes.pdf" || (echo "❌ Falha ao gerar PDF de fretes" && exit 1)

echo "==[7/7]== Plano para atender a Ana (upsell)"
curl -s -X POST "${BASE}/run" \
  -H "Content-Type: application/json" \
  -d '{"query":"Plano para atender a Ana hoje com upsell e próxima ação","formato":"texto"}' \
  | tee out_ana.json | head -c 800 && echo -e "\n…(JSON completo salvo em out_ana.json)"

echo "== Encerrando servidor"
kill "${UV_PID}" 2>/dev/null || true
echo "🌟 Tudo pronto! Arquivos gerados: out_run.json, colabIA_resultado.pdf, out_kb_upsert.json, colabIA_fretes.pdf, out_ana.json"