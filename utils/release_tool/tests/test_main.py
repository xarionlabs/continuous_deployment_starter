# tests/test_main.py
from typer.testing import CliRunner
from release_tool.main import app

runner = CliRunner()

def test_app_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "Release Tool Version: 0.1.0" in result.stdout

def test_example_command():
    result = runner.invoke(app, ["example-command", "Jules"])
    assert result.exit_code == 0
    assert "Hello Jules" in result.stdout

def test_app_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage: main [OPTIONS] COMMAND [ARGS]..." in result.stdout
    assert "Release utility for managing selective service deployments." in result.stdout
    assert "example-command" in result.stdout
