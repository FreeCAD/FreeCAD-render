# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2017 Yorik van Havre <yorik@uncreated.net>              *
# *   Copyright (c) 2021 Howetuft <howetuft@gmail.com>                      *
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

"""This module implements GUI task panels for Render workbench."""


import os
import re
from enum import Enum, auto

from PySide.QtGui import (
    QPushButton,
    QColor,
    QColorDialog,
    QPixmap,
    QIcon,
    QFormLayout,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QLayout,
    QListView,
    QLineEdit,
    QDoubleValidator,
    QGridLayout,
    QRadioButton,
    QGroupBox,
    QLabel,
    QSizePolicy,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
)
from PySide.QtCore import (
    QT_TRANSLATE_NOOP,
    QObject,
    SIGNAL,
    Qt,
    QLocale,
    QSize,
)


import FreeCAD as App
import FreeCADGui as Gui

from ArchMaterial import _ArchMaterialTaskPanel

from Render.constants import (
    TASKPAGE,
    VALID_RENDERERS,
    ICONDIR,
    WBMATERIALDIR,
    FCDMATERIALDIR,
    USERMATERIALDIR,
)
from Render.utils import str2rgb, translate, parse_csv_str
from Render.rendermaterial import (
    STD_MATERIALS,
    STD_MATERIALS_PARAMETERS,
    is_valid_material,
    passthrough_keys,
)
from Render.texture import str2imageid, str2imageid_ext


class ColorPicker(QPushButton):
    """A color picker widget.

    This widget provides a button, with a colored square icon, which triggers
    a color dialog when it is pressed.
    """

    def __init__(self, color=QColor(127, 127, 127)):
        """Initialize ColorPicker.

        Args:
            color -- The default color of the picker
        """
        super().__init__()
        self.color = QColor(color)
        self._set_icon(self.color)
        QObject.connect(self, SIGNAL("clicked()"), self.on_button_clicked)

    def on_button_clicked(self):
        """Respond to button clicked event (callback)."""
        color = QColorDialog.getColor(initial=self.color)
        if color.isValid():
            self.color = color
            self._set_icon(color)

    def _set_icon(self, color):
        """Set the colored square icon."""
        colorpix = QPixmap(16, 16)
        colorpix.fill(color)
        self.setIcon(QIcon(colorpix))

    def set_color(self, color):
        """Set widget color value."""
        self.color = QColor(color)
        self._set_icon(self.color)

    def get_color_text(self):
        """Get widget color value, in text format."""
        color = self.color
        return f"({color.redF()},{color.greenF()},{color.blueF()})"


class ColorOption(Enum):
    """Options for Colors in Material."""

    OBJECT = auto()
    CONSTANT = auto()
    TEXTURE = auto()


class TexturePicker(QComboBox):
    """A texture picker widget.

    This widget provides a combo box, allowing to select a texture.
    """

    def __init__(self, image_list, current_image):
        """Initialize texture picker.

        Args:
            image_list -- list of texture images (list of Texture.ImageId)
            current_image -- current texture image in list (Texture.ImageId)
        """
        super().__init__()
        current_item = -1
        for imageid in image_list:
            texture = App.ActiveDocument.getObject(imageid.texture)
            full_filename = texture.getPropertyByName(imageid.image)
            filename = (
                f'"{os.path.basename(full_filename)}"'
                if full_filename
                else "<No file>"
            )
            texturelabel = texture.Label
            text = f"{texturelabel} - {imageid.image} ({filename})"
            self.addItem(text, imageid)
            if imageid == current_image:
                current_item = self.count() - 1
        self.setCurrentIndex(current_item)

    def get_texture_text(self):
        """Get user selected value in text format."""
        imageid = self.currentData()
        res = (
            f"('{imageid.texture}','{imageid.image}')"
            if imageid
            else "('','')"
        )
        return res


