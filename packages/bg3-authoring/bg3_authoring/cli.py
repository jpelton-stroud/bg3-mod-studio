"""bg3-authoring CLI entrypoint."""

import sys

from bg3_core.cli import build_parser, dispatch_command
from bg3_core.cli_common import ConsoleColor, ExitCode, OutputEmitter


def main() -> None:
    parser = build_parser()
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(ExitCode.USAGE)

    args = parser.parse_args()
    color = ConsoleColor(stream=sys.stderr, force_color=False)
    emitter = OutputEmitter(json_mode=args.json, color=color)

    try:
        ret = dispatch_command(args, emitter)
        sys.exit(ret)
    except KeyboardInterrupt:
        emitter.error(
            message="Operation aborted by user.",
            code="SIGINT",
            exit_code=130,
            exit_process=True,
        )


if __name__ == "__main__":
    main()
