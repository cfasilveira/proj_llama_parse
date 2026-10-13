"""
Regras de negócio para as tabelas: filtrar, nomear e salvar.

Este é o módulo "puro" do projeto: NENHUMA função aqui faz chamada de rede.
Isso é de propósito — permite testar tudo com pytest offline, rápido e grátis.

Formato de entrada (JSON devolvido pelo LlamaParse):
    {
      "pages": [
        {
          "page": 7,
          "items": [
            {"type": "text",  "value": "..."},                  # texto comum → descartamos
            {"type": "table", "csv": "a,b\\n1,2", ...}          # tabela → queremos isto
          ]
        }
      ]
    }

Formato de saída: um arquivo .csv por tabela, nomeado com a página de origem
(ex.: tabela_p007_01.csv) para você conseguir rastrear qual tabela veio de
qual página do PDF.
"""

import csv
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Tabela:
    """Uma tabela extraída do PDF.

    Imutável (frozen=True) e com as propriedades linhas/colunas calculadas
    a partir do próprio CSV — assim não corremos o risco de o número ficar
    desatualizado em relação ao conteúdo.
    """

    pagina: int  # número da página no PDF (começa em 1 na resposta da API)
    indice_na_pagina: int  # 1ª, 2ª... tabela daquela página
    csv: str  # conteúdo CSV gerado pelo LlamaParse

    @property
    def linhas(self) -> int:
        """Quantidade de linhas do CSV (inclui o cabeçalho)."""
        return len(self._linhas_csv())

    @property
    def colunas(self) -> int:
        """Quantidade de colunas (a maior linha encontrada)."""
        return max((len(linha) for linha in self._linhas_csv()), default=0)

    def _linhas_csv(self) -> list[list[str]]:
        """Divide o texto CSV em linhas de campos, ignorando linhas vazias."""
        leitor = csv.reader(StringIO(self.csv))
        return [linha for linha in leitor if any(campo.strip() for campo in linha)]


def _resultado_em_lista(json_resultados: Any) -> list[dict]:
    """Aceita tanto uma lista de resultados quanto um único resultado.

    O `get_json_result()` do LlamaParse devolve uma lista, mas por segurança
    tratamos também o caso de vir um dicionário único.
    """
    if json_resultados is None:
        return []
    if isinstance(json_resultados, dict):
        return [json_resultados]
    return list(json_resultados)


def extrair_tabelas(json_resultados: Any) -> list[Tabela]:
    """Percorre o JSON do LlamaParse e devolve apenas as tabelas com conteúdo.

    Este é o coração do projeto: é aqui que o "texto corrido" do relatório é
    descartado e só a estrutura das tabelas é mantida.
    """

    tabelas: list[Tabela] = []

    for resultado in _resultado_em_lista(json_resultados):
        if not isinstance(resultado, dict):
            continue

        # .get() com valor padrão: se a API mudar o formato, não quebramos.
        for pagina in resultado.get("pages", []) or []:
            if not isinstance(pagina, dict):
                continue

            numero_pagina = pagina.get("page", 0)
            contador_da_pagina = 0  # usado para numerar as tabelas da página

            for item in pagina.get("items", []) or []:
                if not isinstance(item, dict):
                    continue

                # Só nos interessa o tipo "table"...
                if item.get("type") != "table":
                    continue

                # ...e precisa ter conteúdo CSV. Tabela sem csv é tabela quebrada.
                conteudo_csv = (item.get("csv") or "").strip()
                if not conteudo_csv:
                    continue

                contador_da_pagina += 1
                tabelas.append(
                    Tabela(
                        pagina=numero_pagina,
                        indice_na_pagina=contador_da_pagina,
                        csv=conteudo_csv,
                    )
                )

    return tabelas


def nome_arquivo_tabela(tabela: Tabela) -> str:
    """Gera o nome do arquivo CSV: tabela_p007_01.csv (página 7, 1ª tabela).

    Nome determinístico (sempre igual para a mesma tabela) em vez do nome com
    timestamp que a lib usa internamente — assim reruns sobrescrevem em vez de
    acumular arquivos e dá para achar a tabela pela página.
    """
    return f"tabela_p{tabela.pagina:03d}_{tabela.indice_na_pagina:02d}.csv"


def salvar_tabela(tabela: Tabela, pasta: Path) -> Path:
    """Grava a tabela como arquivo CSV e devolve o caminho gravado.

    - mkdir(exist_ok=True): cria a pasta se não existir, não reclama se existir.
    - encoding="utf-8": necessário para acentos do português.
    - Garantimos uma quebra de linha final (bom costume para arquivos de texto).
    """
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)

    destino = pasta / nome_arquivo_tabela(tabela)

    conteudo = tabela.csv
    if not conteudo.endswith("\n"):
        conteudo += "\n"

    destino.write_text(conteudo, encoding="utf-8")
    return destino


def montar_resumo(tabelas: list[Tabela]) -> str:
    """Texto curto com o resultado da extração (usado no log e na tela)."""
    if not tabelas:
        return "Nenhuma tabela encontrada no documento."

    paginas = sorted({tabela.pagina for tabela in tabelas})
    return (
        f"{len(tabelas)} tabela(s) extraída(s) "
        f"das páginas {paginas[0]}..{paginas[-1]} "
        f"({len(paginas)} página(s) com tabela)."
    )
