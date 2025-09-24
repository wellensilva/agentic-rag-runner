curl -X POST http://localhost:8000/kb_upsert \
  -H "Content-Type: application/json" \
  -d '{
    "doc_id": "pol.2025.fretes.v2",
    "text": "Política de fretes — vigente (2025 v2):\n• Frete grátis para pedidos ≥ R$350\n• Prazo de entrega: 2–3 dias\n• Fonte: pol.2025.fretes.v2\n• Validade: até nova atualização",
    "meta": {"kind":"policy","year":"2025","version":"v2"}
curl -X POST http://localhost:8000/kb_query \
  -H "Content-Type: application/json" \
  -d '{"query":"frete grátis e prazo de entrega", "k": 3}'
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"query":"Qual é a política de fretes e prazo?", "formato":"texto"}'
curl -X POST http://localhost:8000/tool/crm_upsert \
  -H "Content-Type: application/json" \
  -d '{
    "id":"cliente-002",
    "nome":"Beatriz",
    "canal_preferido":"whatsapp",
    "ticket_medio": 920.0,
    "ultimo_pedido":"2025-09-10",
    "notas":"Prefere mensagem curta no WhatsApp. Boa resposta a kits de amostra."
  }'
curl -X POST http://localhost:8000/tool/crm_lookup \
  -H "Content-Type: application/json" \
  -d '{"nome":"Ana"}'
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"query":"Plano para atender a Ana hoje com upsell e próxima ação","formato":"texto"}'
