# ***************************************************************************
# *                                                                         *
# * Copyright Contributors to the MaterialX Project                         *
# * Copyright (c) 2024 Howefuft <howetuft-at-gmail>                         *
# *                                                                         *
# * Licensed under the Apache License, Version 2.0 (the "License");         *
# * you may not use this file except in compliance with the License.        *
# * You may obtain a copy of the License at                                 *
# *                                                                         *
# * http://www.apache.org/licenses/LICENSE-2.0                              *
# *                                                                         *
# * Unless required by applicable law or agreed to in writing, software     *
# * distributed under the License is distributed on an "AS IS" BASIS,       *
# * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.*
# * See the License for the specific language governing permissions and     *
# * limitations under the License.                                          *
# *                                                                         *
# ***************************************************************************

# This code is derived from MaterialX TextureBaker C++ implementation,
# licensed under Apache 2.0
# The original code has been found here (2024):
#
# https://github.com/AcademySoftwareFoundation/MaterialX/blob/main/
#
# and especially in these files:
# - source/MaterialXRender/TextureBaker.inl
# - source/MaterialXRender/TextureBaker.h
#
# Derivative work, under Howetuft's copyright, has mainly consisted (but may
# not be restricted) in 2 main parts:
# - Transposing from C++ to Python language
# - Adaptation to FreeCAD Render Workbench needs, in particular ability to
#   handle 'displacement' shaders as well


"""This module provides features to import MaterialX materials in Render WB."""

import hashlib
import sys
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Set
from collections.abc import Sequence

import MaterialX as mx
from MaterialX import PyMaterialXCore as mx_core
from MaterialX import PyMaterialXFormat as mx_format
from MaterialX import PyMaterialXGenShader as mx_gen_shader
from MaterialX import PyMaterialXGenGlsl as mx_gen_glsl
from MaterialX import PyMaterialXRender as mx_render
from MaterialX import PyMaterialXRenderGlsl as mx_render_glsl


