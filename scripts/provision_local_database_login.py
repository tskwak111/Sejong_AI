from __future__ import annotations

import os
import secrets
import stat
import tempfile
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import quote

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict

ROLE_NAME = "sejong_local_login"
TARGET_ENV_KEY = "DATABASE_URL"
CAPABILITY_ROLE_NAME = "sejong_backend"
EXPECTED_ADMIN_IDENTITY = ("postgres", "127.0.0.1", 54322, "postgres")
EXPECTED_EXISTING_ROLE_STATE = (
    True,
    True,
    False,
    False,
    False,
    False,
    False,
    -1,
    True,
    True,
)
EXPECTED_MEMBERSHIP_STATE = (True, True, False, True, True)
EXPECTED_LOGIN_ADMIN_STATE = (True, True, True, False, False)
EXPECTED_CAPABILITY_ROLE_STATE = (
    False,
    True,
    False,
    False,
    False,
    False,
    False,
    -1,
    True,
    True,
    True,
)
EXPECTED_CAPABILITY_MEMBER_STATE = (True, True, True)
ALLOWED_ADMIN_CONNINFO_KEYS = frozenset({"user", "password", "host", "port", "dbname"})
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_PATH = REPOSITORY_ROOT / "apps" / "api" / ".env"


def _assert_no_ambient_libpq_environment(environment: Mapping[str, str]) -> None:
    if any(
        name.upper().startswith("PG") and value != ""
        for name, value in environment.items()
    ):
        raise ValueError("AMBIENT_LIBPQ_ENVIRONMENT_INVALID")


def _validate_admin_dsn(value: str) -> None:
    if (
        not value
        or value != value.strip()
        or any(character in value for character in "\x00\r\n")
    ):
        raise ValueError("ADMIN_DSN_IDENTITY_INVALID")
    try:
        values = conninfo_to_dict(value)
        password = values.get("password")
        port_text = values.get("port")
        if (
            set(values) != ALLOWED_ADMIN_CONNINFO_KEYS
            or not isinstance(password, str)
            or not password
            or any(character in password for character in "\x00\r\n")
            or not isinstance(port_text, str)
            or not port_text.isascii()
            or not port_text.isdecimal()
        ):
            raise ValueError
        identity = (
            values.get("user", ""),
            values.get("host", ""),
            int(port_text),
            values.get("dbname", ""),
        )
    except (TypeError, UnicodeError, ValueError, psycopg.Error):
        raise ValueError("ADMIN_DSN_IDENTITY_INVALID") from None
    if identity != EXPECTED_ADMIN_IDENTITY:
        raise ValueError("ADMIN_DSN_IDENTITY_INVALID")


def _build_backend_database_url(password: str) -> str:
    if not password or any(character in password for character in "\x00\r\n"):
        raise ValueError("BACKEND_PASSWORD_INVALID")
    try:
        encoded_user = quote(ROLE_NAME, safe="")
        encoded_password = quote(password, safe="")
        encoded_database = quote(EXPECTED_ADMIN_IDENTITY[3], safe="")
    except UnicodeError:
        raise ValueError("BACKEND_PASSWORD_INVALID") from None
    return (
        f"postgresql://{encoded_user}:{encoded_password}"
        f"@{EXPECTED_ADMIN_IDENTITY[1]}:{EXPECTED_ADMIN_IDENTITY[2]}/{encoded_database}"
    )


