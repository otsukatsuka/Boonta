"""Boonta v2 CLI entry point."""
import click


@click.group()
def cli():
    """Boonta - JRDB horse racing prediction system."""
    pass


if __name__ == "__main__":
    cli()
