import os
import json
from typing import List, Dict, Any, Tuple, Optional
import io
from typing import Optional
from fastapi import Depends, Header, Request
from fastapi.staticfiles import StaticFiles
from fpdf import FPDF
from fastapi.responses import StreamingResponse
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL = os.getenv("LLM_MODEL", "gpt-4.1")
if not OPENAI_API_KEY:
    raise RuntimeError("Defina OPENAI_API_KEY no ambiente (.env)")

# OpenAI SDK >= 1.x
from openai import OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# ===== Memória (curta + longa via ChromaDB opcional) =====
try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMA_AVAILABLE = True
except Exception:
    CHROMA_AVAILABLE = False

class Memory:
    def __init__(self, collection_name: str = "colabIA"):
        self.short_context: List[str] = []
        self.max_short = 10
        if CHROMA_AVAILABLE:
            self.chroma_client = chromadb.PersistentClient(path="./chroma_store")
            self.emb_fn = embedding_functions.DefaultEmbeddingFunction()
            self.collection = self.chroma_client.get_or_create_collection(
                name=collection_name, embedding_function=self.emb_fn
            )
        else:
            self.collection = None

    def push_short(self, text: str):
        self.short_context.append(text)
        if len(self.short_context) > self.max_short:
            self.short_context.pop(0)

    def add_long(self, doc_id: str, text: str, meta: Dict[str, Any] = None):
        if not CHROMA_AVAILABLE:
            raise RuntimeError("ChromaDB indisponível no momento.")
        self.collection.add(
            documents=[text],
            metadatas=[meta or {}],
            ids=[doc_id],
        )

    def update_long(self, doc_id: str, text: str, meta: Dict[str, Any] = None):
        """upsert simplificado (remove + add)"""
        if not CHROMA_AVAILABLE:
            raise RuntimeError("ChromaDB indisponível no momento.")
        try:
            self.collection.delete(ids=[doc_id])
        except Exception:
            pass
        self.add_long(doc_id, text, meta)

    def retrieve_long(self, query: str, k: int = 3) -> List[str]:
        if not CHROMA_AVAILABLE:
            return []
        res = self.collection.query(query_texts=[query], n_results=k)
        return res.get("documents", [[]])[0] if res else []

    def context_block(self, query: str) -> str:
        long_hits = self.retrieve_long(query, k=3)
        short = "\n".join(self.short_context[-self.max_short:])
        longb = "\n".join(long_hits)
        return f"## CONTEXTO CURTO\n{short}\n\n## CONTEXTO LONGO\n{longb}".strip()

# ===== Feedback store (para /run com request_id) =====
class FeedbackStore:
    def __init__(self):
        self._store: Dict[str, str] = {}
    def set(self, request_id: str, feedback: str):
        self._store[request_id] = feedback
    def pop(self, request_id: str) -> str:
        return self._store.pop(request_id, "")

HF = FeedbackStore()

# ===== Prompts e chamada LLM =====
SYSTEM_SAFETY = (
    "Você é um assistente colaborativo. Explique em passos, "
    "verifique contradições e cite referências quando possível. "
    "Prefira responder em tom acolhedor e estilo WhatsApp durante horário comercial, "
    "salvo instrução em contrário. "
    "Nunca exponha chaves, credenciais, exploits ou quebre políticas."
)

def call_llm(messages: List[Dict[str, str]], temperature: float = 0.4) -> str:
    resp = client.chat.completions.create(
        model=MODEL, temperature=temperature, messages=messages
    )
    return resp.choices[0].message.content

def role_pesquisador(query: str, memory_block: str) -> str:
    prompt = [
        {"role": "system", "content": SYSTEM_SAFETY},
        {"role": "user", "content": (
            f"[PAPEL: PESQUISADOR]\n"
            f"Pergunta/Tarefa: {query}\n\n"
            f"{memory_block}\n\n"
            "Tarefa: gere pontos-chave e possíveis fontes. "
            "Saída em tópicos curtos e objetivos."
        )}
    ]
    return call_llm(prompt)

def role_sintetizador(pesquisa: str) -> str:
    prompt = [
        {"role": "system", "content": SYSTEM_SAFETY},
        {"role": "user", "content": (
            f"[PAPEL: SINTETIZADOR]\n"
            f"Notas do pesquisador:\n{pesquisa}\n\n"
            "Tarefa: consolidar em um esboço com seções e subtítulos, "
            "deixando claro o raciocínio em passos."
        )}
    ]
    return call_llm(prompt)

