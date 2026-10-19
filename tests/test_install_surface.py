"""DEC3=B install-surface contract: a non-editable install must fail loudly.

The repository deliberately ships `data/synthetic/` outside the package
(README "不承诺 wheel 安装面"), so a wheel install has no frozen artifacts.
The contract is *not* "wheel works" but "wheel degrades loudly":

  - wheel content carries no `data/` tree at all;
  - installed `selftest` exits 1 and names `files_present`;
  - installed `validate` on the repo-relative path exits 2 (log file not found).

Running this needs network (build isolation fetches setuptools >= 77) and a
scratch venv, so it is opt-in:

    PROCESS_ATLAS_INSTALL_SURFACE=1 python -m pytest tests/test_install_surface.py -q
"""

import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)

_ENV_FLAG = "PROCESS_ATLAS_INSTALL_SURFACE"

pytestmark = [
    pytest.mark.install_surface,
    pytest.mark.skipif(
        os.environ.get(_ENV_FLAG) != "1",
        reason="opt-in: needs network + scratch venv; set %s=1" % _ENV_FLAG,
    ),
]


def _venv_python(venv_dir):
    if os.name == "nt":
        return os.path.join(venv_dir, "Scripts", "python.exe")
    return os.path.join(venv_dir, "bin", "python")


def _run(argv, cwd):
    """Run and return (exit_code, stdout, stderr) — exit code read, never piped."""
    proc = subprocess.run(
        argv,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


@pytest.fixture(scope="module")
def installed(tmp_path_factory):
    """Build the wheel from the working tree, install it into a scratch venv."""
    scratch = str(tmp_path_factory.mktemp("install_surface"))
    wheel_dir = os.path.join(scratch, "wheel")
    venv_dir = os.path.join(scratch, "venv")
    work_dir = os.path.join(scratch, "work")
    for d in (wheel_dir, work_dir):
        os.makedirs(d)

    code, out, err = _run(
        [sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "-w", wheel_dir],
        cwd=_REPO,
    )
    assert code == 0, "wheel build failed (exit %s)\n%s\n%s" % (code, out, err)

    wheels = [n for n in os.listdir(wheel_dir) if n.endswith(".whl")]
    assert len(wheels) == 1, wheels
    wheel_path = os.path.join(wheel_dir, wheels[0])

    code, out, err = _run([sys.executable, "-m", "venv", venv_dir], cwd=scratch)
    assert code == 0, "venv creation failed (exit %s)\n%s\n%s" % (code, out, err)

    py = _venv_python(venv_dir)
    code, out, err = _run([py, "-m", "pip", "install", wheel_path], cwd=scratch)
    assert code == 0, "wheel install failed (exit %s)\n%s\n%s" % (code, out, err)

    return {"python": py, "wheel": wheel_path, "work": work_dir}


def test_wheel_carries_no_data_tree(installed):
    with zipfile.ZipFile(installed["wheel"]) as zf:
        names = zf.namelist()
    assert not [n for n in names if n.startswith("data/")], names
    assert not [n for n in names if "/data/" in n], names
    assert "process_atlas/cli.py" in names, names


def test_installed_selftest_exits_1_naming_files_present(installed):
    code, out, err = _run(
        [installed["python"], "-m", "process_atlas.cli", "selftest"], cwd=installed["work"]
    )
    assert code == 1, "expected selftest exit 1 on a wheel install, got %s\n%s\n%s" % (
        code, out, err)
    assert "files_present" in err, err


def test_installed_validate_exits_2_on_missing_log(installed):
    code, out, err = _run(
        [installed["python"], "-m", "process_atlas.cli", "validate", "data/synthetic/events.csv"],
        cwd=installed["work"],
    )
    assert code == 2, "expected validate exit 2 on a wheel install, got %s\n%s\n%s" % (
        code, out, err)
    assert "log file not found" in err, err


@pytest.fixture(scope="module", autouse=True)
def _cleanup(installed):
    yield
    shutil.rmtree(os.path.dirname(installed["work"]), ignore_errors=True)