class TexturePickerExt(QWidget):
    """A texture picker widget, with a scalar entry field.

    This widget provides a combo box, allowing to select a texture, and an
    float entry field to specify a scalar for the texture (can be factor,
    strength, distance...)
    It is mostly intended for bump texture.
    """

    def __init__(
        self, image_list, current_image, init_scalar, scalar_label=None
    ):
        """Initialize texture picker.

        Args:
            image_list -- list of texture images (list of Texture.ImageId)
            current_image -- current texture image in list (Texture.ImageId)
            init_scalar -- initialization value for scalar (float)
            scalar_label -- label for scalar (string)
        """
        super().__init__()

        # Initialize layout
        self.setLayout(QVBoxLayout())

        # Normalize scalar
        try:
            init_scalar = QLocale().toString(float(init_scalar))
        except (ValueError, TypeError):
            init_scalar = None

        # Texture picker
        self.texturepicker = TexturePicker(image_list, current_image)
        self.layout().addWidget(self.texturepicker)

        # Scalar box
        scalar_layout = QHBoxLayout()
        self.layout().addLayout(scalar_layout)

        if scalar_label is not None:
            self.scalarlabel = QLabel()
            self.scalarlabel.setText(scalar_label)
            scalar_layout.addWidget(self.scalarlabel)

        self.scalarbox = QLineEdit()
        self.scalarbox.setAlignment(Qt.AlignRight)
        self.scalarbox.setValidator(QDoubleValidator())
        self.scalarbox.setText(init_scalar)
        scalar_layout.addWidget(self.scalarbox)
        # self.scalarbox.setEnabled(False)

    def get_texture_text(self):
        """Get user selected value in text format."""
        imageid = self.texturepicker.currentData()
        scalar, _ = QLocale().toDouble(self.scalarbox.text())
        res = (
            f"('{imageid.texture}','{imageid.image}','{scalar}')"
            if imageid
            else f"('','','{scalar}')"
        )
        return res


class ColorPickerExt(QGroupBox):
    """An extended color picker widget.

    This widget provides a color picker, and also a checkbox that allows to
    specify to use object color in lieu of color selected in the picker.
    """

    def __init__(
        self,
        option=ColorOption.OBJECT,
        color=QColor(127, 127, 127),
        image_list=None,
        current_image=None,
    ):
        """Initialize widget.

        Args:
            color -- RGB color used to initialize the color picker
            use_object_color -- boolean used to initialize the 'use object
                color' checkbox
        """
        super().__init__()
        if image_list is None:
            image_list = []
        self.setLayout(QGridLayout())
        self.layout().setColumnStretch(0, 0)
        self.layout().setColumnStretch(1, 10)

        # Object color option
        self.button_objectcolor = QRadioButton(
            translate("Render", "Use object color")
        )
        self.layout().addWidget(self.button_objectcolor, 0, 0)

        # Constant color option
        self.button_constantcolor = QRadioButton(
            translate("Render", "Use constant color")
        )
        self.colorpicker = ColorPicker(color)
        self.layout().addWidget(self.button_constantcolor, 1, 0)
        self.layout().addWidget(self.colorpicker, 1, 1)
        self.colorpicker.setEnabled(False)
        QObject.connect(
            self.button_constantcolor,
            SIGNAL("toggled(bool)"),
            self.colorpicker.setEnabled,
        )

        # Texture option
        self.button_texture = QRadioButton(translate("Render", "Use texture"))
        self.texturepicker = TexturePicker(image_list, current_image)
        self.layout().addWidget(self.button_texture, 2, 0)
        self.layout().addWidget(self.texturepicker, 2, 1)
        self.texturepicker.setEnabled(False)
        QObject.connect(
            self.button_texture,
            SIGNAL("toggled(bool)"),
            self.texturepicker.setEnabled,
        )

        # Initialize (select button)
        if option == ColorOption.OBJECT:
            self.button_objectcolor.setChecked(True)
        elif option == ColorOption.CONSTANT:
            self.button_constantcolor.setChecked(True)
        elif option == ColorOption.TEXTURE:
            self.button_texture.setChecked(True)

    def get_value(self):
        """Get widget output value."""
        # TODO (add "Constant" if constant...)
        if self.button_objectcolor.isChecked():
            res = ["Object"]
        elif self.button_constantcolor.isChecked():
            res = []
        elif self.button_texture.isChecked():
            res = ["Texture"]
            res += [self.texturepicker.get_texture_text()]

        res += [self.colorpicker.get_color_text()]
        return ";".join(res)


