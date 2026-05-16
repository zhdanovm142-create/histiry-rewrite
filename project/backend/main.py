"""Backend bootstrap entrypoint."""

from backend.api import __name__ as api_module


def main() -> None:
    """Run minimal backend bootstrap."""
    print(f"Backend bootstrap ready ({api_module})")


if __name__ == "__main__":
    main()
