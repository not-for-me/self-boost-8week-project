"""CLI entry point for fin-stat-table-detector.

Provides the main Click application and command group.
"""

import click

from fin_stat_table_detector.cli.commands.detect import detect


@click.group()
@click.version_option(version="0.1.0", prog_name="fin-stat-detect")
def main() -> None:
    """Financial statement table detector CLI.

    Detect financial statement tables in PDF reports and export
    results to Label Studio format for annotation review.
    """
    pass


main.add_command(detect)


if __name__ == "__main__":
    main()