class FloatOption(Enum):
    """Options for Float in Material."""

    CONSTANT = auto()
    TEXTURE = auto()


class FloatBox(QGroupBox):
    """A float value input box widget.

    This widget provides a field to enter a float, and also a
    checkbox that allows to specify a texture in lieu of the float.
    """

    def __init__(
        self,
        option=FloatOption.CONSTANT,
        default=0.0,
        image_list=None,
        current_image=None,
    ):
        """Initialize widget.

        Args:
          option -- selected option (constant/texture) at initialization
          default -- default value
          image_list -- list of selectable image for texture
          current_image -- selected image index at initialization
        """
        super().__init__()

        # Normalize arguments
        if image_list is None:
            image_list = []
        try:
            default = QLocale().toString(float(default))
        except (ValueError, TypeError):
            default = None

        # Initialize layout
        self.setLayout(QGridLayout())
        self.layout().setColumnStretch(0, 0)
        self.layout().setColumnStretch(1, 10)

        # Constant value option
        self.button_constantvalue = QRadioButton(
            translate("Render", "Use constant value")
        )
        self.floatbox = QLineEdit()
        self.floatbox.setAlignment(Qt.AlignRight)
        self.floatbox.setValidator(QDoubleValidator())
        self.floatbox.setText(default)
        self.layout().addWidget(self.button_constantvalue, 1, 0)
        self.layout().addWidget(self.floatbox, 1, 1)
        self.floatbox.setEnabled(False)
        QObject.connect(
            self.button_constantvalue,
            SIGNAL("toggled(bool)"),
            self.floatbox.setEnabled,
        )

        # Texture option
        self.button_texture = QRadioButton(translate("Render", "Use texture"))
        self.texturepicker = TexturePicker(image_list, current_image)
        self.layout().addWidget(self.button_texture, 2, 0)
        self.layout().addWidget(self.texturepicker, 2, 1)
        self.texturepicker.setEnabled(False)
        QObject.connect(
            self.button_texture,
            SIGNAL("toggled(bool)"),
            self.texturepicker.setEnabled,
        )

        # Initialize (select button)
        if option == FloatOption.CONSTANT:
            self.button_constantvalue.setChecked(True)
        elif option == FloatOption.TEXTURE:
            self.button_texture.setChecked(True)

    def get_value(self):
        """Get widget output value."""
        # TODO (add "Constant" if constant...)
        if self.button_constantvalue.isChecked():
            res = []
        elif self.button_texture.isChecked():
            res = ["Texture"]
            res += [self.texturepicker.get_texture_text()]
        else:
            res = []

        floatval, _ = QLocale().toDouble(self.floatbox.text())
        res += [str(floatval)]

        return ";".join(res)


class TexonlyOption(Enum):
    """Options for normals in Material."""

    NO_VALUE = auto()
    TEXTURE = auto()


class TexonlyPicker(QGroupBox):
    """A texture only input widget.

    This widget provides a way to enter a texture only, or nothing,
    like a bump texture in a material.
    """

    def __init__(
        self,
        option=TexonlyOption.NO_VALUE,
        image_list=None,
        current_image=None,
        with_scalar=False,
        scalar_init=1.0,
        scalar_label=None,
    ):
        """Initialize widget.

        Args:
          option -- selected option (no use/texture) at initialization
          image_list -- list of selectable image for texture
          current_image -- selected image index at initialization
          with_scalar -- flag to add a 'scalar' entry field
          scalar_init -- value to initialize 'scalar' field
          scalar_label -- label for scalar entry field
        """
        super().__init__()

        # Normalize arguments
        if image_list is None:
            image_list = []

        # Initialize layout
        self.setLayout(QGridLayout())
        self.layout().setColumnStretch(0, 0)
        self.layout().setColumnStretch(1, 10)

        # No value option
        self.button_novalue = QRadioButton(translate("Render", "Don't use"))
        self.layout().addWidget(self.button_novalue, 0, 0)

        # Texture option
        self.button_texture = QRadioButton(translate("Render", "Use texture"))
        if not with_scalar:
            self.texturepicker = TexturePicker(image_list, current_image)
        else:
            self.texturepicker = TexturePickerExt(
                image_list, current_image, scalar_init, scalar_label
            )
        self.layout().addWidget(self.button_texture, 1, 0)
        self.layout().addWidget(self.texturepicker, 1, 1)
        self.texturepicker.setEnabled(False)
        QObject.connect(
            self.button_texture,
            SIGNAL("toggled(bool)"),
            self.texturepicker.setEnabled,
        )

        # Initialize (select button)
        if option == TexonlyOption.NO_VALUE:
            self.button_novalue.setChecked(True)
        elif option == TexonlyOption.TEXTURE:
            self.button_texture.setChecked(True)

    def get_value(self):
        """Get widget output value."""
        if self.button_novalue.isChecked():
            res = []
        elif self.button_texture.isChecked():
            res = ["Texture"]
            res += [self.texturepicker.get_texture_text()]
        else:
            res = []

        return ";".join(res)


