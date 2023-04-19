# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2020 Howetuft <howetuft@gmail.com>                      *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
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

"""This module implements some helpers for Render workbench."""

import collections
import ast
import sys
import importlib
import csv
import itertools
import functools

try:
    from draftutils.translate import translate as _translate  # 0.19
except ImportError:
    from Draft import translate as _translate  # 0.18

import PySide2

import FreeCAD as App
import FreeCADGui as Gui


translate = _translate


def debug(domain, object_name, msg):
    """Print debug message."""
    msg = f"[Render][{domain}] '{object_name}': {msg}\n"
    App.Console.PrintLog(msg)


def warn(domain, object_name, msg):
    """Print warning message."""
    msg = f"[Render][{domain}] '{object_name}': {msg}\n"
    App.Console.PrintWarning(msg)


def message(domain, object_name, msg):
    """Print normal message."""
    msg = f"[Render][{domain}] '{object_name}': {msg}\n"
    App.Console.PrintMessage(msg)


def getproxyattr(obj, name, default):
    """Get attribute on object's proxy.

    Behaves like getattr, but on Proxy property, and with mandatory default...
    """
    try:
        res = getattr(obj.Proxy, name, default)
    except AttributeError:
        res = default
    return res


RGB = collections.namedtuple("RGB", "r g b")
RGBA = collections.namedtuple("RGBA", "r g b a")


def str2rgb(string):
    """Convert a ({r},{g},{b})-like string into RGB object."""
    float_tuple = map(float, ast.literal_eval(string))
    return RGB._make(float_tuple)


def fcdcolor2rgba(fcdcolor):
    """Convert a FreeCAD color to RGBA.

    Main difference is 4th component: FreeCAD color stores transparency,
    whereas, in RGBA, alpha is opacity.
    """
    red, green, blue, transparency = fcdcolor
    return RGBA(red, green, blue, 1.0 - transparency)


def parse_csv_str(string, delimiter=";"):
    """Parse a csv string, with ";" as default delimiter.

    Multiline strings are accepted (but maybe should be avoided).
    Returns: a list of strings (one for each field)
    """
    if not string:
        return []
    rows = csv.reader(string.splitlines(), delimiter=delimiter)
    return list(itertools.chain(*rows))


def clamp(value, maxval=1e10):
    """Clamp value between -maxval and +maxval."""
    res = value
    res = res if res <= maxval else maxval
    res = res if res >= -maxval else -maxval
    return res


def reload(module_name=None):
    """Reload Render modules."""
    mods = (
        (
            "Render.base",
            "Render.camera",
            "Render.commands",
            "Render.constants",
            "Render.lights",
            "Render.imageviewer",
            "Render.rendermaterial",
            "Render.rdrhandler",
            "Render.rdrexecutor",
            "Render.renderables",
            "Render.rendermesh",
            "Render.utils",
            "Render.view",
            "Render.texture",
            "Render.material",
            "Render.project",
            "Render.taskpanels",
            "Render.help",
            "Render.groundplane",
            "Render.renderers.Appleseed",
            "Render.renderers.Cycles",
            "Render.renderers.Luxcore",
            "Render.renderers.Luxrender",
            "Render.renderers.Ospray",
            "Render.renderers.Pbrt",
            "Render.renderers.Povray",
            "Render.renderers.utils.sunlight",
            "Render.renderers.utils.misc",
            "Render.rendermesh_mp.vector3d",
            "Render.rendermesh_mixins",
            "Render",
        )
        if not module_name
        else (module_name,)
    )
    for mod in mods:
        try:
            module = sys.modules[mod]
        except KeyError:
            print(f"Skip '{mod}'")
        else:
            print(f"Reload '{mod}'")
            importlib.import_module(mod)
            importlib.reload(module)

    # Clear materials cache
    print("Clear material cache")
    rendermaterial = importlib.import_module("Render.rendermaterial")
    rendermaterial.clear_cache()


def set_dryrun(state):
    """Set dry run parameter on/off.

    Warning: debug purpose only. /!\\

    Args:
        state -- state to set dry run (boolean)
    """
    params = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Render")
    state = bool(state)
    params.SetBool("DryRun", state)
    msg = (
        "[Render][Debug] Dry run is on\n"
        if state
        else "[Render][Debug] Dry run is off\n"
    )
    App.Console.PrintMessage(msg)


set_dryrun_on = functools.partial(set_dryrun, state=True)
set_dryrun_off = functools.partial(set_dryrun, state=False)


def set_debug(state):
    """Set debug run parameter on/off.

    Warning: debug purpose only. /!\\

    Args:
        state -- state to set debug (boolean)
    """
    params = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Render")
    state = bool(state)
    params.SetBool("Debug", state)
    msg = (
        "[Render][Debug] Debug is on\n"
        if state
        else "[Render][Debug] Debug is off\n"
    )
    App.Console.PrintMessage(msg)


set_debug_on = functools.partial(set_debug, state=True)
set_debug_off = functools.partial(set_debug, state=False)


def set_memcheck(state):
    """Set memory checking parameter on/off.

    Warning: debug purpose only. /!\\

    Args:
        state -- state to set memory checking (boolean)
    """
    params = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Render")
    state = bool(state)
    params.SetBool("Memcheck", state)
    msg = (
        "[Render][Debug] Memcheck is on\n"
        if state
        else "[Render][Debug] Memcheck is off\n"
    )
    App.Console.PrintMessage(msg)


set_memcheck_on = functools.partial(set_memcheck, state=True)
set_memcheck_off = functools.partial(set_memcheck, state=False)


def last_cmd():
    """Return last executed renderer command (debug purpose)."""
    params = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Render")
    last_cmd_cache = params.GetString("LastCommand")
    return last_cmd_cache


def set_last_cmd(cmd):
    """Set last executed renderer command."""
    cmd = str(cmd)
    params = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Render")
    params.SetString("LastCommand", cmd)


def clear_report_view():
    """Clear report view in FreeCAD Gui."""
    if not App.GuiUp:
        return
    main_window = Gui.getMainWindow()

    report_view = main_window.findChild(
        PySide2.QtWidgets.QDockWidget, "Report view"
    )
    if report_view is None:
        App.Console.PrintWarning(
            "Unable to clear report view: QDockWidget not found\n"
        )
        return

    text_widget = report_view.findChild(
        PySide2.QtWidgets.QTextEdit, "Report view"
    )
    if text_widget is None:
        App.Console.PrintWarning(
            "Unable to clear report view: QTextEdit not found\n"
        )
        return

    text_widget.clear()


def grouper(iterable, number, *, incomplete="ignore", fillvalue=None):
    "Collect data into non-overlapping fixed-length chunks or blocks"
    # From Python documentation (itertools module)
    # grouper('ABCDEFG', 3, fillvalue='x') --> ABC DEF Gxx
    # grouper('ABCDEFG', 3, incomplete='ignore') --> ABC DEF
    args = [iter(iterable)] * number
    if incomplete == "fill":
        return itertools.zip_longest(*args, fillvalue=fillvalue)
    if incomplete == "ignore":
        return zip(*args)

    raise ValueError("Expected fill or ignore")


class SharedWrapper:
    """A wrapper for shared objects containing tuples."""

    def __init__(self, seq, tuple_length):
        self.seq = seq
        self.tuple_length = tuple_length

    def __len__(self):
        return len(self.seq) * self.tuple_length

    def __iter__(self):
        seq = self.seq
        return itertools.chain.from_iterable(seq)
