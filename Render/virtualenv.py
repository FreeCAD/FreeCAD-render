# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2024 Howetuft <howetuft@gmail.com>                      *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2.1 of   *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Library General Public License for more details.                  *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with this program; if not, write to the Free Software   *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************

"""This module installs and manages a Python virtual environment for Render.

We set a Python virtual environment to host required external modules,
e.g. MaterialX.
This solution is preferred to system-wide ('pip install') or even
user-restricted installation ('pip install --user') via pip, as the new
'externally-managed-environment' feature starting from Python 3.11 will prevent
such installations.
But please note also this virtual environment is installed via bootstrap from
Pypa, and not from system venv module. Indeed, 'venv' is deliberately
omitted in base install by certain distributions (Ubuntu, Debian...).

With our bootstrapped virtual environment, the required external modules can
eventually be installed:
- without having to bother with distro's package management
- without requiring any elevation of user rights (sudo etc.).
"""

import os
import urllib.request
import urllib.parse
import tempfile
import subprocess
import shutil
import concurrent.futures
import functools

import FreeCAD as App
import FreeCADGui as Gui

from PySide import __version__ as PYSIDE_VERSION

from Render.utils import find_python
from Render.constants import PARAMS, WHEELSDIR
from Render.rdrexecutor import RendererExecutor, ExporterWorker

RENDER_VENV_FOLDER = ".rendervenv"
RENDER_VENV_DIR = os.path.join(App.getUserAppDataDir(), RENDER_VENV_FOLDER)

# RENDERVENV = RenderVirtualEnv()  # Not workable yet
RENDERVENV = None
QTBASE = "PySide"  # in ("PyQt", "PySide")

# API


def ensure_rendervenv():
    """Ensure Render virtual environment is available and up-to-date."""
    errormsg = "[Render][Init] Virtual environment error\n"
    worker = ExporterWorker(rendervenv_worker, [], errormsg)
    executor = RendererExecutor(worker)
    executor.start()
    executor.join()


def rendervenv_worker():
    """Worker for ensure_rendervenv."""

    _msg("Checking dependencies...")

    try:
        # Step 1: Check if virtual environment exists at location
        # RENDER_VENV_DIR. Otherwise, create it
        _log("Checking Render virtual environment")
        if not _check_venv():
            _msg(">>> Environment folder does not exist - Creating")
            _create_virtualenv()
        else:
            _log(">>> Environment folder exists: OK")

        # Step 2: Check whether Python is available.
        # Otherwise, recreate (try three times)
        for _ in range(3):
            if get_venv_python() is None:
                _msg(
                    ">>> Environment does not provide Python "
                    "- Recreating environment"
                )
                remove_virtualenv(purge=False)
                _create_virtualenv()
            else:
                _log(">>> Environment provides Python: OK")
                break
        else:
            raise VenvError(3)

        # Step 3: Check whether pip is available
        # Otherwise, bootstrap (try three times)
        for _ in range(3):
            if _get_venv_pip() is None:
                _msg(">>> Environment does not provide Pip - Repairing")
                url = "https://bootstrap.pypa.io/get-pip.py"
                _bootstrap(url)
            else:
                _log(">>> Environment provides Pip: OK")
                break
        else:
            raise VenvError(4)

        # Step 4: Update pip (optional)
        if PARAMS.GetBool("UpdatePip"):
            _log(">>> Updating pip")
            pip_install(
                "pip",
                options=[
                    "--upgrade",
                ],
                loglevel=1,
            )

        # Step 5: Check for needed packages - binaries
        packages = [
            "PyQt6",
            "PyQt6-WebEngine",
            "setuptools",
            "wheel",
            "renderplugin",
            "QtPy",
        ]

        if PARAMS.GetBool("MaterialX"):
            packages.append("materialx")

        # Commands for binaries
        options = [
            "--no-warn-script-location",
            "--only-binary=:all:",
            f"--find-links={WHEELSDIR}",
        ]
        commands = [
            (
                pip_install,
                package,
                options + (["-I"] if package == "renderplugin" else []),
                _log,
                1,
            )
            for package in packages
        ]

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(*command): package
                for command, package in zip(commands, packages)
            }
            errors = {}
            for future in concurrent.futures.as_completed(futures):
                package = futures[future]
                if not (return_code := future.result()):
                    _msg(f"Checking package '{package}' - OK")
                else:
                    _warn(
                        f"Checking package '{package}' - ERROR "
                        f"(return code: {return_code})"
                    )
                    errors[package] = return_code

        # Step 6: Report errors to user
        if errors:
            failed = ", ".join(f"'{p}'" for p in errors)
            _warn(
                f"WARNING - The following dependencies could not be installed:"
                f"{failed}"
            )

            statement = (
                f'"{get_venv_python()}" -u -m pip install --prefer-binary '
                f"--require-virtualenv {failed}"
            )
            _warn(
                "You may try to install those packages on your own with the "
                "following command-line statement:\n"
            )
            App.Console.PrintWarning(f"{statement}\n")

    except VenvError as error:
        msg = (
            "[Render][Init] Error - Failed to set virtual environment - "
            f"#{error.errorno} '{error.message}' - "
            "Some features may not be available...\n"
        )
        App.Console.PrintError(msg)
    else:
        if not errors:
            _log("Render virtual environment: OK")
        else:
            _warn(f"Render virtual environment: {len(errors)} error(s)")
        _msg("Done.")


