import ast
import subprocess
import sys
import textwrap
import tomllib
import unittest
from pathlib import Path

from sejong_ai_api import __version__

API_ROOT = Path(__file__).resolve().parents[1]
PRIVACY_SOURCE = API_ROOT / "src" / "sejong_ai_api" / "privacy" / "redaction.py"
SOURCE_FILES = (
    API_ROOT / "src" / "sejong_ai_api" / "main.py",
    API_ROOT / "src" / "sejong_ai_api" / "api" / "health.py",
    API_ROOT / "src" / "sejong_ai_api" / "contracts" / "chat.py",
    API_ROOT / "src" / "sejong_ai_api" / "core" / "logging.py",
    PRIVACY_SOURCE,
)
RETRIEVAL_METADATA_PATH = API_ROOT.parents[1] / "data" / "retrieval" / "topic-coverage.v1.json"

PRIVACY_ALLOWED_IMPORT_ROOTS = {
    "__future__",
    "collections",
    "dataclasses",
    "enum",
    "re",
    "typing",
    "unicodedata",
}

APPROVED_RUNTIME_DEPENDENCIES = {
    "fastapi==0.139.0",
    "httpx==0.28.1",
    "psycopg[binary,pool]==3.3.4",
    "pydantic==2.13.4",
    "uvicorn==0.51.0",
}
APPROVED_DEVELOPMENT_DEPENDENCIES = {
    "mypy==2.3.0",
    "pytest==9.1.1",
    "pytest-asyncio==1.4.0",
    "ruff==0.15.21",
}
BANNED_IMPORT_ROOTS = {
    "anthropic",
    "deepseek",
    "httpx",
    "openai",
    "psycopg",
    "requests",
    "sqlalchemy",
}
BANNED_CONSTRUCTION_CALLS = {
    "AsyncClient",
    "AsyncConnection",
    "AsyncConnectionPool",
    "Client",
    "Connection",
    "ConnectionPool",
    "connect",
    "create_engine",
    "create_pool",
    "getenv",
    "open",
    "urlopen",
}


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def test_privacy_module_is_stdlib_only_and_import_safe() -> None:
    tree = ast.parse(PRIVACY_SOURCE.read_text(encoding="utf-8"), filename=str(PRIVACY_SOURCE))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    assert roots <= PRIVACY_ALLOWED_IMPORT_ROOTS
    source = PRIVACY_SOURCE.read_text(encoding="utf-8")
    for forbidden in ("getenv", "environ", "logging", "open(", "httpx", "psycopg", "requests"):
        assert forbidden not in source


