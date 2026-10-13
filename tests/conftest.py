"""
Fixtures do pytest (dados compartilhados entre os testes).

Aqui criamos um JSON FAKE com a mesma forma que o LlamaParse devolve em
produção. Assim os testes rodam offline: sem rede, sem chave e sem gastar
créditos na API.
"""

from pathlib import Path

import pytest

from extrator.config import Config

# JSON de exemplo no formato real da API:
#   - página 1: 1 texto + 1 tabela válida  → 1 tabela
#   - página 2: 2 tabelas válidas + 1 tabela SEM csv (quebrada) + 1 texto
# Resultado esperado: 3 tabelas extraídas.
JSON_EXEMPLO = {
    "pages": [
        {
            "page": 1,
            "items": [
                {"type": "text", "value": "Relatório da Administração 2024"},
                {"type": "table", "csv": "Indicador,Valor\nReceita,100\nLucro,25"},
            ],
        },
        {
            "page": 2,
            "items": [
                {"type": "table", "csv": "Ano,Produção\n2023,10\n2024,12"},
                {"type": "table", "csv": "Produto,Preço\nA,9.9\nB,19.9"},
                # Tabela "quebrada": a API às vezes devolve sem csv. Devemos ignorar.
                {"type": "table", "csv": ""},
                {"type": "text", "value": "Nota de rodapé qualquer."},
            ],
        },
    ]
}


@pytest.fixture
def json_exemplo() -> list[dict]:
    """Cópia independente do JSON de exemplo (evita que um teste afete outro).

    Devolvemos uma LISTA com um resultado, como o `get_json_result()` real
    do LlamaParse faz (uma entrada por arquivo enviado).
    """
    import json

    return [json.loads(json.dumps(JSON_EXEMPLO))]


@pytest.fixture
def config_teste(tmp_path: Path) -> Config:
    """Configuração válida apontando para uma pasta temporária do pytest.

    `tmp_path` é criado pelo pytest para cada teste e apagado depois —
    assim nunca sujamos a pasta real do projeto com resíduo de teste.
    """
    pdf = tmp_path / "resultado.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake para o teste")  # PDF mínimo de mentira

    return Config(
        arquivo_pdf=pdf,
        pasta_saida=tmp_path / "tabelas",
        api_key="llx-chave-de-teste",
    )