class MaterialSettingsTaskPanel:
    """Task panel to edit Material render settings."""

    NONE_MATERIAL_TYPE = QT_TRANSLATE_NOOP(
        "MaterialSettingsTaskPanel", "<None>"
    )

    def __init__(self, obj=None):
        """Initialize task panel."""
        self.form = Gui.PySideUic.loadUi(TASKPAGE)
        self.tabs = self.form.RenderTabs
        self.tabs.setCurrentIndex(0)
        self.layout = self.tabs.findChild(QFormLayout, "FieldsLayout")
        self.material_type_combo = self.form.findChild(
            QComboBox, "MaterialType"
        )

        # Initialize material name combo
        self.material_combo = self.form.MaterialNameLayout.itemAt(0).widget()
        self.existing_materials = {
            obj.Label: obj
            for obj in App.ActiveDocument.Objects
            if is_valid_material(obj)
        }
        self.material_combo.addItems(list(self.existing_materials.keys()))
        self.material_combo.currentTextChanged.connect(
            self.on_material_name_changed
        )

        # Initialize material type combo
        # Note: itemAt(0) is label, itemAt(1) is combo
        self.material_type_combo = self.form.findChild(
            QComboBox, "MaterialType"
        )
        material_type_set = [
            MaterialSettingsTaskPanel.NONE_MATERIAL_TYPE
        ] + list(STD_MATERIALS)
        self.material_type_combo.addItems(material_type_set)
        self.material_type_combo.currentTextChanged.connect(
            self.on_material_type_changed
        )
        self._set_layout_visible("FieldsLayout", False)
        self.fields = []

        # Initialize Father layout
        self._set_layout_visible("FatherLayout", False)
        self.father_field = self.form.FatherLayout.itemAt(1).widget()

        # Initialize Passthru Renderers selector
        rdrwidget = self.form.findChild(QListWidget, "Renderers")
        for rdr in VALID_RENDERERS:
            item = QListWidgetItem()
            item.setText(rdr)
            item.setIcon(QIcon(os.path.join(ICONDIR, f"{rdr}.svg")))
            rdrwidget.addItem(item)
        rdrwidget.setViewMode(QListView.IconMode)
        rdrwidget.setIconSize(QSize(48, 48))
        rdrwidget.setMaximumWidth(96)
        rdrwidget.setSpacing(6)
        rdrwidget.setMovement(QListView.Static)
        rdrwidget.currentTextChanged.connect(
            self.on_passthrough_renderer_changed
        )
        self.passthru_rdr = rdrwidget
        self.passthru = self.form.findChild(QPlainTextEdit, "PassthroughEdit")
        self.passthru.textChanged.connect(self.on_passthrough_text_changed)
        self.passthru_cache = {}
        self._set_layout_visible("PassthruLayout", False)

        # Get selected material and initialize material type combo with it
        selection = {obj.Label for obj in Gui.Selection.getSelection()}
        selected_materials = selection & self.existing_materials.keys()
        try:
            selected_material = selected_materials.pop()
        except KeyError:
            pass
        else:
            self.material_combo.setCurrentText(selected_material)

    def on_material_name_changed(self, material_name):
        """Respond to material name changed event."""
        # Clear passthrough cache
        self.passthru_cache = {}

        # Find material
        try:
            material = self.existing_materials[material_name]
        except KeyError:
            # Unknown material: disable everything
            self._set_layout_visible("FieldsLayout", False)
            self._set_layout_visible("FatherLayout", False)
            self._set_layout_visible("PassthruLayout", False)
            return

        # Retrieve material type
        self._set_layout_visible("FieldsLayout", True)
        material_type_combo = self.form.findChild(QComboBox, "MaterialType")
        try:
            material_type = material.Material["Render.Type"]
        except KeyError:
            material_type_combo.setCurrentIndex(0)
        else:
            if not material_type:
                material_type = MaterialSettingsTaskPanel.NONE_MATERIAL_TYPE
            material_type_combo.setCurrentText(material_type)

        # Retrieve passthrough
        self._set_layout_visible("PassthruLayout", True)
        try:
            renderer = self.passthru_rdr.currentItem().text()
        except AttributeError:
            renderer = None
        self._populate_passthru(renderer, material)

        # Retrieve material father
        self._set_layout_visible("FatherLayout", True)
        try:
            father = material.Material["Father"]
        except KeyError:
            father = ""
        self.father_field.setText(father)

    def on_material_type_changed(self, material_type):
        """Respond to material type changed event."""
        # Get parameters list
        try:
            params = STD_MATERIALS_PARAMETERS[material_type]
        except KeyError:
            self._delete_fields()
        else:
            self._delete_fields()
            mat_name = self.material_combo.currentText()
            material = self.existing_materials[mat_name]
            # Get available texture images
            images = material.Proxy.get_texture_images()
            for param in params:
                value = self.existing_materials[mat_name].Material.get(
                    f"Render.{material_type}.{param.name}"
                )
                self._add_field(param, value, images)

    def on_passthrough_renderer_changed(self, renderer):
        """Respond to passthrough renderer changed event."""
        mat_name = self.material_combo.currentText()
        material = self.existing_materials[mat_name]
        self._populate_passthru(renderer, material)

    def on_passthrough_text_changed(self):
        """Respond to passthrough renderer changed event."""
        rdr = self.passthru_rdr.currentItem()
        if not rdr:
            return
        text = self.passthru.toPlainText()
        self.passthru_cache[rdr.text()] = text

    PASSTHROUGH_KEYS = {r: passthrough_keys(r) for r in VALID_RENDERERS}

    def _populate_passthru(self, renderer, material):
        """Populate passthrough edit field."""
        # If no renderer or no material provided, disable field and quit
        if not renderer or not material:
            self.passthru.setPlainText("")
            self.passthru.setEnabled(False)
            return

        self.passthru.setEnabled(True)

        # If renderer passthrough is already in cache (and possibly modified),
        # use the cache; otherwise, retrieve it from 'material'.
        try:
            text = self.passthru_cache[renderer]
        except KeyError:
            keys = self.PASSTHROUGH_KEYS[renderer]
            common_keys = keys & material.Material.keys()
            lines = [material.Material[k] for k in sorted(common_keys)]
            text = "\n".join(lines)

        self.passthru.setPlainText(text)

    def _set_layout_visible(self, layout_name, flag):
        """Make a layout visible/invisible, according to flag."""
        layout = self.form.findChild(QLayout, layout_name)
        for index in range(layout.count()):
            item = layout.itemAt(index)
            item.widget().setVisible(flag)

    def _add_field(self, param, value, teximages=None):
        """Add a field to the task panel.

        Args:
            param -- Parameter description (rendermaterial.Param)
            value -- Initial value
            teximages -- List of appliable texture images (texture.ImageInfo)
        """
        name = param.name
        if teximages is None:
            teximages = []

        if param.type == "float":
            if value:
                # Parse value and initialize a FloatBox accordingly
                texture = None  # Default value
                parsedvalue = parse_csv_str(value)
                if "Constant" in parsedvalue:
                    # Constant
                    option = FloatOption.CONSTANT
                    default = parsedvalue[1]
                elif "Texture" in parsedvalue:
                    # Texture
                    option = FloatOption.TEXTURE
                    texture = str2imageid(parsedvalue[1])
                    if len(parsedvalue) > 2:
                        # Ability to specify fallback color
                        default = parsedvalue[2]
                    else:
                        default = None
                else:
                    # Constant (fallback)
                    option = FloatOption.CONSTANT
                    default = parsedvalue[0]
                widget = FloatBox(option, default, teximages, texture)
            else:
                # value is empty, default initialization
                widget = FloatBox(image_list=teximages)
            self.fields.append((name, widget.get_value))
        elif param.type == "RGB":
            if value:
                # Parse value and initialize a ColorPickerExt accordingly
                parsedvalue = parse_csv_str(value)
                color = (0.8, 0.8, 0.8)  # Default value
                texture = None  # Default value
                if "Object" in parsedvalue:
                    # Object color
                    option = ColorOption.OBJECT
                    if len(parsedvalue) > 1:
                        color = str2rgb(parsedvalue[1])
                elif "Constant" in parsedvalue:
                    # Constant
                    option = ColorOption.CONSTANT
                    color = str2rgb(parsedvalue[1])
                elif "Texture" in parsedvalue:
                    # Texture
                    option = ColorOption.TEXTURE
                    texture = str2imageid(parsedvalue[1])
                    if len(parsedvalue) > 2:
                        # Ability to specify fallback color
                        color = str2rgb(parsedvalue[2])
                else:
                    # Constant (fallback)
                    option = ColorOption.CONSTANT
                    color = str2rgb(parsedvalue[0])
                qcolor = QColor.fromRgbF(*color)
                widget = ColorPickerExt(option, qcolor, teximages, texture)
            else:
                # value is empty, default initialization
                widget = ColorPickerExt(image_list=teximages)
            self.fields.append((name, widget.get_value))
        elif param.type == "texonly":
            if value:
                # Parse value and initialize a TexonlyPicker accordingly
                parsedvalue = parse_csv_str(value)
                texture = None  # Default value
                if "Texture" in parsedvalue:
                    # Texture
                    option = TexonlyOption.TEXTURE
                    texture = str2imageid(parsedvalue[1])
                else:
                    # No value (fallback)
                    option = TexonlyOption.NO_VALUE
                    texture = None
                widget = TexonlyPicker(option, teximages, texture)
            else:
                # value is empty, default initialization
                widget = TexonlyPicker(image_list=teximages)
            self.fields.append((name, widget.get_value))
        elif param.type == "texscalar":
            label = translate("Render", "Factor:")
            if value:
                # Parse value and initialize a TexonlyPicker "with scalar"
                parsedvalue = parse_csv_str(value)
                texture = None  # Default value
                if "Texture" in parsedvalue:
                    # Texture
                    option = TexonlyOption.TEXTURE
                    texture, scalar = str2imageid_ext(parsedvalue[1])
                else:
                    # No value (fallback)
                    option = TexonlyOption.NO_VALUE
                    texture = None
                widget = TexonlyPicker(
                    option,
                    teximages,
                    texture,
                    with_scalar=True,
                    scalar_init=scalar,
                    scalar_label=label,
                )
            else:
                # value is empty, default initialization
                widget = TexonlyPicker(
                    image_list=teximages, with_scalar=True, scalar_label=label
                )
            self.fields.append((name, widget.get_value))
        else:
            # Fallback to string input
            widget = QLineEdit()
            self.fields.append((name, widget.text))

        # Set widget tooltip
        widget.setToolTip(param.desc)

        # Prepare label
        text = [a for a in re.split(r"([A-Z][a-z]*\d*)", param.name) if a]
        text = " ".join(text)
        label = QLabel()
        label.setText(text + ":")
        size_policy = QSizePolicy()
        size_policy.setVerticalPolicy(QSizePolicy.Expanding)
        label.setSizePolicy(size_policy)

        # Add label and widget
        layout = self.form.findChild(QLayout, "FieldsLayout")
        layout.addRow(label, widget)

    def _delete_fields(self):
        """Delete all fields, except the first one (MaterialType selector)."""
        layout = self.form.findChild(QLayout, "FieldsLayout")
        for i in reversed(range(layout.count())):
            widget = layout.itemAt(i).widget()
            if widget.objectName() not in (
                "MaterialType",
                "MaterialTypeLabel",
            ):
                widget.setParent(None)
        self.fields = []

    def _write_fields(self):
        """Write task panel fields to FreeCAD material."""
        # Find material
        mat_name = self.material_combo.currentText()
        try:
            material = self.existing_materials[mat_name]
        except KeyError:
            return
        tmp_mat = material.Material.copy()

        # Set render type and associated fields
        if self.material_type_combo.currentIndex():
            render_type = self.material_type_combo.currentText()
            if render_type == MaterialSettingsTaskPanel.NONE_MATERIAL_TYPE:
                render_type = ""
            tmp_mat["Render.Type"] = str(render_type)

            # Set fields
            for field in self.fields:
                field_name, get_value = field
                param_name = f"Render.{render_type}.{field_name}"
                tmp_mat[param_name] = str(get_value())

        # Set passthru
        pthr_keys = self.PASSTHROUGH_KEYS
        for rdr, text in self.passthru_cache.items():
            # Clear existing lines for rdr
            for key in pthr_keys[rdr]:
                tmp_mat.pop(key, None)
            # Fill with new lines for rdr
            lines = dict(zip(sorted(pthr_keys[rdr]), text.splitlines()))
            tmp_mat.update(lines)

        # Set father
        father = self.father_field.text()
        if father:
            tmp_mat["Father"] = str(father)

        # Write to material
        material.Material = tmp_mat

    def accept(self):
        """Respond to user acceptation (OK button).

        Write all task panel fields to material
        """
        self._write_fields()
        Gui.ActiveDocument.resetEdit()
        Gui.Control.closeDialog()
        # Modifying material may require projects recomputation:
        App.ActiveDocument.recompute()
        return True


