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
)
PUBLIC_PROVIDER_NEUTRAL_SOURCES = (PACKAGE_ROOT / "chat" / "service.py",)
PROVIDER_NEUTRAL_IMPORTS = {
    "sejong_ai_api.llm.chat_contracts",
    "sejong_ai_api.llm.classifier_contracts",
    "sejong_ai_api.llm.facts",
}


def test_no_llm_http_router_exists() -> None:
    assert not (PACKAGE_ROOT / "api" / "llm.py").exists()
    assert all("llm" not in path.casefold() for path in create_app().openapi()["paths"])


def _top_level_imported_modules(source_path: Path) -> set[str]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    modules: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
        elif isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
    return modules


def test_public_app_sources_have_no_provider_import() -> None:
    for source_path in PUBLIC_PROVIDER_FREE_SOURCES:
        llm_imports = {
            module
            for module in _top_level_imported_modules(source_path)
            if module == "sejong_ai_api.llm" or module.startswith("sejong_ai_api.llm.")
        }
        assert llm_imports == set(), source_path


def test_chat_service_imports_only_provider_neutral_llm_modules() -> None:
    for source_path in PUBLIC_PROVIDER_NEUTRAL_SOURCES:
        llm_imports = {
            module
            for module in _top_level_imported_modules(source_path)
            if module == "sejong_ai_api.llm" or module.startswith("sejong_ai_api.llm.")
        }
        assert llm_imports == PROVIDER_NEUTRAL_IMPORTS, source_path


def test_llm_package_initializer_is_non_eager() -> None:
    initializer = PACKAGE_ROOT / "llm" / "__init__.py"
    assert _top_level_imported_modules(initializer) == set()
