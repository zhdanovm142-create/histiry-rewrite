"""Frontend bootstrap entrypoint."""

from frontend.dashboard import __name__ as dashboard_module


def main() -> None:
    """Run minimal frontend bootstrap."""
    print(f"Frontend bootstrap ready ({dashboard_module})")


if __name__ == "__main__":
    main()
