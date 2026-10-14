import os
import subprocess
from urllib.parse import urlparse

from apps.api.db import ROOT, settings

url = urlparse(settings.migration_database_url)
environment = {
    **os.environ,
    "DBT_HOST": url.hostname,
    "DBT_PORT": str(url.port or 5432),
    "DBT_USER": url.username,
    "DBT_PASSWORD": url.password,
}
raise SystemExit(
    subprocess.run(
        [
            str(ROOT / ".venv/Scripts/dbt.exe") if os.name == "nt" else "dbt",
            "build",
            "--project-dir",
            str(ROOT / "analytics/dbt"),
            "--profiles-dir",
            str(ROOT / "analytics/dbt"),
        ],
        env=environment,
        check=False,
    ).returncode
)
