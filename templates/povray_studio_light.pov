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
            [0.0  color rgb <0.3, 0.3, 0.3>]
            [0.3  color rgb <0.3, 0.3, 0.3>]
            [0.7  color rgb <0.3, 0.3, 0.3>]
        }
    }
}
light_source {
    <+1e9,+1.5e9,-1e9>
    color rgb <0.1,0.1,0.1>
    parallel
    point_at <0,0,0>
    adaptive 1
}
light_source {
    <-1e9,+0.5e9,-1e9>
    color rgb <0.1,0.1,0.1> shadowless
    parallel
    point_at <0,0,0>
    adaptive 1
}
light_source {
    <0e9,0e9,+1e9>
    color rgb <0.1,0.1,0.1> shadowless
    parallel
    point_at <0,0,0>
    adaptive 1
}
// Standard finish
#declare StdFinish = finish {};

//RaytracingCamera
//RaytracingContent