def get_venv_python():
    """Get Python executable in Render virtual environment."""
    if os.name == "nt":
        python = "pythonw.exe"
    elif os.name == "posix":
        python = "python"
    else:
        raise VenvError(2)  # Unknown os.name

    binpath = _binpath()

    path = os.path.join(binpath, python)

    if not os.path.isfile(path):
        return None

    return path


def get_venv_python_version():
    """Get version of virtual environment Python interpreter."""
    path = get_venv_python()
    res = subprocess.run([path, "--version"], capture_output=True, check=False)
    res = tuple(int(c) for c in res.stdout.lstrip(b"Python ").split(b"."))
    return res


def get_venv_pyside_version():
    """Get version of PySide in virtual environment."""
    python_version = get_venv_python_version()
    _log(f"Virtual environment Python version: {str(python_version)}")
    if QTBASE == "PySide":
        if python_version >= (3, 9):
            return "PySide6"
        return "PySide2"
    if QTBASE == "PyQt":
        if python_version >= (3, 8):
            return "PyQt6"
        return "PyQt5"
    raise ValueError(QTBASE)


def pip_run(verb, package, options=None, log=None, loglevel=0):
    """Install package with pip in Render virtual environment.

    Returns: a subprocess.CompletedInstance"""
    options = options or []
    log = log or _log
    if not (executable := get_venv_python()):
        raise VenvError(3)
    cmd = [executable, "-u", "-m", "pip", verb] + options + [package]
    log(" ".join([">>>"] + cmd))
    environment = os.environ.copy()
    environment.pop("PYTHONHOME", None)
    environment.pop("PYTHONPATH", None)
    environment.pop("PIP_USER", None)
    with subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        env=environment,
    ) as proc:
        pads = " ".join(">>>" for _ in range(loglevel))
        for line in proc.stdout:
            log(f"{pads} {line}")
    return proc.returncode


pip_install = functools.partial(pip_run, "install")
pip_wheel = functools.partial(pip_run, "wheel")