class ApiArchitectureTest(unittest.TestCase):
    def test_retrieval_metadata_is_outside_the_official_release_tree(self) -> None:
        self.assertEqual(RETRIEVAL_METADATA_PATH.parent.name, "retrieval")
        self.assertNotIn("official", RETRIEVAL_METADATA_PATH.parts)
        self.assertTrue(RETRIEVAL_METADATA_PATH.is_file())

    def test_exact_approved_dependencies_and_tool_configuration(self) -> None:
        pyproject_path = API_ROOT / "pyproject.toml"
        self.assertTrue(pyproject_path.is_file(), "apps/api/pyproject.toml must exist")

        pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        self.assertEqual(pyproject["project"]["version"], "0.4.0")
        self.assertEqual(__version__, "0.4.0")
        self.assertEqual(set(pyproject["project"]["dependencies"]), APPROVED_RUNTIME_DEPENDENCIES)
        self.assertEqual(
            set(pyproject["dependency-groups"]["dev"]), APPROVED_DEVELOPMENT_DEPENDENCIES
        )
        self.assertEqual(pyproject["project"]["requires-python"], ">=3.12.13,<3.13")
        self.assertIs(pyproject["tool"]["uv"]["package"], False)
        self.assertEqual(pyproject["tool"]["pytest"]["ini_options"]["pythonpath"], ["src"])
        self.assertEqual(pyproject["tool"]["mypy"]["mypy_path"], "src")

    def test_api_boundary_modules_exist_without_concrete_io_imports_or_construction(self) -> None:
        for source_path in SOURCE_FILES:
            with self.subTest(source_path=source_path.relative_to(API_ROOT)):
                self.assertTrue(source_path.is_file(), f"missing API source: {source_path}")
                tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))

                imported_roots: set[str] = set()
                call_names: set[str] = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        imported_roots.update(
                            alias.name.split(".", maxsplit=1)[0] for alias in node.names
                        )
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        imported_roots.add(node.module.split(".", maxsplit=1)[0])
                    elif isinstance(node, ast.Call):
                        call_name = _call_name(node)
                        if call_name is not None:
                            call_names.add(call_name)

                self.assertEqual(imported_roots & BANNED_IMPORT_ROOTS, set())
                self.assertEqual(call_names & BANNED_CONSTRUCTION_CALLS, set())

    def test_main_import_isolated_from_database_modules_pool_and_environment(self) -> None:
        source_root = API_ROOT / "src"
        probe = textwrap.dedent(
            f"""
            import builtins
            import inspect
            import os
            import sys

            sys.path.insert(0, {str(source_root)!r})

            import fastapi
            import starlette

            original_import = builtins.__import__
            original_environ = os.environ
            original_getenv = os.getenv
            application_source = os.path.normcase(os.path.abspath({str(source_root)!r}))

            def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
                if name.split('.', 1)[0] in {{'psycopg', 'psycopg_pool'}}:
                    raise AssertionError('database driver imported')
                return original_import(name, globals, locals, fromlist, level)

            def ensure_non_application_caller():
                caller = inspect.currentframe().f_back.f_back
                filename = os.path.normcase(os.path.abspath(caller.f_code.co_filename))
                if filename.startswith(application_source):
                    raise AssertionError('application environment read')

            def guarded_getenv(key, default=None):
                ensure_non_application_caller()
                return original_getenv(key, default)

            class GuardedEnvironment:
                def __getitem__(self, key):
                    ensure_non_application_caller()
                    return original_environ[key]

                def get(self, key, default=None):
                    ensure_non_application_caller()
                    return original_environ.get(key, default)

                def __iter__(self):
                    ensure_non_application_caller()
                    return iter(original_environ)

                def __len__(self):
                    ensure_non_application_caller()
                    return len(original_environ)

                def __contains__(self, key):
                    ensure_non_application_caller()
                    return key in original_environ

            builtins.__import__ = guarded_import
            os.getenv = guarded_getenv
            os.environ = GuardedEnvironment()

            import sejong_ai_api.main

            assert 'psycopg' not in sys.modules
            assert 'psycopg_pool' not in sys.modules
            assert 'sejong_ai_api.db.pool' not in sys.modules
            assert 'sejong_ai_api.db.repository' not in sys.modules
            print('isolated-import-safe')
            """
        )

        completed = subprocess.run(
            [sys.executable, "-I", "-c", probe],
            cwd=API_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "isolated-import-safe")
        self.assertEqual(completed.stderr, "")

    def test_public_app_import_loads_only_provider_neutral_llm_modules(self) -> None:
        source_root = API_ROOT / "src"
        probe = textwrap.dedent(
            f"""
            import sys
            from pathlib import Path

            sys.path.insert(0, {str(source_root)!r})

            import sejong_ai_api.main
            import sejong_ai_api.local

            missing_env = Path({str(API_ROOT)!r}) / "tests" / ".missing-task6-env"
            sejong_ai_api.main.create_app()
            sejong_ai_api.local.create_local_app(environ={{}}, env_path=missing_env)

            loaded = {{
                name
                for name in sys.modules
                if name == "sejong_ai_api.llm" or name.startswith("sejong_ai_api.llm.")
            }}
            assert {{
                "sejong_ai_api.llm",
                "sejong_ai_api.llm.chat_contracts",
                "sejong_ai_api.llm.facts",
            }} <= loaded, loaded
            forbidden = {{
                "sejong_ai_api.llm.chat_prompt",
                "sejong_ai_api.llm.limits",
                "sejong_ai_api.llm.settings",
                "sejong_ai_api.llm.upstage_chat",
            }}
            assert not (forbidden & loaded), loaded
            assert "httpx" not in sys.modules
            print("public-import-provider-isolated")
            """
        )

        completed = subprocess.run(
            [sys.executable, "-I", "-c", probe],
            cwd=API_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "public-import-provider-isolated")
        self.assertEqual(completed.stderr, "")


if __name__ == "__main__":
    unittest.main()
