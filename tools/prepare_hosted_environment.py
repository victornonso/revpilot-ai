"""Prepare server-only hosting variables using standard dotenv parsing."""

import json
from pathlib import Path

from dotenv import dotenv_values


def runtime_environment(config, provider_file):
    runtime = {
        key: str(value)
        for key, value in config.items()
        if key != "APP_DATABASE_PASSWORD"
    }
    runtime.update(
        {
            key: value
            for key, value in dotenv_values(provider_file).items()
            if key.startswith("LLM_") and value is not None
        }
    )
    runtime["MIGRATION_DATABASE_URL"] = runtime["DATABASE_URL"]
    runtime["PYTHON_VERSION"] = "3.12.15"
    runtime.setdefault("LLM_TIER", "paid")
    return runtime


def main():
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / ".local/hosted-demo.json").read_text())
    runtime = runtime_environment(config, root / ".env.llm")
    (root / ".local/render.env").write_text(
        "\n".join(f"{key}={json.dumps(value)}" for key, value in runtime.items()),
        encoding="utf-8",
    )
    print(
        "Server environment prepared in ignored .local/render.env. Values are not logged."
    )


if __name__ == "__main__":
    main()
