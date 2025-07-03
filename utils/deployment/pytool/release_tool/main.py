# release_tool/main.py
import typer
from typing_extensions import Annotated
import os # Added for environment variable access for VARS_JSON default

from release_tool import __version__

app = typer.Typer(help="Release utility for managing selective service deployments.")

def version_callback(value: bool):
    if value:
        typer.echo(f"Release Tool Version: {__version__}")
        raise typer.Exit()

@app.callback()
def main(
    version: Annotated[bool, typer.Option("--version", "-v", callback=version_callback, is_eager=True, help="Show the application's version and exit.")] = False,
):
    """
    Main entry point for the release tool.
    """
    # This callback is good for global options like version, context settings, etc.
    # Specific command logic will go into the command functions themselves.
    pass

from release_tool import changed_services # Import the new module

@app.command()
def determine_changes(
    changed_files_input: Annotated[str, typer.Option("--changed-files", help="Space-separated string of changed files.")] = "",
    assume_value_changes: Annotated[bool, typer.Option("--assume-values-changed", help="Assume potential value changes if no code changes.")] = False,
    services_dir: Annotated[str, typer.Option("--services-dir", help="Path to the services definition directory.")] = "./services",
):
    """
    Determines which services are affected by changes.
    Outputs a space-separated list of affected service names to STDOUT.
    """
    typer.echo(f"Executing determine-changes...", err=True) # Log to stderr
    typer.echo(f"Input - Changed files string: '{changed_files_input}'", err=True)
    typer.echo(f"Input - Assume value changes: {assume_value_changes}", err=True)
    typer.echo(f"Input - Services directory: {services_dir}", err=True)

    affected_service_list = changed_services.determine_affected_services(
        changed_files_str=changed_files_input,
        assume_value_changes=assume_value_changes,
        services_dir=services_dir
    )

    output_string = " ".join(affected_service_list)
    typer.echo(f"Output - Affected services string: '{output_string}'", err=True)

    # Print the space-separated list to stdout, which can be captured by other processes
    print(output_string)

@app.command()
def generate_units(
    affected_services: Annotated[str, typer.Option("--affected-services", help="Space-separated string of affected service names.")] = "",
    services_dir: Annotated[str, typer.Option("--services-dir", help="Path to the services definition directory.")] = "./services",
    output_dir: Annotated[str, typer.Option("--output-dir", help="Path to output generated unit files.")] = "~/.config/containers/systemd",
    meta_target: Annotated[str, typer.Option("--meta-target", help="Optional systemd target name to make services PartOf (e.g., all-containers.target).")] = "",
    vars_json_str: Annotated[str, typer.Option("--vars-json", help="JSON string of global variables (from GitHub vars).")] = os.environ.get("VARS_JSON_STR", "{}") # Read from env if not passed as option
):
    """
    Generates systemd unit files for affected services from compose definitions.
    """
    from release_tool import unit_generator
    from pathlib import Path

    typer.echo("Executing generate-units...", err=True)
    # If vars_json_str was taken from env, it's already set. If passed as CLI, CLI takes precedence.
    # Typer handles this priority. If --vars-json is provided, it overrides the default (which reads from env).
    typer.echo(f"Input - Affected services: '{affected_services}'", err=True)
    typer.echo(f"Input - Services directory: {services_dir}", err=True)
    typer.echo(f"Input - Output directory: {output_dir}", err=True)
    typer.echo(f"Input - Meta target: '{meta_target}'", err=True)
    typer.echo(f"Input - Vars JSON string: '{vars_json_str[:100]}{'...' if len(vars_json_str) > 100 else ''}'", err=True)


    affected_services_list = [s for s in affected_services.split(' ') if s]

    if not affected_services_list:
        typer.echo("No affected services provided. Nothing to generate.", err=True)
        raise typer.Exit(code=0)

    services_dir_path = Path(services_dir)
    output_dir_path = Path(output_dir).expanduser()

    typer.echo(f"Resolved services definition directory: {services_dir_path}", err=True)
    typer.echo(f"Resolved output directory for units: {output_dir_path}", err=True)

    success = unit_generator.generate_all_quadlet_files(
        affected_services=affected_services_list,
        services_dir_path=services_dir_path,
        output_dir_path=output_dir_path,
        meta_target_name=meta_target if meta_target else None,
        vars_json_string=vars_json_str
    )

    if success:
        typer.echo("Unit file generation process completed successfully.", err=True)
    else:
        typer.echo("Unit file generation process encountered errors.", err=True)
        raise typer.Exit(code=1)


