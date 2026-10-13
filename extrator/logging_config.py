"""
Configuração de logging (registro de eventos do programa).

Por que usar logging em vez de print()?
- `print` só joga texto na tela. `logging` registra COM HORA e NÍVEL,
  e pode gravar em arquivo — essencial para descobrir o que aconteceu
  quando o parse de 68 páginas falhar às 2 da manhã.

Níveis usados (do menos para o mais grave):
    DEBUG    → detalhes internos (vão só para o arquivo)
    INFO     → progresso normal ("enviando PDF...", "3 tabelas salvas")
    WARNING  → algo suspeito, mas o programa continua
    ERROR    → falhou uma operação
    CRITICAL → o programa não pode continuar

Este módulo é usado por TODOS os outros:
    logger = logging.getLogger("extrator")   # mesma "família" de logs
"""

import logging
from pathlib import Path

# Formato da mensagem: data + hora | nível | nome do módulo | texto
FORMATO = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

# Nome da "família" de logs do projeto. Todos os módulos usam este prefixo
# (ex.: "extrator.parser", "extrator.pipeline") para poder filtrar depois.
NOME_LOGGER = "extrator"


def configurar_logging(
    nivel_console: int = logging.INFO,
    arquivo: str = "extrator.log",
) -> logging.Logger:
    """Configura o logger do projeto e o devolve.

    - Console: mostra INFO ou mais grave (o usuário vê o progresso).
    - Arquivo: grava DEBUG ou mais grave (o detalhe fica guardado para análise).

    A checagem `if logger.handlers` evita configurar duas vezes — se chamarmos
    esta função de novo, o pytest ou um import duplicado não criaria handlers
    repetidos (logs apareceriam em dobro).
    """

    logger = logging.getLogger(NOME_LOGGER)
    logger.setLevel(logging.DEBUG)  # o logger aceita tudo; quem filtra são os handlers
    if logger.handlers:
        return logger  # já estava configurado

    # Handler de console (para o usuário ver na tela).
    console = logging.StreamHandler()
    console.setLevel(nivel_console)
    console.setFormatter(logging.Formatter(FORMATO))

    # Handler de arquivo (guarda o detalhe fino para depois).
    # encoding="utf-8" é obrigatório aqui: o relatório tem acentos em português.
    arquivo_handler = logging.FileHandler(Path(arquivo), encoding="utf-8")
    arquivo_handler.setLevel(logging.DEBUG)
    arquivo_handler.setFormatter(logging.Formatter(FORMATO))

    logger.addHandler(console)
    logger.addHandler(arquivo_handler)

    return logger


def obter_logger(nome_modulo: str) -> logging.Logger:
    """Cria (ou recupera) o logger de um módulo específico.

    Uso:  logger = obter_logger(__name__)
    Assim os logs ficam nomeados como "extrator.parser", "extrator.tabelas"...
    e dá para saber de onde veio cada mensagem.
    """

    return logging.getLogger(f"{NOME_LOGGER}.{nome_modulo}")
