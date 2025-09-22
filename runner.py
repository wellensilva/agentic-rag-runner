import os
import openai

# Configure sua chave de API
openai.api_key = os.getenv("OPENAI_API_KEY")

def run_agentic(prompt: str, model: str = "gpt-4.1") -> str:
    """
    Executa uma chamada ao modelo com foco agentic (memória + raciocínio em etapas).
    :param prompt: Texto de entrada.
    :param model: Modelo a ser usado (padrão: gpt-4.1).
    :return: Resposta do modelo.
    """
    try:
        response = openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Você é um assistente colaborativo com foco em pesquisa e memória."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Erro: {e}"

if __name__ == "__main__":
    # Exemplo de execução
    entrada = input("Digite seu prompt: ")
    saida = run_agentic(entrada)
    print("Resposta:\n", saida)