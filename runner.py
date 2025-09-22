import os
import json
from typing import List, Dict, Any, Tuple

# =============== CONFIG ===============
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL = os.getenv("LLM_MODEL", "gpt-4.1")
assert OPENAI_API_KEY, "Defina OPENAI_API_KEY no ambiente."

# ---- Cliente OpenAI (SDK >=1.x) ----
from openai import OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# =============== CARTÃO 1: MEMÓRIA CURTA + LONGA ===============
# Memória curta = janela de contexto (histórico resumido)
# Memória longa = armazenamento persistente (ex.: ChromaDB)

try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMA_AVAILABLE = True
except Exception:
    CHROMA_AVAILABLE = False

class Memory:
    def __init__(self, collection_name: str = "colabIA"):
        self.short_context: List[str] = []
        self.max_short = 10  # guarda últimos N trechos (memória curta)
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

# =============== CARTÃO 2: APRENDIZAGEM ADAPTATIVA (HF LOOP) ===============
def human_feedback_loop(draft: str) -> Tuple[str, Dict[str, Any]]:
    """
    Interface simples para incorporar feedback humano.
    - Aqui você pode substituir por UI/flags/criticas automáticas.
    """
    print("\n--- RASCUNHO DO MODELO ---\n")
    print(draft[:2000] + ("\n...[cortado]" if len(draft) > 2000 else ""))
    print("\nDigite um feedback curto (ou ENTER p/ aceitar): ")
    try:
        fb = input().strip()
    except EOFError:
        fb = ""
    accepted = (fb == "")
    return ("", {"accepted": accepted, "feedback": fb})

# =============== CARTÃO 3: COLABORAÇÃO HUMANO-MÁQUINA (PASSO A PASSO) ===============
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

# =============== CARTÃO 4: ORQUESTRAÇÃO MULTI-AGENTE ===============
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

# =============== CARTÃO 5: ALINHAMENTO ÉTICO (GUARDIÃO) ===============
def guardian_check(text: str) -> Tuple[bool, str]:
    """
    Filtro simples de segurança/escopo.
    Retorna (ok, motivo). Expanda com regras específicas do seu projeto.
    """
    banned = ["exploit", "malware", "doxxing", "private key", "senha="]
    for b in banned:
        if b.lower() in text.lower():
            return False, f"Conteúdo bloqueado por política ('{b}')."
    return True, "OK"

# =============== ORQUESTRADOR ===============
class Orquestrador:
    def __init__(self):
        self.mem = Memory()

    def run(self, query: str, formato: str = "texto") -> Dict[str, Any]:
        # 1) contexto (memória curta + longa)
        ctx = self.mem.context_block(query)

        # 2) pesquisador
        draft_pesq = role_pesquisador(query, ctx)
        self.mem.push_short(f"[pesquisador]\n{draft_pesq}")

        # 3) guardião antes de seguir
        ok, why = guardian_check(draft_pesq)
        if not ok:
            return {"status": "blocked", "step": "pesquisador", "reason": why}

        # 4) sintetizador
        draft_synth = role_sintetizador(draft_pesq)
        self.mem.push_short(f"[sintetizador]\n{draft_synth}")

        ok, why = guardian_check(draft_synth)
        if not ok:
            return {"status": "blocked", "step": "sintetizador", "reason": why}

        # 5) executor
        draft_exec = role_executor(draft_synth, formato=formato)
        self.mem.push_short(f"[executor]\n{draft_exec}")

        ok, why = guardian_check(draft_exec)
        if not ok:
            return {"status": "blocked", "step": "executor", "reason": why}

        # 6) loop de feedback humano (opcional)
        _, fb = human_feedback_loop(draft_exec)
        if not fb["accepted"] and fb["feedback"]:
            hint = fb["feedback"]
            # Regerar com pista/hint
            regen_prompt = [
                {"role": "system", "content": SYSTEM_SAFETY},
                {"role": "user", "content": (
                    f"[REVISÃO COM FEEDBACK HUMANO]\n"
                    f"Feedback: {hint}\n\n"
                    f"Texto a revisar:\n{draft_exec}\n\n"
                    "Aplique o feedback preservando coerência e clareza."
                )}
            ]
            draft_exec = call_llm(regen_prompt, temperature=0.4)

        # 7) persistir um resumo na memória longa (se disponível)
        resumo_prompt = [
            {"role": "system", "content": SYSTEM_SAFETY},
            {"role": "user", "content": (
                f"Resuma em 8-12 linhas (objetivo, decisões, pontos-chave):\n{draft_exec}"
            )}
        ]
        resumo = call_llm(resumo_prompt, temperature=0.2)
        if CHROMA_AVAILABLE:
            self.mem.add_long(doc_id=f"log-{hash(draft_exec)}", text=resumo, meta={"kind": "resumo_exec"})

        return {
            "status": "ok",
            "pesquisa": draft_pesq,
            "esboco": draft_synth,
            "resultado": draft_exec,
            "resumo": resumo
        }

# =============== CLI ===============
def main():
    print("== Colaborativo IA Runner ==")
    print("Digite sua tarefa (ENTER para exemplo):")
    try:
        query = input().strip()
    except EOFError:
        query = ""
    if not query:
        query = "Gere um plano de 1 página para lançar um MVP do meu projeto com tarefas semanais."

    orch = Orquestrador()
    out = orch.run(query=query, formato="texto")
    print("\n--- SAÍDA ---")
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()