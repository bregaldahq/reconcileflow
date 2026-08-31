from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github" / "workflows" / "ci-cd.yml"
PRODUCTION_COMPOSE = ROOT / "compose.production.yaml"
SMOKE_SCRIPT = ROOT / "scripts" / "smoke_test.sh"
DEPLOY_SCRIPT = ROOT / "scripts" / "deploy_remote.sh"
GITIGNORE = ROOT / ".gitignore"
BASH = shutil.which("bash")


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _delivery_environment(tmp_path: Path, *, fail_first_up: bool = False) -> dict[str, str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker_log = tmp_path / "docker.log"
    marker = tmp_path / "failed-once"

    _write_executable(
        bin_dir / "curl",
        """#!/usr/bin/env bash
url="${@: -1}"
case "$url" in
  */health/ready) printf '%s' '{"status":"ready"}' ;;
  */api/v1/profiles) printf '%s' '{"items":[{"label":"Conciliação padrão"}]}' ;;
  *) printf '%s' '<title>ReconcileFlow</title>' ;;
esac
""",
    )
    _write_executable(
        bin_dir / "docker",
        """#!/usr/bin/env bash
printf '%s\n' "$*" >> "$DOCKER_LOG"
if [[ "${DOCKER_FAIL_FIRST_UP:-false}" == true \
  && "$*" == *" up "* \
  && ! -f "$DOCKER_FAILURE_MARKER" ]]; then
  touch "$DOCKER_FAILURE_MARKER"
  exit 19
fi
""",
    )

    environment = os.environ.copy()
    environment.update(
        {
            "PATH": f"{bin_dir}{os.pathsep}{environment['PATH']}",
            "DOCKER_LOG": str(docker_log),
            "DOCKER_FAILURE_MARKER": str(marker),
            "DOCKER_FAIL_FIRST_UP": "true" if fail_first_up else "false",
            "SMOKE_MAX_ATTEMPTS": "1",
            "SMOKE_RETRY_SECONDS": "0",
        }
    )
    return environment


def _prepare_deploy_directory(tmp_path: Path) -> Path:
    deploy_dir = tmp_path / "deploy"
    scripts_dir = deploy_dir / "scripts"
    scripts_dir.mkdir(parents=True)
    shutil.copy(PRODUCTION_COMPOSE, deploy_dir / PRODUCTION_COMPOSE.name)
    shutil.copy(SMOKE_SCRIPT, scripts_dir / SMOKE_SCRIPT.name)
    (deploy_dir / ".env.production").write_text(
        "POSTGRES_PASSWORD=unit-test\nPUBLIC_ORIGIN=https://example.test\n",
        encoding="utf-8",
    )
    return deploy_dir


def _immutable_image(name: str, character: str) -> str:
    return f"ghcr.io/example/reconcileflow/{name}@sha256:{character * 64}"


def test_all_third_party_actions_are_pinned_to_full_commit() -> None:
    action_lines = [
        line.strip()
        for line in WORKFLOW.read_text(encoding="utf-8").splitlines()
        if "uses:" in line
    ]

    assert len(action_lines) >= 10
    for line in action_lines:
        assert re.search(r"@[0-9a-f]{40}(?:\s+#\s+v\d+)?$", line), line


def test_pipeline_requires_quality_and_runtime_before_publish_and_deploy() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "needs: [quality, runtime-smoke]" in workflow
    assert "needs: publish" in workflow
    assert "vars.DEPLOY_ENABLED == 'true'" in workflow
    assert "make verify" in workflow
    assert "docker compose up --build --detach --wait" in workflow
    assert "koalaman/shellcheck:v0.11.0@sha256:" in workflow
    assert "subject-digest:" in workflow
    assert "@${{ steps.backend-build.outputs.digest }}" in workflow
    assert "@${{ steps.frontend-build.outputs.digest }}" in workflow


def test_production_compose_uses_prebuilt_images_and_private_binding() -> None:
    compose = PRODUCTION_COMPOSE.read_text(encoding="utf-8")

    assert "build:" not in compose
    assert "${BACKEND_IMAGE:?" in compose
    assert "${FRONTEND_IMAGE:?" in compose
    assert '"${BIND_ADDRESS:-127.0.0.1}:${WEB_PORT:-8080}:80"' in compose
    assert "8000:8000" not in compose
    assert "no-new-privileges:true" in compose


def test_production_environment_and_release_files_are_ignored() -> None:
    patterns = GITIGNORE.read_text(encoding="utf-8").splitlines()

    assert ".env.*" in patterns
    assert "!.env.production.example" in patterns


@pytest.mark.skipif(BASH is None, reason="bash não está disponível")
@pytest.mark.parametrize("script", [SMOKE_SCRIPT, DEPLOY_SCRIPT])
def test_delivery_scripts_have_valid_bash_syntax(script: Path) -> None:
    assert BASH is not None
    subprocess.run([BASH, "-n", str(script)], check=True)  # noqa: S603


@pytest.mark.skipif(BASH is None, reason="bash não está disponível")
def test_smoke_test_checks_web_health_and_profile_catalog(tmp_path: Path) -> None:
    environment = _delivery_environment(tmp_path)
    assert BASH is not None

    result = subprocess.run(  # noqa: S603
        [BASH, str(SMOKE_SCRIPT), "https://example.test"],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert "interface web" in result.stdout
    assert "saúde da API" in result.stdout
    assert "catálogo de perfis" in result.stdout


@pytest.mark.skipif(BASH is None, reason="bash não está disponível")
def test_remote_deploy_records_immutable_release_and_runs_compose(tmp_path: Path) -> None:
    environment = _delivery_environment(tmp_path)
    deploy_dir = _prepare_deploy_directory(tmp_path)
    backend_image = _immutable_image("backend", "a")
    frontend_image = _immutable_image("web", "b")
    assert BASH is not None

    subprocess.run(  # noqa: S603
        [BASH, str(DEPLOY_SCRIPT), str(deploy_dir), backend_image, frontend_image],
        check=True,
        env=environment,
    )

    release = (deploy_dir / ".env.release").read_text(encoding="utf-8")
    docker_log = (tmp_path / "docker.log").read_text(encoding="utf-8")
    assert f"BACKEND_IMAGE={backend_image}" in release
    assert f"FRONTEND_IMAGE={frontend_image}" in release
    assert "config --quiet" in docker_log
    assert "pull" in docker_log
    assert "up --detach --remove-orphans --wait --wait-timeout 180" in docker_log


@pytest.mark.skipif(BASH is None, reason="bash não está disponível")
def test_remote_deploy_restores_previous_release_after_failure(tmp_path: Path) -> None:
    environment = _delivery_environment(tmp_path, fail_first_up=True)
    deploy_dir = _prepare_deploy_directory(tmp_path)
    old_backend = _immutable_image("backend", "c")
    old_frontend = _immutable_image("web", "d")
    previous_release = f"BACKEND_IMAGE={old_backend}\nFRONTEND_IMAGE={old_frontend}\n"
    (deploy_dir / ".env.release").write_text(previous_release, encoding="utf-8")
    assert BASH is not None

    result = subprocess.run(  # noqa: S603
        [
            BASH,
            str(DEPLOY_SCRIPT),
            str(deploy_dir),
            _immutable_image("backend", "e"),
            _immutable_image("web", "f"),
        ],
        check=False,
        env=environment,
    )

    docker_log = (tmp_path / "docker.log").read_text(encoding="utf-8")
    assert result.returncode == 19
    assert (deploy_dir / ".env.release").read_text(encoding="utf-8") == previous_release
    assert docker_log.count("up --detach --remove-orphans --wait --wait-timeout 180") == 2
