"""
Testes do extrator.pipeline (orquestração).

Aqui não existe rede: passamos uma função de parse FALSA no parâmetro
`funcao_parse`. Isso testa a sequência completa
(API → filtro → gravação → resumo) em milissegundos.
"""

from pathlib import Path

import pytest

from extrator.config import Config
from extrator.pipeline import ResultadoPipeline, executar_pipeline


def parse_falso(_config: Config) -> list[dict]:
    """Função falsa: devolve o mesmo formato que a API real devolveria."""
    return [
        {
            "pages": [
                {"page": 9, "items": [{"type": "table", "csv": "a,b\n1,2"}]},
            ]
        }
    ]


def parse_falhando(_config: Config) -> list[dict]:
    """Função falsa que simula uma falha de rede/API."""
    raise ConnectionError("API indisponível (simulado)")


def test_pipeline_com_parse_falso(
    config_teste: Config, json_exemplo: list[dict]
) -> None:
    """Deve gravar 3 CSVs na pasta de saída e devolver o resultado."""

    def parse_que_usa_o_fixture(_config: Config) -> list[dict]:
        return json_exemplo

    resultado = executar_pipeline(config_teste, funcao_parse=parse_que_usa_o_fixture)

    assert isinstance(resultado, ResultadoPipeline)
    assert len(resultado.tabelas) == 3
    assert len(resultado.caminhos) == 3

    # Os arquivos existem mesmo no disco e com o nome esperado.
    arquivos = sorted(p.name for p in config_teste.pasta_saida.glob("*.csv"))
    assert arquivos == [
        "tabela_p001_01.csv",
        "tabela_p002_01.csv",
        "tabela_p002_02.csv",
    ]

    # O conteúdo bate com o CSV original da primeira tabela.
    primeiro = resultado.caminhos[0]
    assert "Indicador,Valor" in primeiro.read_text(encoding="utf-8")


def test_pipeline_sem_tabelas(config_teste: Config) -> None:
    """Se a API devolver nada, o pipeline conclui com listas vazias."""

    def parse_vazio(_config: Config) -> list[dict]:
        return [{"pages": [{"page": 1, "items": [{"type": "text", "value": "oi"}]}]}]

    resultado = executar_pipeline(config_teste, funcao_parse=parse_vazio)

    assert resultado.tabelas == []
    assert resultado.caminhos == []
    assert list(config_teste.pasta_saida.glob("*.csv")) == []


def test_erro_do_parse_sobe_para_quem_chamou(config_teste: Config) -> None:
    """Falha na API não é engolida: propaga para o main tratar (código 1)."""
    with pytest.raises(ConnectionError):
        executar_pipeline(config_teste, funcao_parse=parse_falhando)


def test_pipeline_usa_a_pasta_da_configuracao(config_teste: Config) -> None:
    """O pipeline grava exatamente na pasta indicada no Config."""
    executar_pipeline(config_teste, funcao_parse=parse_falso)
    assert config_teste.pasta_saida.is_dir()
    assert [p.name for p in config_teste.pasta_saida.glob("*.csv")] == [
        "tabela_p009_01.csv"
    ]
