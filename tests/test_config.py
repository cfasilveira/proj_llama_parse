"""
Testes do extrator.config (carregamento e validação da configuração).

Cada teste isola o ambiente com monkeypatch, garantindo que:
- o .env real do projeto NÃO interfira no resultado;
- variáveis de um teste não vazem para outro.
"""

from pathlib import Path

import pytest

from extrator import config as modulo_config
from extrator.config import Config, carregar_config

# Caminho inexistente de propósito: carregar_config não deve achar o .env real.
ENV_INEXISTENTE = "nao_existe.env"


def _pdf_fake(tmp_path: Path) -> Path:
    pdf = tmp_path / "resultado.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    return pdf


def test_falta_a_chave(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Sem a variável de ambiente, deve falhar com mensagem clara."""
    monkeypatch.delenv(modulo_config.CHAVE_AMBIENTE, raising=False)

    with pytest.raises(ValueError, match=modulo_config.CHAVE_AMBIENTE):
        carregar_config(
            arquivo_pdf=str(_pdf_fake(tmp_path)),
            pasta_saida=str(tmp_path / "tabelas"),
            caminho_env=ENV_INEXISTENTE,
        )


def test_chave_com_formato_errado(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Chave que não começa com 'llx-' é rejeitada."""
    monkeypatch.setenv(modulo_config.CHAVE_AMBIENTE, "chave-copiada-errada")

    with pytest.raises(ValueError, match="llx-"):
        carregar_config(
            arquivo_pdf=str(_pdf_fake(tmp_path)),
            pasta_saida=str(tmp_path / "tabelas"),
            caminho_env=ENV_INEXISTENTE,
        )


def test_pdf_inexistente(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Chave ok, mas o PDF não está no disco → erro antes de qualquer chamada."""
    monkeypatch.setenv(modulo_config.CHAVE_AMBIENTE, "llx-valida")

    with pytest.raises(ValueError, match="PDF"):
        carregar_config(
            arquivo_pdf=str(tmp_path / "nao_existe.pdf"),
            pasta_saida=str(tmp_path / "tabelas"),
            caminho_env=ENV_INEXISTENTE,
        )


def test_config_valida(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Caminho feliz: devolve um Config pronto e cria a pasta de saída."""
    monkeypatch.setenv(modulo_config.CHAVE_AMBIENTE, "llx-valida")
    pasta_saida = tmp_path / "tabelas"

    config = carregar_config(
        arquivo_pdf=str(_pdf_fake(tmp_path)),
        pasta_saida=str(pasta_saida),
        caminho_env=ENV_INEXISTENTE,
    )

    assert isinstance(config, Config)
    assert config.api_key == "llx-valida"
    assert config.arquivo_pdf.name == "resultado.pdf"
    assert pasta_saida.is_dir()  # a pasta de saída foi criada


def test_ler_chave_do_arquivo_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Se a variável não estiver no ambiente, deve vir do arquivo .env."""
    monkeypatch.delenv(modulo_config.CHAVE_AMBIENTE, raising=False)

    env = tmp_path / ".env"
    env.write_text("LLAMA_CLOUD_API_KEY=llx-vinda_do_env\n", encoding="utf-8")

    config = carregar_config(
        arquivo_pdf=str(_pdf_fake(tmp_path)),
        pasta_saida=str(tmp_path / "tabelas"),
        caminho_env=str(env),
    )

    assert config.api_key == "llx-vinda_do_env"


def test_padroes_do_config() -> None:
    """Os padrões estão nos lugares certos (pt, tier agentic com economia)."""
    config = Config(
        arquivo_pdf=Path("resultado.pdf"),
        pasta_saida=Path("tabelas"),
        api_key="llx-x",
    )
    assert config.language == "pt"
    assert config.tier == "agentic"
    assert config.cost_optimizer is True


def test_tier_invalido(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Tier fora da lista aceita pela API v2 → erro claro."""
    monkeypatch.setenv(modulo_config.CHAVE_AMBIENTE, "llx-valida")

    with pytest.raises(ValueError, match="Tier"):
        carregar_config(
            arquivo_pdf=str(_pdf_fake(tmp_path)),
            pasta_saida=str(tmp_path / "tabelas"),
            caminho_env=ENV_INEXISTENTE,
            tier="turbo",
        )
