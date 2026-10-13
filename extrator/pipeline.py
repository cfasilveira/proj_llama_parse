"""
Pipeline: a orquestração do projeto.

Liga todas as peças na ordem certa:

    config válida ──▶ parse na API ──▶ filtro das tabelas ──▶ grava CSVs ──▶ resumo

O truque importante (que deixa o projeto testável sem rede): a função de parse
entra como PARÂMETRO (`funcao_parse`). Em produção usamos a real
(`extrair_tabelas_via_api`); nos testes passamos uma função falsa que devolve
JSON de mentira. Nada de framework de mock — Python puro.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from extrator.config import Config
from extrator.parser_llama import extrair_tabelas_via_api
from extrator.tabelas import (
    Tabela,
    extrair_tabelas,
    montar_resumo,
    salvar_tabela,
)

logger = logging.getLogger("extrator.pipeline")

# Assinatura esperada da função de parse: recebe Config, devolve o JSON bruto.
TipoFuncaoParse = Callable[[Config], list[dict]]


@dataclass(frozen=True)
class ResultadoPipeline:
    """O que o pipeline entrega no final."""

    tabelas: list[Tabela]  # tabelas em memória (com página, linhas, colunas)
    caminhos: list[Path]  # caminhos dos CSVs gravados no disco


def executar_pipeline(
    config: Config,
    funcao_parse: TipoFuncaoParse = extrair_tabelas_via_api,
) -> ResultadoPipeline:
    """Roda a extração de ponta a ponta e devolve o resultado."""

    logger.info("Início do pipeline.")
    # Nunca logamos a chave de API — só os caminhos e o modo de operação.
    logger.info("PDF: %s | Saída: %s", config.arquivo_pdf, config.pasta_saida)

    # 1) Falar com a API (ou com a função falsa, nos testes).
    json_resultados = funcao_parse(config)

    # 2) Filtrar: do JSON completo, só as tabelas com csv.
    tabelas = extrair_tabelas(json_resultados)
    logger.info("%d tabela(s) identificada(s) no JSON.", len(tabelas))

    # 3) Gravar cada tabela como um CSV na pasta de saída.
    caminhos: list[Path] = []
    for tabela in tabelas:
        caminho = salvar_tabela(tabela, config.pasta_saida)
        logger.info(
            "Salvo: %s (%d linhas x %d colunas)",
            caminho,
            tabela.linhas,
            tabela.colunas,
        )
        caminhos.append(caminho)

    # 4) Resumo final para o usuário.
    logger.info(montar_resumo(tabelas))
    logger.info("Fim do pipeline.")

    return ResultadoPipeline(tabelas=tabelas, caminhos=caminhos)
