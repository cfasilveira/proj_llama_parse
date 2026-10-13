"""
Testes do extrator.tabelas (funções puras: filtragem, nomes e gravação).

São os testes mais importantes do projeto: cobrem a regra de negócio
sem rede e sem API.
"""

from pathlib import Path

from extrator.tabelas import (
    Tabela,
    extrair_tabelas,
    montar_resumo,
    nome_arquivo_tabela,
    salvar_tabela,
)


def test_extrai_apenas_tabelas_com_conteudo(json_exemplo: list[dict]) -> None:
    """Do JSON de exemplo, só as 3 tabelas com csv devem ser mantidas."""
    tabelas = extrair_tabelas(json_exemplo)

    assert len(tabelas) == 3
    # Textos foram descartados e a tabela sem csv também.
    assert all(t.csv for t in tabelas)


def test_preserva_pagina_e_ordem(json_exemplo: list[dict]) -> None:
    """A tabela 1 é da página 1; as outras duas são da página 2."""
    tabelas = extrair_tabelas(json_exemplo)

    assert [t.pagina for t in tabelas] == [1, 2, 2]
    assert [t.indice_na_pagina for t in tabelas] == [1, 1, 2]
    # Conteúdo íntegro: a primeira tabela tem os cabeçalhos esperados.
    assert "Indicador,Valor" in tabelas[0].csv


def test_entradas_vazias_ou_estranhas() -> None:
    """Não deve explodir com JSON vazio, None ou estrutura incompleta."""
    assert extrair_tabelas([]) == []
    assert extrair_tabelas(None) == []
    assert extrair_tabelas([{}]) == []
    assert extrair_tabelas([{"pages": None}]) == []
    assert extrair_tabelas([{"pages": [{"page": 1}]}]) == []  # sem items
    assert extrair_tabelas([{"pages": [{"items": ["nao sou dict"]}]}]) == []


def test_aceita_resultado_unico_em_vez_de_lista() -> None:
    """Um dicionário único (em vez de lista) também é aceito."""
    resultado_unico = {
        "pages": [{"page": 3, "items": [{"type": "table", "csv": "a\n1"}]}]
    }
    tabelas = extrair_tabelas(resultado_unico)

    assert len(tabelas) == 1
    assert tabelas[0].pagina == 3


def test_nome_do_arquivo_da_tabela() -> None:
    """O nome precisa carregar a página e o índice, com zeros à esquerda."""
    tabela = Tabela(pagina=7, indice_na_pagina=1, csv="a,b\n1,2")
    assert nome_arquivo_tabela(tabela) == "tabela_p007_01.csv"

    outra = Tabela(pagina=120, indice_na_pagina=10, csv="a\n1")
    assert nome_arquivo_tabela(outra) == "tabela_p120_10.csv"


def test_conta_linhas_e_colunas() -> None:
    """linhas inclui o cabeçalho; colunas é o máximo entre as linhas."""
    tabela = Tabela(pagina=1, indice_na_pagina=1, csv="a,b,c\n1,2,3\n4,5,6")
    assert tabela.linhas == 3
    assert tabela.colunas == 3

    vazia = Tabela(pagina=1, indice_na_pagina=1, csv="")
    assert vazia.linhas == 0
    assert vazia.colunas == 0


def test_salvar_tabela_cria_o_arquivo(json_exemplo: list[dict], tmp_path: Path) -> None:
    """Deve criar a pasta e gravar o CSV com o conteúdo exato (mais '\\n')."""
    tabela = extrair_tabelas(json_exemplo)[0]
    destino = salvar_tabela(tabela, tmp_path / "saida")

    assert destino.is_file()
    assert destino.name == "tabela_p001_01.csv"
    assert destino.read_text(encoding="utf-8") == tabela.csv + "\n"


def test_salvar_tabela_repetida_nao_duplica_arquivos(
    json_exemplo: list[dict], tmp_path: Path
) -> None:
    """Mesmo nome gravado duas vezes = um arquivo só (sobrescrito)."""
    tabela = extrair_tabelas(json_exemplo)[0]

    salvar_tabela(tabela, tmp_path)
    salvar_tabela(tabela, tmp_path)

    assert len(list(tmp_path.glob("*.csv"))) == 1


def test_montar_resumo_com_e_sem_tabelas(json_exemplo: list[dict]) -> None:
    """O resumo deve mencionar a contagem e o intervalo de páginas."""
    assert "Nenhuma tabela" in montar_resumo([])

    resumo = montar_resumo(extrair_tabelas(json_exemplo))
    assert "3 tabela(s)" in resumo
    assert "páginas 1..2" in resumo
