curl -X POST http://localhost:8000/kb_upsert \
  -H "Content-Type: application/json" \
  -d '{
    "doc_id": "pol.2025.fretes.v2",
    "text": "Política de fretes — vigente (2025 v2):\n• Frete grátis para pedidos ≥ R$350\n• Prazo de entrega: 2–3 dias\n• Fonte: pol.2025.fretes.v2\n• Validade: até nova atualização",
    "meta": {"kind":"policy","year":"2025","version":"v2"}
  }'