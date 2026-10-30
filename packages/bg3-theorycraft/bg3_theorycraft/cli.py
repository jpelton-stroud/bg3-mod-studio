"""bg3-theorycraft CLI entrypoint."""

import sys

from bg3_theorycraft import simulate_build_synergy


def main() -> None:
    sys.exit(simulate_build_synergy.main())


if __name__ == "__main__":
    main()
