import ast
from pathlib import Path

from sejong_ai_api.main import create_app

API_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = API_ROOT / "src" / "sejong_ai_api"
PUBLIC_PROVIDER_FREE_SOURCES = (
    PACKAGE_ROOT / "main.py",
    PACKAGE_ROOT / "local.py",
    PACKAGE_ROOT / "api" / "chat.py",
    PACKAGE_ROOT / "api" / "health.py",
    PACKAGE_ROOT / "chat" / "service.py",
)


def test_no_llm_http_router_exists() -> None:
    assert not (PACKAGE_ROOT / "api" / "llm.py").exists()
    assert all("llm" not in path.casefold() for path in create_app().openapi()["paths"])


def test_public_app_and_chat_sources_have_no_llm_import() -> None:
    for source_path in PUBLIC_PROVIDER_FREE_SOURCES:
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        imported_modules = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }
        imported_modules.update(
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
        assert not any(
            module == "sejong_ai_api.llm" or module.startswith("sejong_ai_api.llm.")
            for module in imported_modules
        ), source_path