class RenderTextureBaker:
    """A texture baker, capable for displacement shaders as well.

    This texture baker is based on GLSL.
    """

    # pylint: disable=too-many-instance-attributes

    SRGB_TEXTURE = "srgb_texture"
    LIN_REC709 = "lin_rec709"
    BAKED_POSTFIX = "_baked"
    SHADER_PREFIX = "SR_"
    DEFAULT_UDIM_PREFIX = "_"
    EMPTY_STRING = ""

    @dataclass
    class BakedImage:
        """A baked image descriptor."""

        filename: mx_format.FilePath
        uniform_color: mx_core.Color4 = field(default_factory=mx_core.Color4)
        is_uniform: bool = False

    @dataclass
    class BakedConstant:
        """A baked image with constant color descriptor."""

        color: mx.Color4
        is_default: bool = False

    def __init__(
        self,
        width: int,
        height: int,
        base_type: mx_render.BaseType,
        flip_saved_image: bool = False,
    ) -> None:
        # Class declarations
        self._extension = ""
        self._colorspace = ""
        self._distance_unit = ""
        self._average_images = False
        self._optimize_constants = False
        self._output_image_path: mx_format.FilePath = None
        self._baked_graph_name = ""
        self._baked_geom_info_name = ""
        self._texture_filename_template = ""
        self._output_stream = None
        self._hash_image_names = False
        self._texture_space_min = None
        self._texture_space_max = None

        self._material: mx.Node = None
        self._frame_capture_image: mx.PyMaterialXRender.Image = None
        self._baked_image_map: Dict[
            int, List[RenderTextureBaker.BakedImage]
        ] = {}
        self._baked_constant_map: Dict[
            int, RenderTextureBaker.BakedConstant
        ] = {}
        self._tex_template_overrides: Dict[str, str] = {}
        self._baked_input_map: Dict[str, str] = {}

        self._world_space_nodes: Dict[str, mx.Node] = {}

        self._flip_saved_image: bool = False

        self._write_document_per_material: bool = False
        self._baked_texture_doc: mx.Document = None

        # Constructor initializations
        self._renderer = mx_render_glsl.GlslRenderer.create(
            width, height, base_type
        )
        self._distance_unit = "meter"
        self._average_images = False
        self._optimize_constants = True
        self._baked_graph_name = "NG_baked"
        self._baked_geom_info_name = "GI_baked"
        self._texture_filename_template = (
            "$MATERIAL_"
            "$SHADINGMODEL_"
            "$INPUT"
            "$UDIMPREFIX"
            "$UDIM"
            ".$EXTENSION"
        )
        self._output_stream = sys.stdout
        self._hash_image_names = True
        self._texture_space_min = mx.Vector2(0.0)
        self._texture_space_max = mx.Vector2(1.0)
        self._generator = mx_gen_glsl.GlslShaderGenerator.create()
        self._permitted_overrides: Set[str] = {
            "$ASSET",
            "$MATERIAL",
            "$UDIMPREFIX",
        }
        self._flip_saved_image = bool(flip_saved_image)
        self._write_document_per_material = True
        self._baked_texture_doc = None

        # Specific
        self._base_type = base_type

        if base_type == mx_render.BaseType.UINT8:
            self._extension = mx_render.ImageLoader.PNG_EXTENSION
            self._colorspace = self.SRGB_TEXTURE
        else:
            self._extension = mx_render.ImageLoader.HDR_EXTENSION
            self._colorspace = self.LIN_REC709

        # Initialize our base renderer
        self._renderer.initialize()

        # Initialize our image handler
        self._renderer.setImageHandler(
            mx_render.ImageHandler.create(mx_render.StbImageLoader.create())
        )
        self._renderer.setImageHandler(
            mx_render_glsl.GLTextureHandler.create(
                mx_render.StbImageLoader.create()
            )
        )

        # Create our dedicated frame capture image
        self._frame_capture_image = mx_render.Image.create(
            width, height, 4, base_type
        )
        self._frame_capture_image.createResourceBuffer()

    # GETTERS AND SETTERS

    @property
    def extension(self) -> str:
        """Return the file extension for baked textures."""
        return self._extension

    @extension.setter
    def extension(self, value: str) -> None:
        """Set the file extension for baked textures."""
        self._extension = str(value)

    @property
    def colorspace(self) -> str:
        """Return the color space in which color textures are encoded."""
        return self._colorspace

    @colorspace.setter
    def colorspace(self, value: str) -> None:
        """Set the color space in which color textures are encoded.

        By default, this color space is srgb_texture, and color inputs are
        automatically transformed to this space by the baker.  If another color
        space is set, then the input graph is responsible for transforming
        colors to this space.
        """
        self._colorspace = str(value)

    @property
    def distance_unit(self) -> str:
        """Return the distance unit to which textures are baked."""
        return self._distance_unit

    @distance_unit.setter
    def distance_unit(self, value: str) -> None:
        """Set the distance unit to which textures are baked.

        Defaults to meters.
        """
        self._distance_unit = str(value)

    @property
    def average_images(self) -> bool:
        """Return whether images should be averaged to generate constants."""
        return self._average_images

    @average_images.setter
    def average_images(self, value: bool) -> None:
        """Set whether images should be averaged to generate constants.

        Defaults to false.
        """
        self._average_images = bool(value)

    @property
    def optimize_constants(self) -> bool:
        """Return whether uniform textures should be stored as constants."""
        return self._optimize_constants

    @optimize_constants.setter
    def optimize_constants(self, value: bool) -> None:
        """Set whether uniform textures should be stored as constants.

        Defaults to true.
        """
        self._optimize_constants = bool(value)

    @property
    def output_image_path(self) -> mx.FilePath:
        """Get the current output location for baked texture images."""
        return self._output_image_path

    @output_image_path.setter
    def output_image_path(self, value: mx.FilePath) -> None:
        """Set the output location for baked texture images.

        Defaults to the root folder of the destination material.
        """
        self._output_image_path = (
            value if isinstance(value, mx.FilePath) else mx.FilePath(value)
        )

    @property
    def baked_graph_name(self) -> str:
        """Return the name of the baked graph element."""
        return self._baked_graph_name

    @baked_graph_name.setter
    def baked_graph_name(self, value: str) -> None:
        """Set the name of the baked graph element."""
        self._baked_graph_name = str(value)

    @property
    def baked_geom_info_name(self) -> str:
        """Return the name of the baked geometry info element."""
        return self._baked_geom_info_name

    @baked_geom_info_name.setter
    def baked_geom_info_name(self, value: str) -> None:
        """Set the name of the baked geometry info element."""
        self._baked_geom_info_name = str(value)

    @property
    def texture_filename_template(self) -> str:
        """Get the texture filename template."""
        return self._texture_filename_template

    @texture_filename_template.setter
    def texture_filename_template(self, value: str) -> None:
        """Set the texture filename template."""
        value = str(value)
        self._texture_filename_template = (
            value + ".$EXTENSION" if "$EXTENSION" in value else value
        )

    def _set_filename_template_var_override(
        self, value: Sequence[str]
    ) -> None:
        """Set 'tex_filename_overrides' if template variable exists."""
        key, value, *_ = iter(value)
        if key not in self._tex_template_overrides:
            return
        self._tex_template_overrides[key] = value

    filename_template_var_override = property(
        fset=_set_filename_template_var_override
    )

    @property
    def output_stream(self):
        """Return the output stream for reporting progress and warnings."""
        return self._output_stream

    @output_stream.setter
    def output_stream(self, value) -> None:
        """Set the output stream for reporting progress and warnings.

        Defaults to sys.stdout.
        """
        try:
            write = value.write
        except AttributeError as err:
            raise TypeError(
                "'output_stream' setting error - no 'write' method."
            ) from err

        if not callable(write):
            msg = (
                "'output_stream' setting error - "
                "'write' attribute is not callable."
            )
            raise TypeError(msg)

        self._output_stream = value

    @property
    def hash_image_names(self) -> bool:
        """Return whether hashing baked image filenames is set."""
        return self._hash_image_names

    @hash_image_names.setter
    def hash_image_names(self, value: bool) -> None:
        """Set whether to create a short name for baked images by hashing.

        If set, the baked image filenames are systematically hashed.
        This is useful for file systems which may have a maximum limit on
        filename size.
        By default names are not hashed.
        """
        self._hash_image_names = bool(value)

    @property
    def texture_space_min(self) -> mx.Vector2:
        """Return the minimum texcoords used in texture baking."""
        return self._texture_space_min

    @texture_space_min.setter
    def texture_space_min(self, value) -> None:
        """Set the minimum texcoords used in texture baking.

        Defaults to 0, 0.
        """
        if not isinstance(value, mx.Vector2):
            msg = (
                "'texture_space_min' setting error - "
                f"'MaterialX.Vector2' expected, got {type(value)}"
            )
            raise TypeError(msg)
        self._texture_space_min = value

    @property
    def texture_space_max(self) -> mx.Vector2:
        """Return the maximum texcoords used in texture baking."""
        return self._texture_space_max

    @texture_space_max.setter
    def texture_space_max(self, value) -> None:
        """Set the maximum texcoords used in texture baking.

        Defaults to 1, 1.
        """
        if not isinstance(value, mx.Vector2):
            msg = (
                "'texture_space_max' setting error - "
                f"'MaterialX.Vector2' expected, got {type(value)}"
            )
            raise TypeError(msg)
        self._texture_space_max = value

    # PRIVATE METHODS

    def _get_value_string_from_color(
        self, color: mx.Color4, type_: str
    ) -> str:
        """Get a string from a color, depending on a target type."""
        color0, color1, color2, _ = color.asTuple()
        if type_ in ["color4", "vector4"]:
            return str(color)
        if type_ in ["color3", "vector3"]:
            return str(mx.Vector3(color0, color1, color2))
        if type_ == "vector2":
            return str(mx.Vector2(color0, color1))
        if type_ == "float":
            return str(color0)
        return self.EMPTY_STRING

    @staticmethod
    def _find_var_in_template(filename: str, var: str, start: int) -> int:
        """Find variable in template file."""
        res = filename.find(var, start)
        if var == "$UDIM" and res != -1:
            udim_prefix = filename.find("$UDIMPREFIX", start)
            if res == udim_prefix:
                res = filename.find(var, res + 1)
        return res

    def _generate_texture_filename(
        self, filename_template_map: Dict[str, str]
    ) -> mx.FilePath:
        """Generate filename for texture."""
        baked_image_name = self._texture_filename_template

        for key, value in filename_template_map.items():
            replacement = (
                self._tex_template_overrides[key]
                if key in self._tex_template_overrides
                else value
            )
            replacement = (
                self.EMPTY_STRING
                if not filename_template_map["$UDIM"] and key == "$UDIMPREFIX"
                else replacement
            )
            i = 0
            while (
                i := self._find_var_in_template(baked_image_name, key, i)
            ) != -1:
                baked_image_name = "".join(
                    [
                        baked_image_name[0:i],
                        replacement[0 : len(key)],
                        baked_image_name[i + len(key) :],
                    ]
                )
                i += 1

            if self._hash_image_names:
                hashed_image_name = hashlib.sha1(
                    baked_image_name.encode("utf-8")
                ).hexdigest()
                baked_image_name = f"{hashed_image_name}.{self._extension}"

        return self._output_image_path / baked_image_name

    def _initialize_file_template_map(
        self, input_: mx.Input, shader: mx.Node, udim: str
    ):
        """Initialize a file template for exporting."""
        # source/MaterialXRender/TextureBaker.inl#L142
        asset_path = mx_format.FilePath(shader.getActiveSourceUri())
        asset_path.removeExtension()
        filename_template_map = {}
        filename_template_map["$ASSET"] = asset_path.getBaseName()
        filename_template_map["$INPUT"] = self._baked_input_map[
            input_.getName()
        ]
        filename_template_map["$EXTENSION"] = self._extension
        filename_template_map["$MATERIAL"] = self._material.getName()
        filename_template_map["$SHADINGMODEL"] = shader.getCategory()
        filename_template_map["$UDIM"] = udim
        filename_template_map["$UDIMPREFIX"] = self.DEFAULT_UDIM_PREFIX
        return filename_template_map

    def _write_baked_image(
        self, baked: BakedImage, image: mx_render.Image
    ) -> bool:
        """Write baked image to disk."""
        filename = baked.filename.asString()

        if not self._renderer.getImageHandler().saveImage(
            baked.filename, image, self._flip_saved_image
        ):
            if self._output_stream:
                print(
                    f"Failed to write baked image: {filename}",
                    file=self._output_stream,
                )
            return False

        if self._output_stream:
            print(
                f"Wrote baked image: {filename}",
                file=self._output_stream,
            )
        return True

    def _bake_shader_inputs(
        self,
        material: mx.Node,
        shader: mx.Node,
        context: mx_gen_shader.GenContext,
        udim: str,
    ) -> None:
        """Bake shader inputs."""
        # source/MaterialXRender/TextureBaker.inl
        self._material = material

        if not shader:
            return

        baked_outputs = {}
        for input_ in shader.getInputs():
            output = input_.getConnectedOutput()
            if output and output.getNamePath() not in baked_outputs:
                baked_outputs[output.getNamePath()] = input_
                self._baked_input_map[input_.getName()] = input_.getName()

                # When possible, nodes with world-space outputs are applied
                # outside of the baking process.
                world_space_node = mx_gen_shader.connectsToWorldSpaceNode(
                    output
                )
                if world_space_node:
                    output.setConnectedNode(
                        world_space_node.getConnectedNode("in")
                    )
                    self._world_space_nodes[input_.getName()] = (
                        world_space_node
                    )

                filename_template_map = self._initialize_file_template_map(
                    input_, shader, udim
                )
                self._bake_graph_output(output, context, filename_template_map)

            elif output.getNamePath() in baked_outputs:
                # When the input shares the same output as a previously baked
                # input, we use the already baked input.
                self._baked_input_map[input_.getName()] = baked_outputs[
                    output.getNamePath()
                ].getName()

    def _bake_graph_output(
        self,
        output: mx.Output,
        context: mx_gen_shader.GenContext,
        filename_template_map: Dict[str, str],
    ) -> None:
        """Bake the graph of an output node."""
        if not output:
            return

        # WARNING: not translatable into Python
        # encode_srgb = bool(
        # self._colorspace == self.SRGB_TEXTURE
        # and (output.getType() in ["color3", "color4"])
        # )
        # self._renderer.getFrameBuffer.setEncodeSrgb(encode_srgb)
        shader = self._generator.generate("BakingShader", output, context)
        self._renderer.createProgram(shader)

        # Render and capture the requested image
        self._renderer.renderTextureSpace(
            self._texture_space_min, self._texture_space_max
        )
        texturefilepath = self._generate_texture_filename(
            filename_template_map
        )
        self._frame_capture_image = self._renderer.captureImage(
            self._frame_capture_image
        )

        # Construct a baked image record
        baked = self.BakedImage(filename=texturefilepath)
        if self._average_images:
            baked.uniform_color = self._frame_capture_image.getAverageColor()
            baked.is_uniform = True
        elif self._frame_capture_image.isUniformColor(baked.uniform_color):
            baked.is_uniform = True
        try:
            self._baked_image_map[output.getNamePath()].append(baked)
        except KeyError:
            self._baked_image_map[output.getNamePath()] = [baked]

        # Enhancement: Write images to memory rather than to disk.
        # Write non-uniform images to disk.
        if not baked.is_uniform:
            self._write_baked_image(baked, self._frame_capture_image)

    def _optimize_baked_textures(self, shader: mx_core.Node) -> None:
        """Optimize baked textures collection."""
        if not shader:
            return

        # Check for fully uniform outputs
        for first, second in self._baked_image_map.items():
            output_is_uniform = True
            for baked in second:
                if (
                    not baked.is_uniform
                    or baked.uniform_color != second[0].uniform_color
                ):
                    output_is_uniform = False
                    continue
                if output_is_uniform:
                    baked_constant = self.BakedConstant(
                        color=second[0].uniform_color
                    )
                    self._baked_constant_map[first] = baked_constant

        # Check for uniform outputs at their default values
        if shader_node_def := shader.getNodeDef():
            for shader_input in shader.getInputs():
                output = shader_input.getConnectedOutput()
                if output.getNamePath() in self._baked_constant_map:
                    input_ = shader_node_def.getInput(shader_input.getName())
                    if input_:
                        uniform_color = self._baked_constant_map[
                            output.getNamePath()
                        ].color
                        uniform_color_string = (
                            self._get_value_string_from_color(
                                uniform_color, input_.getType()
                            )
                        )
                        default_value_string = (
                            input_.getValueString()
                            if input_.hasValueString()
                            else self.EMPTY_STRING
                        )
                        if uniform_color_string == default_value_string:
                            self._baked_constant_map[
                                output.getNamePath()
                            ].is_default = True

        # Remove baked images that have been replaced by constant values
        for first2, second2 in self._baked_constant_map.items():
            if (
                second2.is_default
                or self._optimize_constants
                or self._average_images
            ):
                del self._baked_image_map[first2]

    def _generate_new_document_from_shader(
        self, shader: mx_core.Node, udim_set: List[str]
    ) -> mx.Document:
        """Generate a new document from a given shader."""
        # pylint: disable=too-many-locals
        if not shader:
            return None

        # Create document
        if not self._baked_texture_doc or self._write_document_per_material:
            self._baked_texture_doc = mx.createDocument()
        if shader.getDocument().hasColorSpace():
            self._baked_texture_doc.setColorSpace(
                shader.getDocument().getColorSpace()
            )

        # Create node graph and geometry info
        if self._baked_image_map:
            self._baked_graph_name = (
                self._baked_texture_doc.createValidChildName(
                    self._baked_graph_name
                )
            )
            baked_node_graph = self._baked_texture_doc.addNodeGraph(
                self._baked_graph_name
            )
            baked_node_graph.setColorSpace(self._colorspace)

        self._baked_geom_info_name = (
            self._baked_texture_doc.createValidChildName(
                self._baked_geom_info_name
            )
        )
        baked_geom = (
            self._baked_texture_doc.addGeomInfo(self._baked_geom_info_name)
            if udim_set
            else None
        )
        if baked_geom:
            baked_geom.setGeomPropValue(
                mx.UDIM_SET_PROPERTY, udim_set, "stringarray"
            )

        # Create a shader node
        baked_shader = self._baked_texture_doc.addNode(
            shader.getCategory(),
            shader.getName() + self.BAKED_POSTFIX,
            shader.getType(),
        )

        # Optionally create a material node, connecting it to the new shader
        # node
        if self._material:
            try:
                material_name = self._tex_template_overrides["$MATERIAL"]
            except KeyError:
                material_name = self._material.getName()
            baked_material = self._baked_texture_doc.addNode(
                self._material.getCategory(),
                material_name + self.BAKED_POSTFIX,
                self._material.getType(),
            )
            for source_material_input in self._material.getInputs():
                source_material_input_name = source_material_input.getName()
                upstream_shader = source_material_input.getConnectedNode()
                if (
                    upstream_shader
                    and upstream_shader.getNamePath() == shader.getNamePath()
                ):
                    baked_material_input = baked_material.getInput(
                        source_material_input_name
                    )
                    if not baked_material_input:
                        baked_material_input = baked_material.addInput(
                            source_material_input_name,
                            source_material_input.getType(),
                        )
                    baked_material_input.setNodeName(baked_shader.getName())

        # Create and connect inputs on the new shader node
        value_elements = (
            v for v in shader.getChildren() if v.isA(mx.ValueElement)
        )
        for value_elem in value_elements:
            # Get the source input and its connected output
            source_input = value_elem

            output = source_input.getConnectedOutput()

            # Skip uniform outputs at their default values
            if (
                output
                and output.getNamePath() in self._baked_constant_map
                and self._baked_constant_map[output.getNamePath()].is_default
            ):
                continue

            # Find or create the baked input.
            source_name = source_input.getName()
            source_type = source_input.getType()
            if not (baked_input := baked_shader.getInput(source_name)):
                baked_input = baked_shader.addInput(source_name, source_type)

            # Assign image or constant data to the baked input
            if output:
                # Store a constant value for uniform outputs
                if (
                    self._optimize_constants
                    and output.getNamePath() in self._baked_constant_map
                ):
                    uniform_color = self._baked_constant_map[
                        output.getNamePath()
                    ].color
                    uniform_color_string = self._get_value_string_from_color(
                        uniform_color, baked_input.getType()
                    )
                    baked_input.setValueString(uniform_color_string)
                    if baked_input.getType() in ["color3", "color4"]:
                        baked_input.setColorSpace(self._colorspace)
                    continue

                if self._baked_image_map:
                    # Add the image node
                    baked_image = baked_node_graph.addNode(
                        "image",
                        source_name + self.BAKED_POSTFIX,
                        source_type,
                    )
                    input_ = baked_image.addInput("file", "filename")
                    filename_template_map = self._initialize_file_template_map(
                        baked_input,
                        shader,
                        self.EMPTY_STRING if not udim_set else mx.UDIM_TOKEN,
                    )
                    input_.setValueString(
                        self._generate_texture_filename(
                            filename_template_map
                        ).asString()
                    )

                    # Reconstruct any world-space nodes that were excluded
                    # from the baking process
                    try:
                        orig_world_space_node = self._world_space_nodes[
                            source_input.getName()
                        ]
                    except KeyError:
                        pass
                    else:
                        if orig_world_space_node:
                            new_world_space_node = baked_node_graph.addNode(
                                orig_world_space_node.getCategory,
                                source_name + self.BAKED_POSTFIX + "_map",
                                source_type,
                            )
                        new_world_space_node.copyContentFrom(
                            orig_world_space_node
                        )
                        if map_input := new_world_space_node.getInput("in"):
                            map_input.setNodeName(baked_image.getName())
                        baked_image = new_world_space_node

                    # Add the graph output
                    baked_output = baked_node_graph.addOutput(
                        source_name + "_output", source_type
                    )
                    baked_output.setConnectedNode(baked_image)
                    baked_input.setConnectedOutput(baked_output)
            else:  # if output
                baked_input.copyContentFrom(source_input)

        # Generate uniform images and write to disk
        uniform_image = mx_render.createUniformImage(
            4, 4, 4, self._base_type, mx.Color4()
        )
        for value in self._baked_image_map.values():
            for baked in value:
                if baked.is_uniform:
                    uniform_image.setUniformColor(baked.uniform_color)
                    self._write_baked_image(baked, uniform_image)

        # Clear cached information after each material bake
        self._baked_image_map.clear()
        self._baked_constant_map.clear()
        self._world_space_nodes.clear()
        self._baked_input_map.clear()
        self._material = None

        return self._baked_texture_doc

    # PUBLIC METHODS (API)

    def bake_material_to_doc(
        self,
        doc: mx.Document,
        search_path: mx.FileSearchPath,
        material_path: str,
        udim_set: List[str],
    ) -> Tuple[mx.Document, str]:
        """Bake a material node to a document.

        Unlike the C++ model, this function can bake displacement nodes.
        """
        # source/MaterialXRender/TextureBaker.inl#L485

        if self._output_stream:
            print(
                f"Processing material: {material_path}",
                file=self._output_stream,
            )

        # Set up generator context for material
        context = mx_gen_shader.GenContext(self._generator)
        context.getOptions().targetColorSpaceOverride = self.LIN_REC709
        context.getOptions().fileTextureVerticalFlip = True
        context.getOptions().targetDistanceUnit = self._distance_unit
        context.getOptions().shaderInterfaceType = (
            mx_gen_shader.ShaderInterfaceType.SHADER_INTERFACE_COMPLETE
        )

        # If we're generating Vulkan-compliant GLSL then set the binding
        # context (generateshader.py)
        if isinstance(self._generator, mx_gen_glsl.VkShaderGenerator):
            binding_context = mx_gen_glsl.GlslResourceBindingContext.create(
                0, 0
            )
            context.pushUserData("udbinding", binding_context)

        # Color management
        cms = mx_gen_shader.DefaultColorManagementSystem.create(
            self._generator.getTarget()
        )
        cms.loadLibrary(doc)
        context.registerSourceCodeSearchPath(search_path)
        self._generator.setColorManagementSystem(cms)

        # Compute the material tag set
        if not (material_tags := udim_set.copy()):
            material_tags.append(self.EMPTY_STRING)

        elem = doc.getDescendant(material_path)
        if not elem or not elem.isA(mx.Node):
            return None, ""
        material_node = elem

        # TODO Process all shader nodes
        shader_nodes = mx.getShaderNodes(material_node)
        if not (shader_node := shader_nodes[0] if shader_nodes else None):
            return None, ""

        resolver = doc.createStringResolver()

        # Iterate over material tags
        for tag in material_tags:
            # Always clear any cached implementations before generation
            # WARNING: Not available in Python
            # context.clearNodeImplementations()

            hw_shader = self._generator.generate(
                "Shader", shader_node, context
            )
            if not hw_shader:
                continue
            self._renderer.getImageHandler().setSearchPath(search_path)
            resolver.setUdimString(tag)
            self._renderer.getImageHandler().setFilenameResolver(resolver)
            self._bake_shader_inputs(material_node, shader_node, context, tag)

            self._optimize_baked_textures(shader_node)

        return (
            self._generate_new_document_from_shader(shader_node, udim_set),
            shader_node.getName(),
        )

    def bake_all_materials(
        self,
        doc: mx.Document,
        search_path: mx.FileSearchPath,
        output_filename: mx_format.FilePath,
    ):
        """Bake all materials of a given document."""
        if isinstance(search_path, str):
            search_path = mx.FileSearchPath(search_path)

        if isinstance(output_filename, str):
            output_filename = mx_format.FilePath(output_filename)

        if not self._output_image_path:
            self._output_image_path = output_filename.getParentPath()
            if not self._output_image_path.exists():
                self._output_image_path.createDirectory()

        renderable_materials = mx_gen_shader.findRenderableElements(doc)

        # Compute the UDIM set
        udim_set_value = doc.getGeomPropValue(mx.UDIM_SET_PROPERTY)

        udim_set = []
        if udim_set_value:
            udim_set = [udim_set_value]

        # Bake all materials in documents to memory
        baked_documents = []
        for element in renderable_materials:
            baked_material_doc, document_name = self.bake_material_to_doc(
                doc,
                search_path,
                element.getNamePath(),
                udim_set,
            )
            if self._write_document_per_material and baked_material_doc:
                baked_documents.append((document_name, baked_material_doc))

        if self._write_document_per_material:
            # Write document in memory to disk
            for document_name, baked_material_doc in baked_documents:
                if baked_material_doc:
                    write_filename = output_filename

                # Add additional filename decorations if there are multiple
                # documents
                if len(baked_documents) > 1:
                    extension = write_filename.getExtension()
                    write_filename.removeExtension()
                    filename_separator = (
                        self.EMPTY_STRING
                        if write_filename.isDirectory()
                        else "_"
                    )
                    write_filename = mx_format.FilePath(
                        write_filename.asString()
                        + filename_separator
                        + document_name
                        + "."
                        + extension
                    )

                mx.writeToXmlFile(baked_material_doc, write_filename)
                if self._output_stream:
                    print(
                        f"Wrote baked document: {write_filename.asString()}",
                        file=self._output_stream,
                    )
        elif self._baked_texture_doc:
            mx.writeToXmlFile(self._baked_texture_doc, output_filename)
            if self._output_stream:
                print(
                    f"Wrote baked document: {output_filename.asString()}",
                    file=self._output_stream,
                )

    def setup_unit_system(self, unit_definitions: mx.Document) -> None:
        """Set up baker unit system."""
        distance_type_def = (
            unit_definitions.getUnitTypeDef("distance")
            if unit_definitions
            else None
        )
        angle_type_def = (
            unit_definitions.getUnitTypeDef("angle")
            if unit_definitions
            else None
        )
        if not distance_type_def and not angle_type_def:
            return

        unit_system = mx_gen_shader.UnitSystem.create(
            self._generator.getTarget()
        )
        if not unit_system:
            return
        self._generator.setUnitSystem(unit_system)
        registry = mx.UnitConverterRegistry.create()
        registry.addUnitConverter(
            distance_type_def, mx.LinearUnitConverter.create(distance_type_def)
        )
        registry.addUnitConverter(
            angle_type_def, mx.LinearUnitConverter.create(angle_type_def)
        )
        self._generator.getUnitSystem().loadLibrary(unit_definitions)
        self._generator.getUnitSystem().setUnitConverterRegistry(registry)
