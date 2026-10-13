#!/usr/bin/env python3
"""
Ponto de entrada do projeto.

Este arquivo é propositalmente pequeno: ele só liga as peças e devolve um
código de saída para o sistema operacional.

    uv run main.py     →  extrai as tabelas de resultado.pdf para ./tabelas/

Códigos de saída (úteis para scripts/CI):
    0 = sucesso
    1 = erro (configuração inválida ou falha na extração)
"""

import sys

from extrator.config import carregar_config
from extrator.logging_config import configurar_logging
from extrator.pipeline import executar_pipeline


def main() -> int:
    """Roda a extração e devolve 0 (ok) ou 1 (erro)."""

    # 1) Logging primeiro: assim qualquer problema seguinte fica registrado
    #    na tela (INFO) e no arquivo extrator.log (DEBUG).
    logger = configurar_logging()

    # 2) Carrega e VALIDA a configuração (.env, chave, PDF, pasta de saída).
    #    Erros de digitação/ambiente aparecem aqui, cedo e com mensagem clara.
    try:
        config = carregar_config()
    except ValueError as erro:
        logger.error("Configuração inválida: %s", erro)
        return 1

    # 3) Executa o pipeline: API → filtro de tabelas → gravação dos CSVs.
    try:
        resultado = executar_pipeline(config)
    except Exception:
        # .exception grava o traceback completo no extrator.log.
        logger.exception("A extração falhou.")
        return 1

    # 4) Mensagem final curta (o detalhe já foi logado pelo pipeline).
    print(f"\nConcluído: {len(resultado.caminhos)} arquivo(s) em '{config.pasta_saida}'.")
    return 0


# O bloco abaixo só roda quando o arquivo é executado diretamente
# (não quando é importado pelo pytest). Por isso os testes não disparam o main.
if __name__ == "__main__":
    sys.exit(main())
