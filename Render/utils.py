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


class RGB:
    """A RGB color, consistent with FreeCAD internals.

    Very important: by design, this color is in sRGB colorspace, like colors
    in FreeCAD.
    To get a proper input for renderers, one must convert this color to linear.
    """

    def __init__(self, color):
        """Initialize RGB.

        Arguments are in sRGB colorspace.

        Args:
            color -- a tuple containing a RGB(A) in sRGB colorspace
        """
        self._red, self._green, self._blue, *remain = color
        self._red = float(self._red)
        self._green = float(self._green)
        self._blue = float(self._blue)
        if remain:
            self._alpha = float(remain[0])
        else:
            self._alpha = 1.0

    _linearRGB = collections.namedtuple("_linearRGB", "r g b a")
    _sRGB = collections.namedtuple("_sRGB", "r g b a")

    def to_linear(self):
        """Convert color from srgb to linear.

        Decode gamma=2.2 correction. This function is useful to convert FCD
        colors (coded in srgb) to renderers inputs (expected in linear rgb).

        Returns:
            color in linear colorspace
        """
        return self._linearRGB(
            self._red**2.2,
            self._green**2.2,
            self._blue**2.2,
            self._alpha,
        )

    def to_linear_hex(self):
        """Convert color from srgb to linear hexadecimal.

        Decode gamma=2.2 correction. This function is useful to convert FCD
        colors (coded in srgb) to renderers inputs (expected in linear rgb).

        Returns:
            color in linear colorspace
        """
        lcol = self.to_linear()
        red = int(lcol.r * 255)
        green = int(lcol.g * 255)
        blue = int(lcol.b * 255)
        res = (red << 16) + (green << 8) + blue
        res = f"{res:06x}"
        return res

    def to_srgb(self):
        """Return color in srgb.

        Returns:
            color in sRGB colorspace
        """
        return self._sRGB(self._red, self._green, self._blue, self._alpha)

    @property
    def alpha(self):
        """Get alpha component."""
        return self._alpha

    @alpha.setter
    def alpha(self, alpha):
        """Set alpha component."""
        self._alpha = float(alpha)

    def set_transparency(self, transparency):
        """Set alpha channel from given transparency."""
        self._alpha = 1.0 - float(transparency) / 100

    def __str__(self):
        """String conversion - deactivated."""
        return f"{self._red},{self._green},{self._blue},{self._alpha}"

    @staticmethod
    def from_string(string):
        """Convert a ({r},{g},{b})-like string into RGB object."""
        float_tuple = map(float, ast.literal_eval(string))
        return RGB(float_tuple)

    @staticmethod
    def from_linear(lrgb):
        """Create a RGB from a linear RGB."""
        srgb = tuple(c ** (1.0 / 2.2) for c in lrgb[0:3])
        try:
            alpha = lrgb[3]
        except IndexError:
            return RGB(srgb)
        return RGB(srgb, alpha)

    @staticmethod
    def from_fcd_rgba(color, transparency=None):
        """Create a RGB from a FreeCAD RGBA.

        2 important points:
        - color is in sRGB colorspace
        - 'a' component is a **transparency** (not an opacity), in [0, 100]

        Args:
            rgb -- The rgb (in sRGB).
        """
        if transparency is not None:
            # RGB + transparency
            rgb = list(color)
            assert len(rgb) == 3
            rgba = rgb + [1.0 - transparency / 100]
            return RGB(rgba)

        # RGBA (except 'alpha' is transparency...)
        assert len(color) == 4
        rgba = list(color[0:3]) + [1.0 - color[3]]
        return RGB(rgba)


WHITE = RGB.from_linear((0.8, 0.8, 0.8))  # A balanced white for default colors

SUPERWHITE = RGB.from_linear((1.0, 1.0, 1.0))

CAR_RED = RGB.from_linear((0.8, 0.2, 0.2))


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
            "Render.prefpage",
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