class MaterialTaskPanel(_ArchMaterialTaskPanel):
    """Task panel to create and edit Material.

    Essentially derived from Arch Material Task Panel, except for
    material cards directory.
    """

    def __init__(self, obj=None):
        super().__init__(obj)
        self.form.setWindowTitle("Render Material")
        # Disable copy from existant (buggy with textures...)
        self.form.comboBox_FromExisting.hide()

        # Disable color buttons (error-prone) and replace with message
        self.form.ButtonColor.hide()
        self.form.label.hide()
        self.form.ButtonSectionColor.hide()
        self.form.label_8.hide()
        self.form.SpinBox_Transparency.hide()
        self.form.label_6.hide()
        msg = """\
*Nota: If you want to set color or other aspect parameters of the material, \
please edit 'Render settings' from material context menu.*"""
        label = QLabel(msg)
        label.setTextFormat(Qt.TextFormat.MarkdownText)
        self.form.layout().addWidget(label)

    def fillMaterialCombo(self):
        """Fill Material combo box.

        Look for cards in both Workbench directory and Materials sub-folder
        in the user folder.
        User cards with same name will override system cards.
        """
        paths = [
            ("USER", USERMATERIALDIR),
            ("RENDER", WBMATERIALDIR),
        ]
        params = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Render")
        if params.GetBool("UseFCDMaterials", False):
            paths.append(("FREECAD", FCDMATERIALDIR))
        self.cards = {
            f"{d} - {os.path.splitext(f)[0]}": os.path.join(p, f)
            for d, p in paths
            if os.path.exists(p)
            for f in os.listdir(p)
            if os.path.splitext(f)[1].upper() == ".FCMAT"
        }
        for k in sorted(self.cards.keys()):
            self.form.comboBox_MaterialsInDir.addItem(k)

    def accept(self):
        """Respond to user acceptation.

        Import the selected card into the underlying material, including
        textures.
        """
        # Get card file path (directory)
        card = self.form.comboBox_MaterialsInDir.currentText()
        try:
            path = self.cards[card]
        except KeyError:
            path = None
        else:
            path = os.path.dirname(path)

        # Import textures (and remove texture data from self.material)
        self.material = self.obj.Proxy.import_textures(self.material, path)

        # Update material (relying on base class)
        super().accept()
        return True

    def reject(self):  # pylint: disable=no-self-use
        """Respond to user rejection."""
        return True
