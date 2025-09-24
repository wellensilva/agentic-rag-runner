$ErrorActionPreference = "Stop"
$PORT = $env:PORT; if (-not $PORT) { $PORT = 8000 }
$BASE = "http://localhost:$PORT"

Write-Host "==[1/7]== Ativando venv e instalando dependências"
if (-not (Test-Path ".\.venv")) {
  python -m venv .venv
}
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

if (-not (Test-Path ".env")) {
  Write-Host "⚠️  .env não encontrado. Copiando .env.example..."
  Copy-Item ".env.example" ".env" -ErrorAction SilentlyContinue
}
if (-not (Get-Content .env | Select-String -Pattern "^OPENAI_API_KEY=")) {
  throw "Abra .env e preencha OPENAI_API_KEY antes de continuar."
}

Write-Host "==[2/7]== Subindo a API no background (porta $PORT)"
# Fecha uvicorn antigo
Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Process -FilePath "python" -ArgumentList "-m","uvicorn","app:app","--host","0.0.0.0","--port",$PORT,"--reload" -NoNewWindow
Start-Sleep -Seconds 2

Write-Host "==[3/7]== Aguardando /health ficar OK"
$ok = $false
for ($i=0; $i -lt 40; $i++) {
  try {
    $h = Invoke-RestMethod "$BASE/health" -TimeoutSec 2
    if ($h.ok -eq $true) { $ok = $true; break }
  } catch { Start-Sleep -Milliseconds 500 }
}
if (-not $ok) { throw "Healthcheck falhou." }
Invoke-RestMethod "$BASE/health" | ConvertTo-Json

Write-Host "==[4/7]== Teste /run (JSON)"
$body = '{"query":"Crie um plano de MVP em 1 página para o projeto Biblioteca Viva.","formato":"texto"}'
$out = Invoke-RestMethod -Method Post -Uri "$BASE/run" -ContentType "application/json" -Body $body
$out | ConvertTo-Json -Depth 5 | Tee-Object -FilePath "out_run.json" | Out-String | Select-Object -First 50

Write-Host "==[5/7]== Teste /run_pdf (gera colabIA_resultado.pdf)"
Invoke-WebRequest -Method Post -Uri "$BASE/run_pdf" -ContentType "application/json" -Body $body -OutFile "colabIA_resultado.pdf"
if (-not (Test-Path ".\colabIA_resultado.pdf")) { throw "Falha ao gerar PDF" } else { Write-Host "✅ PDF gerado: colabIA_resultado.pdf" }

Write-Host "==[6/7]== Subindo política vigente no RAG e consultando"
$kb = '{
  "doc_id": "pol.2025.fretes.v2",
  "text": "Política de fretes — vigente (2025 v2):\n• Frete grátis para pedidos ≥ R$350\n• Prazo de entrega: 2–3 dias\n• Fonte: pol.2025.fretes.v2\n• Validade: até nova atualização",
  "meta": {"kind":"policy","year":"2025","version":"v2"}
}'
try {
  $kb_resp = Invoke-RestMethod -Method Post -Uri "$BASE/kb_upsert" -ContentType "application/json" -Body $kb
  $kb_resp | ConvertTo-Json | Set-Content "out_kb_upsert.json"
} catch {
  Write-Host "ℹ️  kb_upsert falhou (ChromaDB pode estar desabilitado). Pulando..."
}

Invoke-WebRequest -Method Post -Uri "$BASE/run_pdf" -ContentType "application/json" `
  -Body '{"query":"Qual é a política de fretes e prazo?","formato":"texto"}' -OutFile "colabIA_fretes.pdf"
if (-not (Test-Path ".\colabIA_fretes.pdf")) { throw "Falha ao gerar PDF de fretes" } else { Write-Host "✅ PDF fretes: colabIA_fretes.pdf" }

Write-Host "==[7/7]== Plano para atender a Ana (upsell)"
$ana = Invoke-RestMethod -Method Post -Uri "$BASE/run" -ContentType "application/json" `
  -Body '{"query":"Plano para atender a Ana hoje com upsell e próxima ação","formato":"texto"}'
$ana | ConvertTo-Json -Depth 5 | Tee-Object -FilePath "out_ana.json" | Out-String | Select-Object -First 50

Write-Host "🌟 Tudo pronto! Arquivos: out_run.json, colabIA_resultado.pdf, out_kb_upsert.json, colabIA_fretes.pdf, out_ana.json"