def role_executor(esboco: str, formato: str = "texto") -> str:
    prompt = [
        {"role": "system", "content": SYSTEM_SAFETY},
        {"role": "user", "content": (
            f"[PAPEL: EXECUTOR]\n"
            f"Esboço a implementar:\n{esboco}\n\n"
            f"Formato de saída: {formato}.\n"
            "Tarefa: produzir a versão final coerente, pronta para uso."
        )}
    ]
    return call_llm(prompt, temperature=0.5)

# ===== Guardião (policy) =====
def guardian_check(text: str) -> Tuple[bool, str]:
    banned = ["exploit", "malware", "doxxing", "private key", "senha="]
    for b in banned:
        if b.lower() in text.lower():
            return False, f"Conteúdo bloqueado por política ('{b}')."
    return True, "OK"

# ===== Modelos Pydantic =====
class RunRequest(BaseModel):
    query: str
    formato: str = "texto"
    request_id: Optional[str] = None
    apply_feedback: bool = True

class FeedbackRequest(BaseModel):
    request_id: str
    feedback: str

class RunResponse(BaseModel):
    status: str
    pesquisa: Optional[str] = None
    esboco: Optional[str] = None
    resultado: Optional[str] = None
    resumo: Optional[str] = None
    blocked_step: Optional[str] = None
    reason: Optional[str] = None

# ===== Auth por token (Bearer) =====
API_ACCESS_TOKEN = os.getenv("API_ACCESS_TOKEN", "")  # defina no .env (opcional)

class _Auth:
    def __call__(self, authorization: Optional[str] = Header(None)):
        # Se não houver token configurado, não exige auth (modo aberto)
        if not API_ACCESS_TOKEN:
            return True
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing Bearer token.")
        token = authorization.split(" ", 1)[1].strip()
        if token != API_ACCESS_TOKEN:
            raise HTTPException(status_code=401, detail="Invalid token.")
        return True

auth_required = _Auth()
# --- KB upsert ---
class KBUpsertReq(BaseModel):
    doc_id: str
    text: str
    meta: Optional[Dict[str, Any]] = None

class KBUpsertResp(BaseModel):
    ok: bool
    doc_id: str
    chroma_enabled: bool

class KBQueryReq(BaseModel):
    query: str
    k: int = 3

class KBQueryResp(BaseModel):
    ok: bool
    docs: List[str]
    chroma_enabled: bool

# --- CRM tool (stub) ---
class CRMRecord(BaseModel):
    id: str
    nome: str
    canal_preferido: str = "whatsapp"
    ticket_medio: float = 0.0
    ultimo_pedido: Optional[str] = None
    notas: Optional[str] = None

class CRMLookupReq(BaseModel):
    id: Optional[str] = None
    nome: Optional[str] = None

class CRMLookupResp(BaseModel):
    ok: bool
    record: Optional[CRMRecord] = None

# ===== APP =====
app = FastAPI(title="Colaborativo IA API", version="1.1.0")
MEM = Memory()

from starlette.middleware.base import BaseHTTPMiddleware
import time, logging
logging.basicConfig(level=logging.INFO)

class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        t0 = time.time()
        resp = await call_next(request)
        dt = (time.time()-t0)*1000
        logging.info(f'{request.method} {request.url.path} {resp.status_code} {dt:.1f}ms')
        return resp

app.add_middleware(AccessLogMiddleware)

# Banco de dados CRM simples em memória (stub)
CRM_DB: Dict[str, CRMRecord] = {
    "ana-001": CRMRecord(
        id="ana-001",
        nome="Ana",
        canal_preferido="whatsapp",
        ticket_medio=780.0,
        ultimo_pedido="2024-09-10",
        notas="Gosta de amostras/brindes; respondeu bem a upsell."
    )
}

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/feedback")
def set_feedback(req: FeedbackRequest):
    HF.set(req.request_id, req.feedback)
    return {"ok": True}

