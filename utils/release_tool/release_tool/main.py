# release_tool/main.py
import typer
from typing_extensions import Annotated

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
    changed_files_input: Annotated[str, typer.Option("--changed-files", help="Space-separated string of changed files.", RichHelpPanel="Inputs")] = "",
    assume_value_changes: Annotated[bool, typer.Option("--assume-values-changed", help="Assume potential value changes if no code changes.", RichHelpPanel="Inputs")] = False,
    services_dir: Annotated[str, typer.Option("--services-dir", help="Path to the services definition directory.", RichHelpPanel="Inputs")] = "./services",
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
    affected_services: Annotated[str, typer.Option("--affected-services", help="Space-separated string of affected service names.", RichHelpPanel="Inputs")] = "",
    services_dir: Annotated[str, typer.Option("--services-dir", help="Path to the services definition directory.", RichHelpPanel="Inputs")] = "./services",
    output_dir: Annotated[str, typer.Option("--output-dir", help="Path to output generated unit files.", RichHelpPanel="Inputs")] = "~/.config/containers/systemd",
    meta_target: Annotated[str, typer.Option("--meta-target", help="Optional systemd target name to make services PartOf (e.g., all-containers.target).", RichHelpPanel="Config")] = "",
    vars_json_str: Annotated[str, typer.Option("--vars-json", help="JSON string of global variables (from GitHub vars).", RichHelpPanel="Inputs")] = "{}"
):
    """
    Generates systemd unit files for affected services from compose definitions.
    """
    typer.echo(f"Placeholder: generate-units called.")
    typer.echo(f"Affected services: '{affected_services}'")
    typer.echo(f"Services directory: {services_dir}")
    typer.echo(f"Output directory: {output_dir}")
    # Actual logic will be implemented in step 5
    from release_tool import unit_generator # Import the new module
    from pathlib import Path

    typer.echo("Executing generate-units...", err=True)
    affected_services_list = [s for s in affected_services.split(' ') if s]

    if not affected_services_list:
        typer.echo("No affected services provided. Nothing to generate.", err=True)
        raise typer.Exit(code=0) # Not an error, just nothing to do

    services_dir_path = Path(services_dir)
    output_dir_path = Path(output_dir).expanduser() # Handles ~

    typer.echo(f"Affected services for generation: {affected_services_list}", err=True)
    typer.echo(f"Services definition directory: {services_dir_path}", err=True)
    typer.echo(f"Output directory for units: {output_dir_path}", err=True)

    success = unit_generator.generate_all_quadlet_files(
        affected_services=affected_services_list,
        services_dir_path=services_dir_path,
        output_dir_path=output_dir_path,
        meta_target_name=meta_target if meta_target else None # Pass None if empty string
    )

    if success:
        typer.echo("Unit file generation process completed successfully.", err=True)
    else:
        typer.echo("Unit file generation process encountered errors.", err=True)
        raise typer.Exit(code=1)


@app.command()
def pull_images(
    affected_services: Annotated[str, typer.Option(help="Space-separated string of affected service names.")] = "",
    units_dir: Annotated[str, typer.Option(help="Path to the generated unit files directory.")] = "~/.config/containers/systemd", # Needs expansion
):
    """
    Pulls container images for the affected services.
    """
    typer.echo(f"Placeholder: pull-images called.")
    typer.echo(f"Affected services: '{affected_services}'")
    typer.echo(f"Units directory: {units_dir}")
    # Actual logic will be implemented in step 6
    from release_tool import image_manager # Import the new module
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
    affected_services: Annotated[str, typer.Option(help="Space-separated string of affected service names.")] = "",
    units_dir: Annotated[str, typer.Option(help="Path to the generated unit files directory.")] = "~/.config/containers/systemd", # Needs expansion
):
    """
    Restarts affected services and their dependents.
    """
    # Actual logic will be implemented in step 7
    from release_tool import service_manager # Import the new module
    from pathlib import Path

    typer.echo("Executing manage-services restart...", err=True)
    affected_services_list = [s for s in affected_services.split(' ') if s]

    # The units_dir is not directly used by service_manager.manage_services_restart,
    # as systemctl operates on loaded units. It's kept as an option for consistency
    # or if future enhancements need it.
    # units_dir_path = Path(units_dir).expanduser()

    if not affected_services_list:
        typer.echo("No affected services provided for restart. Triggering daemon-reload only.", err=True)
        # Call daemon-reload directly, or have manage_services_restart handle empty list
        service_manager.manage_services_restart(affected_services_names=[])
        raise typer.Exit(code=0)

    typer.echo(f"Affected services for restart: {affected_services_list}", err=True)
    # typer.echo(f"Units directory (context): {units_dir_path}", err=True)

    success = service_manager.manage_services_restart(
        affected_services_names=affected_services_list
        # Potentially pass max_retries, check_interval from CLI options here
    )

    if success:
        typer.echo("Service restart process completed successfully.", err=True)
    else:
        typer.echo("Service restart process encountered errors.", err=True)
        raise typer.Exit(code=1)


@manage_app.command("status")
def services_status(
    services_to_check: Annotated[str, typer.Option(help="Space-separated string of service names to check.")] = "",
    units_dir: Annotated[str, typer.Option(help="Path to the generated unit files directory.")] = "~/.config/containers/systemd", # Needs expansion
):
    """
    Checks the status of specified services.
    """
    typer.echo(f"Placeholder: manage-services status called.")
    typer.echo(f"Services to check: '{services_to_check}'")
    typer.echo(f"Units directory: {units_dir}")
    # Actual logic will be implemented in step 7 (or as part of restart)

app.add_typer(manage_app)


# Remove the example_command if no longer needed, or keep for testing
@app.command()
def example_command(name: str):
    """
    An example command (can be removed later).
    """
    typer.echo(f"Hello {name}")


if __name__ == "__main__":
    app()
