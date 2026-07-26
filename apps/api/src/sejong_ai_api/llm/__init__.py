"""Non-eager package boundary for local LLM modules.

Callers import provider-neutral contracts or explicitly local provider modules by
their full module path. Importing this package never constructs or imports a
provider transport.
"""

__all__: list[str] = []
