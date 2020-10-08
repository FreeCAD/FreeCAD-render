# Cameras

A camera allows to define a specific point of view for a rendering. It defines
which portion of a scene is visible in the rendered image.

# Zero, one or more cameras

The rendering process in the external renderer will always need one (and
only one) camera as an input: the active camera. That being said:

Cameras are optional in FreeCAD rendering projects. Indeed, if no camera is
defined in a project, the current point of view in FreeCAD viewport will be
used instead to create a virtual camera on-the-fly and export it to the
renderer.

More than one camera can also be added into a project. In this case, all the
cameras will be exported to the renderer, which will retain one (usually the
last one) as active camera.

Please note that `Visibility` matters also: only visible cameras (meaning their
`Visibility` parameters are `True`) will be exported to the renderer.

Tip: if you want to make various renderings of a scene from different points of
views (left view, right view etc.), you can create the corresponding cameras,
add them all to your project, and then play on `Visibility` parameters, keeping
only one camera visible at a time, to get each of the renderings.


# How to create a camera

The general method to add a camera to your rendering project is the following: 
1. Create the camera object: press <img src=../icons/Camera-photo.svg height=32>
2. If necessary, tweak the camera's position and orientation in your scene
3. **Add a view of the camera in your project**. This is a mandatory step to
   have the camera eventually exported! Use <img src=../icons/RenderView.svg
   height=32> button, like for objects...

Please note that the camera will be created using the current point of view in
FreeCAD viewport (i.e. the current internal Coin camera). Thus painful
reorientation/repositioning effort can be avoided by carefully positioning your
point of view in viewport before creating your camera. You may also prefer to set view to 
perspective in the viewport, which will usually be closer to final
rendering. 

The camera will be represented in viewport by the following symbol:

<img src=./camera.jpg>


# Parameters

Render Camera records the internal camera parameters used in FreeCAD
viewport.  This viewport relies on
[Pivy/Coin](https://wiki.freecadweb.org/Pivy), a 3D-rendering library
implementing the [Open
Inventor](https://web.archive.org/web/20041120092542/http://oss.sgi.com/projects/inventor/)
standard.  This is why we refer you to [Open
Inventor](https://developer.openinventor.com/UserGuides/Oiv9/Inventor_Mentor/Cameras_and_Lights/Cameras.html)
and [Coin](https://grey.colorado.edu/coin3d/classSoCamera.html#pub-attribs)
camera documentations for more details about Render Camera parameters.

# Context menu

You will find, in Camera context menu, a few features to help positioning and
orienting a Camera:
* `Set GUI to this camera`: resets the GUI camera (the camera from which the
  scene is seen in FreeCAD viewport) to the selected Camera.
* `Set this camera to GUI`: sets the selected Camera to the GUI camera.
* `Point at...`: allows to orient the camera so that it looks at a specific
  object. Trigger this action, click on the target object in the viewport, and
  the camera will be automatically oriented towards the selected object.

You can access the context menu by right-clicking on the Camera in the tree
view.
