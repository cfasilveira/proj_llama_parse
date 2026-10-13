"""
Único módulo que conversa com a API do LlamaParse v2 (o "IO" do projeto).

Ele recebe um `Config` e devolve o JSON bruto da API. NÃO filtra nada —
a filtragem das tabelas fica em `tabelas.py`. Essa separação permite:
- trocar a forma de extração sem tocar nas regras de negócio;
- testar o pipeline offline injetando uma função de parse falsa.

Sobre a API v2 (SDK oficial `llama-cloud`):
- O parse acontece em 3 passos feitos pelo SDK: enviar o arquivo, rodar o
  job e esperar terminar. O `parse()` já faz os três e devolve o resultado.
- expand=["items"]: pedimos a visão "items" — a árvore de elementos da página
  (textos, tabelas, imagens). É a única visão onde dá para separar tabela de
  texto corrido, porque cada item tem um `type`.
- tier="agentic": usa os modelos de IA para um bom resultado em tabelas.
  O cost_optimizer manda as páginas simples para um nível mais barato e só
  gasta o tier completo nas páginas complexas (equivalente ao antigo auto_mode).
"""

import logging

from extrator.config import Config

logger = logging.getLogger("extrator.parser")

# Versão da configuração de parse (a LlamaIndex publica versões datadas).
VERSAO_PARSE = "latest"


def extrair_tabelas_via_api(config: Config) -> list[dict]:
    """Envia o PDF ao LlamaParse v2 e devolve o JSON bruto do resultado.

    O import do SDK é FEITO DENTRO DA FUNÇÃO de propósito: assim os testes
    offline (que nunca chamam esta função) não precisam carregar a biblioteca.
    """

    # Import oficial v2 ("llama-cloud"). O antigo "llama-parse" usava a API v1,
    # que foi descontinuada pela LlamaIndex.
    from llama_cloud import LlamaCloud

    # O cliente lê a chave do ambiente; passamos a da configuração por segurança.
    cliente = LlamaCloud(api_key=config.api_key)

    logger.info(
        "Enviando '%s' ao LlamaParse (tier=%s)...",
        config.arquivo_pdf,
        config.tier,
    )

    # Opções de processamento: idioma do OCR + economia de créditos.
    opcoes_processamento: dict = {
        "ocr_parameters": {"languages": [config.language]},
    }
    # O cost_optimizer só existe nos tiers com IA (agentic/agentic_plus).
    if config.cost_optimizer and config.tier.startswith("agentic"):
        opcoes_processamento["cost_optimizer"] = {"enable": True}

    try:
        # O SDK faz upload + job + espera, tudo em uma chamada.
        resultado = cliente.parsing.parse(
            tier=config.tier,
            version=VERSAO_PARSE,
            upload_file=str(config.arquivo_pdf),
            processing_options=opcoes_processamento,
            expand=["items"],  # pedimos a árvore de itens (tabelas, textos...)
        )
    except Exception:
        # Logamos o erro COMO EXCEÇÃO (guarda o traceback no arquivo de log)
        # e deixamos o erro subir para o pipeline/main tratar.
        logger.exception("Falha ao chamar a API do LlamaParse.")
        raise

    paginas = _converter_paginas(resultado)
    logger.info("Parse concluído: %d página(s) recebida(s).", len(paginas))

    # Devolvemos o MESMO formato do JSON antigo ({"pages": [{"page": n,
    # "items": [...]}]}) para que `tabelas.py` continue funcionando igual —
    # a mudança de API fica isolada aqui dentro.
    return [{"pages": paginas}]


def _converter_paginas(resultado) -> list[dict]:
    """Converte o objeto de resultado do SDK v2 no formato simples que usamos.

    Atenção aos detalhes:
    - o número da página no v2 se chama `page_number` (não `page`);
    - páginas que falharam vêm com success=False e sem `items` — pulamos.
    """
    paginas_convertidas: list[dict] = []

    estrutura_itens = getattr(resultado, "items", None)
    for pagina in getattr(estrutura_itens, "pages", None) or []:
        if getattr(pagina, "success", True) is False:
            logger.warning(
                "Página %s falhou no parse e foi ignorada.",
                getattr(pagina, "page_number", "?"),
            )
            continue

        itens_convertidos = []
        for item in getattr(pagina, "items", None) or []:
            itens_convertidos.append(
                {
                    # Só mantemos o que `tabelas.py` precisa saber.
                    "type": getattr(item, "type", None),
                    "csv": getattr(item, "csv", None),
                    "md": getattr(item, "md", None),
                    "rows": getattr(item, "rows", None),
                }
            )

        paginas_convertidas.append(
            {
                "page": getattr(pagina, "page_number", 0),
                "items": itens_convertidos,
            }
        )

    return paginas_convertidas
