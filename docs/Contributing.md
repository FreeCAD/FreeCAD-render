# Contributing

Any contributions are welcome, feel free to post pull requests to this project!

Beforehand, you may find below some useful information to make your code more
easily accepted.

## Code Quality

In order to make this module easy to read, maintain and extend by everyone, we
strive to sustain a good level of code quality. In particular, we try to
ensure that the code complies with
[PEP8](https://www.python.org/dev/peps/pep-0008/) and
[PEP257](https://www.python.org/dev/peps/pep-0257/). Therefore,
* If you post contributions (thank you very much!), please enforce PEP8 /
  PEP257 on your production, and **run [pylint](www.pylint.org),
  [flake8](flake8.pycqa.org) and [pydocstyle](www.pydocstyle.org)** on your
  code before sending your PR. A specific pylintrc file, with general PEP8
  rules and some specific tweaks related to FreeCAD framework, is provided for
  that purpose in the project directory.
* If you see anything that could be improved in terms of code quality (PEP
  compliance, pythonicity, coding best practices...), or simply readability
  (comments, documentation...), do not hesitate to post propositions!

## Writing a new renderer plugin

You may find [here](../renderers/README.md) some useful guidelines to write a
new renderer plugin.

## Translating
Render Workbench is translated following the [general
guidelines](https://wiki.freecadweb.org/Translating_an_external_workbench)
provided by FreeCAD documentation.
Please note we do not translate:
* Debug messages (calls to debug()), as they are supposed to be hidden in
  normal functioning.
* Assert messages, as they are supposed not to appear in normal functioning,
  and to be reported as is to developers if they occur.

## To Do (not exhaustive)

* Add some more lighting functionalities:
  - Spot lights
  - Directional lights
* Add UV-textures to material support
* Currently the external (open the file to be rendered in the Renderer's
  GUI)/internal (render directly inside FreeCAD) render mode is not
  implemented, the external mode will always be used.
* Add support for more renderers:
  - Yafaray
  - OpenCasCade's [CadRays](https://www.opencascade.com/content/cadrays) 
  - Kerkythea (adapt the existing macro)
  - Blender's Eevee
