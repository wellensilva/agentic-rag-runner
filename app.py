import os
import json
from typing import List, Dict, Any, Tuple, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL = os.getenv("LLM_MODEL", "gpt-4.1")
if not OPENAI_API_KEY:
    raise RuntimeError("Defina OPENAI_API_KEY no ambiente (.env)")

from openai import OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# ===== Memória =====
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
            return
        self.collection.add(
            documents=[text],
            metadatas=[meta or {}],
            ids=[doc_id],
        )

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

# ===== HF loop (versão API) =====
class FeedbackStore:
    """Armazena feedbacks simples por request_id para um fluxo manual opcional."""
    def __init__(self):
        self._store: Dict[str, str] = {}

    def set(self, request_id: str, feedback: str):
        self._store[request_id] = feedback

    def pop(self, request_id: str) -> str:
        return self._store.pop(request_id, "")

HF = FeedbackStore()

SYSTEM_SAFETY = (
    "Você é um assistente colaborativo. Explique em passos, "
    "verifique contradições e cite referências quando possível. "
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

def guardian_check(text: str) -> Tuple[bool, str]:
    banned = ["exploit", "malware", "doxxing", "private key", "senha="]
    for b in banned:
        if b.lower() in text.lower():
            return False, f"Conteúdo bloqueado por política ('{b}')."
    return True, "OK"

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

app = FastAPI(title="Colaborativo IA API", version="1.0.0")
MEM = Memory()

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
        MEM.add_long(doc_id=f"log-{hash(draft_exec)}", text=resumo, meta={"kind": "resumo_exec"})

    return RunResponse(
        status="ok",
        pesquisa=draft_pesq,
        esboco=draft_synth,
        resultado=draft_exec,
        resumo=resumo
    )
