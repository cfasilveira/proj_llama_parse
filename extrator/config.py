"""
Configuração central do projeto.

Responsabilidade deste módulo: ler as configurações do ambiente (.env) e do
sistema de arquivos, validar tudo ANTES de qualquer chamada de rede e devolver
um objeto `Config` pronto para o resto do programa usar.

Por que centralizar aqui?
- A chave da API deixa de ficar no código (antes estava hardcoded em main.py).
- Se algo faltar (chave, PDF), o programa falha cedo e com mensagem clara,
  em vez de quebrar no meio de um parse de 68 páginas.
"""

import os
from dataclasses import dataclass
from pathlib import Path

# O python-dotenv lê o arquivo .env e "despeja" as variáveis no ambiente.
from dotenv import load_dotenv

# Constantes padrão: se o usuário não informar nada, usamos estas.
# Estão em maiúsculas porque são valores fixos (convenção de Python).
ARQUIVO_PDF_PADRAO = "resultado.pdf"
PASTA_SAIDA_PADRAO = "tabelas"
CHAVE_AMBIENTE = "LLAMA_CLOUD_API_KEY"
PREFIXO_CHAVE_LLAMA = "llx-"  # toda chave válida da LlamaCloud começa assim


@dataclass(frozen=True)
class Config:
    """Configuração validada e pronta para uso.

    `frozen=True` significa que o objeto é imutável depois de criado — evita
    que qualquer parte do programa mude a configuração sem querer no meio da
    execução.
    """

    arquivo_pdf: Path  # PDF de entrada
    pasta_saida: Path  # pasta onde os CSVs serão gravados
    api_key: str  # chave da API (nunca é impressa nos logs)
    language: str = "pt"  # idioma do documento, ajuda o OCR do LlamaParse
    # "Nível" de IA do Parse v2 (quanto mais alto, mais preciso e mais caro):
    #   fast | cost_effective | agentic | agentic_plus
    tier: str = "agentic"
    # Economia de créditos: páginas simples vão para um nível mais barato e
    # só as complexas (com tabelas) usam o tier completo. Vale com agentic+.
    cost_optimizer: bool = True


# Níveis aceitos pela API v2 do Parse (usados na validação da configuração).
TIRES_VALIDOS = ("fast", "cost_effective", "agentic", "agentic_plus")


def carregar_config(
    arquivo_pdf: str = ARQUIVO_PDF_PADRAO,
    pasta_saida: str = PASTA_SAIDA_PADRAO,
    caminho_env: str = ".env",
    tier: str = Config.tier,
) -> Config:
    """Carrega e valida a configuração. Levanta ValueError se algo estiver errado.

    Ordem das verificações (da mais grave para a mais simples):
    1. chave da API presente e com formato válido;
    2. nível (tier) de parse válido;
    3. arquivo PDF existe no disco;
    4. pasta de saída criada (não é erro se já existir).
    """

    # Passo 1: carregar o .env. Se o arquivo não existir, load_dotenv apenas
    # retorna False (não é erro) — aí a validação abaixo acusa a chave faltando.
    load_dotenv(caminho_env)

    # Passo 2: ler a chave do ambiente.
    api_key = os.getenv(CHAVE_AMBIENTE, "").strip()
    if not api_key:
        raise ValueError(
            f"A variável {CHAVE_AMBIENTE} não foi encontrada. "
            f"Copy .env.example para .env e preencha com a sua chave "
            f"(https://cloud.llamaindex.ai/)."
        )
    if not api_key.startswith(PREFIXO_CHAVE_LLAMA):
        # Validação simples que pega o erro comum de colar a chave errada.
        raise ValueError(
            f"A {CHAVE_AMBIENTE} não parece válida: deve começar com '{PREFIXO_CHAVE_LLAMA}'."
        )

    # Passo 3: o nível (tier) precisa ser um dos aceitos pela API v2.
    if tier not in TIRES_VALIDOS:
        raise ValueError(
            f"Tier inválido: '{tier}'. Use um destes: {', '.join(TIRES_VALIDOS)}."
        )

    # Passo 4: o PDF de entrada precisa existir.
    caminho_pdf = Path(arquivo_pdf)
    if not caminho_pdf.is_file():
        raise ValueError(f"Arquivo PDF não encontrado: '{caminho_pdf.resolve()}'.")

    # Passo 5: pasta de saída. `exist_ok=True` não reclama se já existir.
    caminho_saida = Path(pasta_saida)
    caminho_saida.mkdir(parents=True, exist_ok=True)

    return Config(
        arquivo_pdf=caminho_pdf,
        pasta_saida=caminho_saida,
        api_key=api_key,
        tier=tier,
    )