@app.command()
def pull_images(
    affected_services: Annotated[str, typer.Option("--affected-services", help="Space-separated string of affected service names.")] = "",
    units_dir: Annotated[str, typer.Option("--units-dir", help="Path to the generated unit files directory.")] = "~/.config/containers/systemd",
):
    """
    Pulls container images for the affected services.
    """
    from release_tool import image_manager
    from pathlib import Path

    typer.echo("Executing pull-images...", err=True)
    affected_services_list = [s for s in affected_services.split(' ') if s]

    if not affected_services_list:
        typer.echo("No affected services provided. Nothing to pull.", err=True)
        raise typer.Exit(code=0)

    units_dir_path = Path(units_dir).expanduser()

    typer.echo(f"Affected services for image pulling: {affected_services_list}", err=True)
    typer.echo(f"Units directory: {units_dir_path}", err=True)

    success = image_manager.pull_images_for_services(
        affected_services=affected_services_list,
        units_dir_path=units_dir_path
    )

    if success:
        typer.echo("Image pulling process completed.", err=True)
    else:
        typer.echo("Image pulling process encountered errors or failures.", err=True)
        raise typer.Exit(code=1)


# Create a Typer app for service management subcommands
manage_app = typer.Typer(name="manage-services", help="Manages services (restart, status, etc.).")

@manage_app.command("restart")
def services_restart(
    affected_services: Annotated[str, typer.Option("--affected-services", help="Space-separated string of affected service names.")] = "",
    units_dir: Annotated[str, typer.Option("--units-dir", help="Path to the generated unit files directory (contextual, not directly used by restart logic).")] = "~/.config/containers/systemd", # Kept for CLI consistency
):
    """
    Restarts affected services and their dependents.
    """
    from release_tool import service_manager
    # from pathlib import Path # Not needed for units_dir here

    typer.echo("Executing manage-services restart...", err=True)
    affected_services_list = [s for s in affected_services.split(' ') if s]

    if not affected_services_list:
        typer.echo("No affected services provided for restart. Triggering daemon-reload only.", err=True)
        service_manager.manage_services_restart(affected_services_names=[])
        raise typer.Exit(code=0)

    typer.echo(f"Affected services for restart: {affected_services_list}", err=True)

    success = service_manager.manage_services_restart(
        affected_services_names=affected_services_list
    )

    if success:
        typer.echo("Service restart process completed successfully.", err=True)
    else:
        typer.echo("Service restart process encountered errors.", err=True)
        raise typer.Exit(code=1)


@manage_app.command("status")
def services_status(
    services_to_check: Annotated[str, typer.Option("--services-to-check", help="Space-separated string of service names to check.")] = "",
    units_dir: Annotated[str, typer.Option("--units-dir", help="Path to the generated unit files directory (contextual).")] = "~/.config/containers/systemd", # Kept for CLI consistency
):
    """
    Checks the status of specified services.
    """
    typer.echo(f"Placeholder: manage-services status called.")
    typer.echo(f"Services to check: '{services_to_check}'")
    typer.echo(f"Units directory: {units_dir}")
    # Actual logic will be implemented later if needed, using service_manager.check_one_service_status

app.add_typer(manage_app)


# Remove the example_command if no longer needed, or keep for testing
@app.command()
def example_command(name: str):
    """
    An example command (can be removed later).
    """
    typer.echo(f"Hello {name}")


if __name__ == "__main__": # pragma: no cover
    app()
