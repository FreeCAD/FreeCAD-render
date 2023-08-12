// Persistence of Vision Ray Tracer Scene Description File
// for FreeCAD (http://www.freecadweb.org)

#version 3.6;

#include "colors.inc"
#include "metals.inc"
#include "rad_def.inc"

global_settings {
    radiosity {
        Rad_Settings(Radiosity_OutdoorHQ,off,off)
    }
    assumed_gamma 1.0
    subsurface {}
}

#default {finish{ambient 0}}


// Standard finish
#declare StdFinish = finish {};

//RaytracingCamera
//RaytracingContent

