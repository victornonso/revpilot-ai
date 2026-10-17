from dotenv import dotenv_values

from tools.prepare_hosted_environment import runtime_environment


def test_quoted_provider_credentials_preserve_dotenv_semantics(tmp_path):
    source = tmp_path / "provider.env"
    source.write_text(
        'LLM_API_KEY= "fixture-quoted-value"\nLLM_MODEL = "fixture-model"\n'
    )
    result = runtime_environment(
        {
            "DATABASE_URL": "postgresql+psycopg://application/db",
            "MIGRATION_DATABASE_URL": "postgresql+psycopg://administrator/db",
            "APP_DATABASE_PASSWORD": "fixture-password",
        },
        source,
    )
    assert result["LLM_API_KEY"] == "fixture-quoted-value"
    assert result["LLM_MODEL"] == "fixture-model"
    assert result["MIGRATION_DATABASE_URL"] == result["DATABASE_URL"]
    assert "APP_DATABASE_PASSWORD" not in result
    target = tmp_path / "render.env"
    import json

    target.write_text("\n".join(f"{k}={json.dumps(v)}" for k, v in result.items()))
    assert dict(dotenv_values(target)) == result


def test_paid_deepseek_tier_survives_hosted_preparation(tmp_path):
    source = tmp_path / "provider.env"
    source.write_text(
        "LLM_PROVIDER=deepseek\nLLM_TIER=paid\n"
        "LLM_MODEL=deepseek-flash\nLLM_BASE_URL=https://api.deepseek.com\n"
    )
    result = runtime_environment({"DATABASE_URL": "fixture-url"}, source)
    assert result["LLM_TIER"] == "paid"
    assert result["LLM_PROVIDER"] == "deepseek"