def update_env_assignment(path: Path, key: str, value: str) -> None:
    if not key or any(character in key for character in "=\r\n"):
        raise ValueError("INVALID_ENV_KEY")
    if any(character in value for character in "\r\n"):
        raise ValueError("INVALID_ENV_VALUE")

    original = path.read_bytes() if path.exists() else b""
    key_prefix = key.encode("utf-8") + b"="
    replacement = key_prefix + value.encode("utf-8")
    updated_lines: list[bytes] = []
    found = False

    for line in original.splitlines(keepends=True):
        content = line.rstrip(b"\r\n")
        line_ending = line[len(content) :]
        if content.startswith(key_prefix):
            updated_lines.append(replacement + line_ending)
            found = True
        else:
            updated_lines.append(line)

    updated = b"".join(updated_lines)
    if not found:
        line_ending = b"\r\n" if b"\r\n" in original else b"\n"
        if updated and not updated.endswith((b"\r", b"\n")):
            updated += line_ending
        updated += replacement + line_ending

    path.parent.mkdir(parents=True, exist_ok=True)
    existing_mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else None
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f"{path.name}.",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(updated)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        if existing_mode is not None:
            os.chmod(temporary_path, existing_mode)
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def provision(admin_dsn: str, env_path: Path) -> None:
    _assert_no_ambient_libpq_environment(os.environ)
    _validate_admin_dsn(admin_dsn)

    password = secrets.token_urlsafe(32)
    with psycopg.connect(
        admin_dsn,
        hostaddr=EXPECTED_ADMIN_IDENTITY[1],
        autocommit=False,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
SELECT
  rolcanlogin, rolinherit, rolsuper, rolcreatedb, rolcreaterole,
  rolreplication, rolbypassrls, rolconnlimit, rolvaliduntil IS NULL,
  NOT EXISTS (
    SELECT 1
    FROM pg_catalog.pg_db_role_setting AS settings
    WHERE settings.setrole = roles.oid
  )
FROM pg_catalog.pg_roles AS roles
WHERE roles.rolname = %s
""".strip(),
                (ROLE_NAME,),
            )
            role_state = cursor.fetchone()
            if role_state is not None:
                if role_state != EXPECTED_EXISTING_ROLE_STATE:
                    raise ValueError("BACKEND_ROLE_STATE_INVALID")
                # PostgreSQL 17 rejects even a no-op NOSUPERUSER assignment from the
                # intentionally non-superuser local admin. The same boundary applies to
                # NOREPLICATION and NOBYPASSRLS. The existing state was checked above,
                # so rotate only options that role-admin may set.
                role_options = sql.SQL(
                    " LOGIN INHERIT NOCREATEDB NOCREATEROLE PASSWORD {}"
                ).format(sql.Literal(password))
                cursor.execute(
                    sql.SQL("ALTER ROLE {} WITH").format(sql.Identifier(ROLE_NAME))
                    + role_options
                )
            else:
                role_options = sql.SQL(
                    " LOGIN INHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE "
                    "NOREPLICATION NOBYPASSRLS PASSWORD {}"
                ).format(sql.Literal(password))
                cursor.execute(
                    sql.SQL("CREATE ROLE {} WITH").format(sql.Identifier(ROLE_NAME))
                    + role_options
                )
            cursor.execute(
                """
SELECT
  rolcanlogin, rolinherit, rolsuper, rolcreatedb, rolcreaterole,
  rolreplication, rolbypassrls, rolconnlimit, rolvaliduntil IS NULL,
  NOT EXISTS (
    SELECT 1
    FROM pg_catalog.pg_db_role_setting AS settings
    WHERE settings.setrole = roles.oid
  )
FROM pg_catalog.pg_roles AS roles
WHERE roles.rolname = %s
""".strip(),
                (ROLE_NAME,),
            )
            if cursor.fetchone() != EXPECTED_EXISTING_ROLE_STATE:
                raise ValueError("BACKEND_ROLE_STATE_INVALID")
            cursor.execute(
                sql.SQL("GRANT {} TO {}").format(
                    sql.Identifier(CAPABILITY_ROLE_NAME),
                    sql.Identifier(ROLE_NAME),
                )
            )
            cursor.execute(
                """
SELECT
  pg_catalog.count(*) = 1,
  COALESCE(pg_catalog.bool_and(granted_role.rolname = %s), false),
  COALESCE(pg_catalog.bool_or(memberships.admin_option), false),
  COALESCE(pg_catalog.bool_or(memberships.inherit_option), false),
  COALESCE(pg_catalog.bool_or(memberships.set_option), false)
FROM pg_catalog.pg_auth_members AS memberships
JOIN pg_catalog.pg_roles AS granted_role
  ON granted_role.oid = memberships.roleid
JOIN pg_catalog.pg_roles AS member_role
  ON member_role.oid = memberships.member
WHERE member_role.rolname = %s
""".strip(),
                (CAPABILITY_ROLE_NAME, ROLE_NAME),
            )
            if cursor.fetchone() != EXPECTED_MEMBERSHIP_STATE:
                raise ValueError("BACKEND_MEMBERSHIP_STATE_INVALID")
            cursor.execute(
                """
SELECT
  pg_catalog.count(*) = 1,
  COALESCE(pg_catalog.bool_and(member_role.rolname = %s), false),
  COALESCE(pg_catalog.bool_or(memberships.admin_option), false),
  COALESCE(pg_catalog.bool_or(memberships.inherit_option), false),
  COALESCE(pg_catalog.bool_or(memberships.set_option), false)
FROM pg_catalog.pg_auth_members AS memberships
JOIN pg_catalog.pg_roles AS granted_role
  ON granted_role.oid = memberships.roleid
JOIN pg_catalog.pg_roles AS member_role
  ON member_role.oid = memberships.member
WHERE granted_role.rolname = %s
""".strip(),
                (EXPECTED_ADMIN_IDENTITY[0], ROLE_NAME),
            )
            if cursor.fetchone() != EXPECTED_LOGIN_ADMIN_STATE:
                raise ValueError("BACKEND_LOGIN_ADMIN_STATE_INVALID")
            cursor.execute(
                """
SELECT
  rolcanlogin, rolinherit, rolsuper, rolcreatedb, rolcreaterole,
  rolreplication, rolbypassrls, rolconnlimit, rolvaliduntil IS NULL,
  NOT EXISTS (
    SELECT 1
    FROM pg_catalog.pg_db_role_setting AS settings
    WHERE settings.setrole = roles.oid
  ),
  NOT EXISTS (
    SELECT 1
    FROM pg_catalog.pg_auth_members AS memberships
    WHERE memberships.member = roles.oid
  )
FROM pg_catalog.pg_roles AS roles
WHERE roles.rolname = %s
""".strip(),
                (CAPABILITY_ROLE_NAME,),
            )
            if cursor.fetchone() != EXPECTED_CAPABILITY_ROLE_STATE:
                raise ValueError("BACKEND_CAPABILITY_STATE_INVALID")
            cursor.execute(
                """
SELECT
  pg_catalog.count(*) = 2,
  pg_catalog.count(*) FILTER (
    WHERE member_role.rolname = %s
      AND NOT memberships.admin_option
      AND memberships.inherit_option
      AND memberships.set_option
  ) = 1,
  pg_catalog.count(*) FILTER (
    WHERE member_role.rolname = %s
      AND memberships.admin_option
      AND NOT memberships.inherit_option
      AND NOT memberships.set_option
  ) = 1
FROM pg_catalog.pg_auth_members AS memberships
JOIN pg_catalog.pg_roles AS granted_role
  ON granted_role.oid = memberships.roleid
JOIN pg_catalog.pg_roles AS member_role
  ON member_role.oid = memberships.member
WHERE granted_role.rolname = %s
""".strip(),
                (ROLE_NAME, EXPECTED_ADMIN_IDENTITY[0], CAPABILITY_ROLE_NAME),
            )
            if cursor.fetchone() != EXPECTED_CAPABILITY_MEMBER_STATE:
                raise ValueError("BACKEND_CAPABILITY_MEMBER_STATE_INVALID")
        connection.commit()

    backend_dsn = _build_backend_database_url(password)
    # PostgreSQL and filesystem replacement cannot share a transaction. A file failure keeps the
    # previous env bytes intact; rerunning provisioning safely rotates the database password again.
    update_env_assignment(env_path, TARGET_ENV_KEY, backend_dsn)


def main() -> int:
    admin_dsn = os.environ.get("SEJONG_ADMIN_DATABASE_URL", "")
    if not admin_dsn.strip():
        print("[FAIL] step=PROVISION-LOCAL-DB-LOGIN reason=missing-admin-dsn code=2")
        return 2

    try:
        provision(admin_dsn, DEFAULT_ENV_PATH)
    except psycopg.Error:
        print("[FAIL] step=PROVISION-LOCAL-DB-LOGIN reason=database code=1")
        return 1
    except (OSError, UnicodeError, ValueError):
        print("[FAIL] step=PROVISION-LOCAL-DB-LOGIN reason=operational code=1")
        return 1

    print("[PASS] step=PROVISION-LOCAL-DB-LOGIN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