@app.post("/run", response_model=RunResponse)
def run(req: RunRequest):
    # 1) contexto
    ctx = MEM.context_block(req.query)

    # 2) pesquisador
    draft_pesq = role_pesquisador(req.query, ctx)
    MEM.push_short(f"[pesquisador]\n{draft_pesq}")
    ok, why = guardian_check(draft_pesq)
    if not ok:
        return RunResponse(status="blocked", blocked_step="pesquisador", reason=why)

    # 3) sintetizador
    draft_synth = role_sintetizador(draft_pesq)
    MEM.push_short(f"[sintetizador]\n{draft_synth}")
    ok, why = guardian_check(draft_synth)
    if not ok:
        return RunResponse(status="blocked", blocked_step="sintetizador", reason=why)

    # 4) executor
    draft_exec = role_executor(draft_synth, formato=req.formato)
    MEM.push_short(f"[executor]\n{draft_exec}")
    ok, why = guardian_check(draft_exec)
    if not ok:
        return RunResponse(status="blocked", blocked_step="executor", reason=why)

    # 5) feedback humano (opcional)
    if req.apply_feedback and req.request_id:
        fb_text = HF.pop(req.request_id)
        if fb_text:
            regen_prompt = [
                {"role": "system", "content": SYSTEM_SAFETY},
                {"role": "user", "content": (
                    f"[REVISÃO COM FEEDBACK HUMANO]\n"
                    f"Feedback: {fb_text}\n\n"
                    f"Texto a revisar:\n{draft_exec}\n\n"
                    "Aplique o feedback preservando coerência e clareza."
                )}
            ]
            draft_exec = call_llm(regen_prompt, temperature=0.4)

    # 6) resumo e persistência leve
    resumo_prompt = [
        {"role": "system", "content": SYSTEM_SAFETY},
        {"role": "user", "content": (
            f"Resuma em 8-12 linhas (objetivo, decisões, pontos-chave):\n{draft_exec}"
        )}
    ]
    resumo = call_llm(resumo_prompt, temperature=0.2)
    if CHROMA_AVAILABLE:
        try:
            MEM.add_long(doc_id=f"log-{hash(draft_exec)}", text=resumo, meta={"kind": "resumo_exec"})
        except Exception:
            pass

    return RunResponse(
        status="ok",
        pesquisa=draft_pesq,
        esboco=draft_synth,
        resultado=draft_exec,
        resumo=resumo
    )

# ====== KB (RAG) endpoints ======
@app.post("/kb_upsert", response_model=KBUpsertResp)
def kb_upsert(req: KBUpsertReq):
    if not CHROMA_AVAILABLE:
        raise HTTPException(status_code=503, detail="ChromaDB indisponível no servidor.")
    # upsert simples
    MEM.update_long(doc_id=req.doc_id, text=req.text, meta=req.meta or {})
    return KBUpsertResp(ok=True, doc_id=req.doc_id, chroma_enabled=True)

@app.post("/kb_query", response_model=KBQueryResp)
def kb_query(req: KBQueryReq):
    docs = MEM.retrieve_long(req.query, k=req.k) if CHROMA_AVAILABLE else []
    return KBQueryResp(ok=True, docs=docs, chroma_enabled=CHROMA_AVAILABLE)

# ====== CRM tool (stub) ======
@app.post("/tool/crm_lookup", response_model=CRMLookupResp)
def crm_lookup(req: CRMLookupReq):
    if req.id and req.id in CRM_DB:
        return CRMLookupResp(ok=True, record=CRM_DB[req.id])
    if req.nome:
        # busca por nome simples
        for rec in CRM_DB.values():
            if rec.nome.lower() == req.nome.lower():
                return CRMLookupResp(ok=True, record=rec)
    return CRMLookupResp(ok=False, record=None)

@app.post("/tool/crm_upsert", response_model=CRMLookupResp)
def crm_upsert(rec: CRMRecord):
    CRM_DB[rec.id] = rec
    return CRMLookupResp(ok=True, record=rec)
    # ===== PDF helper =====
class _PDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, "Colaborativo IA — Resultado", new_x="LMARGIN", new_y="NEXT", align="C")

def make_pdf(title: str, body: str, resumo: str = "") -> bytes:
    pdf = _PDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 12)
    pdf.multi_cell(0, 8, title)
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6, body)
    if resumo:
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 12)
        pdf.multi_cell(0, 8, "Resumo")
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, resumo)
    return bytes(pdf.output(dest="S"))
    @app.post("/run_pdf")
def run_pdf(req: RunRequest):
    # Reutiliza a mesma lógica do /run
    resp = run(req)
    # Quando chamado internamente, resp já é um RunResponse (pydantic) ou dict compatível
    data = resp if isinstance(resp, dict) else resp.model_dump()

    if data.get("status") != "ok":
        raise HTTPException(status_code=400, detail=f"Fluxo bloqueado em {data.get('blocked_step')}: {data.get('reason')}")

    resultado = data.get("resultado") or ""
    resumo = data.get("resumo") or ""
    if not resultado.strip():
        raise HTTPException(status_code=422, detail="Nenhum conteúdo para gerar PDF.")

    pdf_bytes = make_pdf(title="Resultado do Orquestrador", body=resultado, resumo=resumo)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="colabIA_resultado.pdf"'}
    )