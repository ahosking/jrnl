# Copyright (C) 2012-2021 jrnl contributors
# License: https://www.gnu.org/licenses/gpl-3.0.html

import os
import re
import shutil
import tempfile
from unittest.mock import patch

from pytest_bdd import given
from pytest_bdd import then
from pytest_bdd import when
from pytest_bdd.parsers import parse
from pytest import fixture
import toml

from jrnl import __version__
from jrnl.cli import cli
from jrnl.os_compat import split_args


# ----- FIXTURES ----- #
@fixture
def cli_run():
    return {"status": 0, "stdout": None, "stderr": None}


@fixture
def temp_dir():
    return tempfile.TemporaryDirectory()


@fixture
def working_dir(request):
    return os.path.join(request.config.rootpath, "tests")


@fixture
def toml_version(working_dir):
    pyproject = os.path.join(working_dir, "..", "pyproject.toml")
    pyproject_contents = toml.load(pyproject)
    return pyproject_contents["tool"]["poetry"]["version"]


# ----- STEPS ----- #
@given(parse('we use the config "{config_file}"'), target_fixture="config_path")
@given('we use the config "<config_file>"', target_fixture="config_path")
def set_config(config_file, temp_dir, working_dir):
    # Move into temp dir as cwd
    os.chdir(temp_dir.name)

    # Copy the config file over
    config_source = os.path.join(working_dir, "data", "configs", config_file)
    config_dest = os.path.join(temp_dir.name, config_file)
    shutil.copy2(config_source, config_dest)

    # @todo make this only copy some journals over
    # Copy all of the journals over
    journal_source = os.path.join(working_dir, "data", "journals")
    journal_dest = os.path.join(temp_dir.name, "features", "journals")
    shutil.copytree(journal_source, journal_dest)

    # @todo get rid of this by using default config values
    # merge in version number
    if config_file.endswith("yaml") and os.path.exists(config_dest):
        # Add jrnl version to file for 2.x journals
        with open(config_dest, "a") as cf:
            cf.write("version: {}".format(__version__))

    return config_dest


@when(parse('we run "jrnl {command}"'))
@when('we run "jrnl <command>"')
def run(command, config_path, cli_run, capsys):
    args = split_args(command)
    status = 0

    # fmt: off
    # see: https://github.com/psf/black/issues/664
    with \
        patch("sys.argv", ['jrnl'] + args), \
        patch("jrnl.config.get_config_path", side_effect=lambda: config_path), \
        patch("jrnl.install.get_config_path", side_effect=lambda: config_path) \
    :
        try:
            cli(args)
        except SystemExit as e:
            status = e.code
    # fmt: on

    cli_run["status"] = status
    captured = capsys.readouterr()
    cli_run["stdout"] = captured.out
    cli_run["stderr"] = captured.err


@then("we should get no error")
def no_error(cli_run):
    assert cli_run["status"] == 0, cli_run["status"]


@then(parse('the output should match "{regex}"'))
def matches_std_output(regex, cli_run):
    out = cli_run["stdout"]
    matches = re.findall(regex, out)
    assert matches, f"\nRegex didn't match:\n{regex}\n{str(out)}\n{str(matches)}"


@then(parse("the output should contain\n{output}"))
@then(parse('the output should contain "{output}"'))
@then('the output should contain "<output>"')
def check_output_inline(output, cli_run):
    assert output and output in cli_run["stdout"]


@then(parse('the output should be "{expected_out}"'))
@then(parse("the output should be\n{expected_out}"))
def check_output(cli_run, expected_out):
    expected_out = expected_out.strip()
    actual_out = cli_run["stdout"].strip()
    assert (
        expected_out == actual_out
    ), f"Output does not match.\nExpected:\n{expected_out}\n---end---\nActual:\n{actual_out}\n---end---\n"


@then("the output should contain pyproject.toml version")
def check_output_version_inline(cli_run, toml_version):
    out = cli_run["stdout"]
    assert toml_version in out, toml_version


@then(parse('we should see the message "{text}"'))
def check_message(text, cli_run):
    out = cli_run["stderr"]
    assert text in out, [text, out]