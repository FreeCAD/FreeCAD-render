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

sky_sphere {
    pigment {
        gradient y
        color_map {
            [0.0  color LightGray]
            [0.3  color White]
            [0.7  color LightGray]
        }
    }
}

// Standard finish
#declare StdFinish = finish {};

//RaytracingCamera
//RaytracingContent