def pip_uninstall(package):
    """Install (or uninstall) package with pip.

    Returns: a subprocess.CompletedInstance"""
    if not (executable := get_venv_python()):
        raise VenvError(3)
    result = subprocess.run(
        [executable, "-m", "pip", "uninstall", "-y", package],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return result


# Check


def _check_venv():
    """Check if virtual environment folder exists."""
    # Does path exists as a directory?
    return os.path.isdir(RENDER_VENV_DIR)


def _get_venv_pip():
    """Get pip executable in Render virtual environment."""
    if os.name == "nt":
        pip = "pip.exe"
    elif os.name == "posix":
        pip = "pip"
    else:
        raise VenvError(2)

    binpath = _binpath()

    path = os.path.join(binpath, pip)

    if not os.path.isfile(path):
        return None

    return path


# Repair


def _create_virtualenv():
    """Create a fresh Render virtual environment."""
    # We won't use system's pip or system's venv, in order to circumvent:
    # - system managed environment (Arch etc.)
    # - missing venv (Ubuntu etc.)
    # Instead, we will bootstrap everything from pypi
    # https://pypi.org/project/bootstrap-env
    url = "https://bootstrap.pypa.io/virtualenv.pyz"
    if not (python := find_python()):
        raise VenvError(0)
    with tempfile.TemporaryDirectory() as tmp:
        pyz = os.path.join(tmp, "virtualenv.pyz")
        urllib.request.urlretrieve(url, pyz)
        command = [
            python,
            "-I",
            "-u",
            pyz,
            RENDER_VENV_DIR,
            # "--system-site-packages",  Issue with snap
        ]
        _log(" ".join(command))
        subprocess.run(
            command,
            check=True,
        )


def remove_virtualenv(purge=True):
    """Remove Render virtual environment."""
    if purge:
        pip_run("cache", "purge")
    shutil.rmtree(RENDER_VENV_DIR, ignore_errors=True)


def _bootstrap(url):
    """Bootstrap a component in Render virtual environment."""
    _, _, path, _, _, _ = urllib.parse.urlparse(url)
    scriptname = os.path.split(path)[-1]
    python = get_venv_python()

    # Download script into temporary folder
    with tempfile.TemporaryDirectory() as tmp:
        script = os.path.join(tmp, scriptname)
        urllib.request.urlretrieve(url, script)
        _log(f">>> Bootstrapping {path}")
        subprocess.run([python, "-u", script], check=True)


# Error handling


class VenvError(Exception):
    """Exception class for error in Render virtual environment handling."""

    MESSAGES = {
        1: "Cannot find Python",
        2: "Unknown OS",
        3: "Python is not available in virtual environment",
        4: "Pip is not available in virtual environment",
    }

    def __init__(self, errorno):
        self._errorno = int(errorno)

    @property
    def message(self):
        """Return error message."""
        return self.MESSAGES.get(self._errorno, "Unknown error")

    @property
    def errorno(self):
        """Return error number."""
        return self._errorno


# Helpers


def _log(message):
    """Log function for Render virtual environment handling."""
    if not message:
        return
    # Trim ending newline
    if message.endswith("\n"):
        message = message[:-1]
    App.Console.PrintLog(f"[Render][Init] {message}\n")


def _msg(message):
    """Message function for Render virtual environment handling."""
    if not message:
        return
    # Trim ending newline
    if message.endswith("\n"):
        message = message[:-1]
    App.Console.PrintMessage(f"[Render][Init] {message}\n")
    _status(message)


def _warn(message):
    """Warn function for Render virtual environment handling."""
    if not message:
        return
    # Trim ending newline
    if message.endswith("\n"):
        message = message[:-1]
    App.Console.PrintWarning(f"[Render][Init] {message}\n")
    _status(message)


def _status(message):
    """Print to status bar."""
    if not message:
        return
    # Trim ending newline
    if message.endswith("\n"):
        message = message[:-1]
    if App.GuiUp:
        Gui.getMainWindow().statusBar().showMessage(
            f"Render Initialization - {message}\n"
        )


def _binpath():
    """Get path to binaries."""
    if os.name == "nt":
        path = os.path.join(RENDER_VENV_DIR, "Scripts")
    elif os.name == "posix":
        path = os.path.join(RENDER_VENV_DIR, "bin")
    else:
        raise VenvError(2)  # Unknown os.name
    return path


def get_venv_sitepackages():
    """Get site packages directory for virtual environment."""
    args = [
        get_venv_python(),
        "-c",
        "import sysconfig; print(sysconfig.get_paths()['purelib'])",
    ]
    env = os.environ
    env.pop("PYTHONHOME", None)
    result = subprocess.run(
        args, capture_output=True, text=True, env=env, check=False
    )
    result.check_returncode()
    return result.stdout.strip()
