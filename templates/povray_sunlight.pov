    // Persistence of Vision Ray Tracer Scene Description File
    // for FreeCAD (http://www.freecadweb.org)

    #version 3.6;

    #include "colors.inc"
    #include "metals.inc"
    #include "rad_def.inc"

    global_settings {
        radiosity {
            Rad_Settings(Radiosity_Normal,off,off)
        }
        assumed_gamma 1
        subsurface {}
    }

    #default {finish{ambient 0}}

    // Sky
    sky_sphere{
        pigment{ gradient y
           color_map{
               [0.0 color rgb<1,1,1> ]
               [0.8 color rgb<0.18,0.28,0.75>]
               [1.0 color rgb<0.75,0.75,0.75>]}
               //[1.0 color rgb<0.15,0.28,0.75>]}
               scale 2
               translate -1
        } // end pigment
    } // end sky_sphere

    // Sun
    global_settings { ambient_light rgb<1, 1, 1> }
    light_source {
        <85525370374085.5,119995516108223.16,-32977069856138.77>
        color rgb <1,1,1>
        parallel
        point_at <0,0,0>
        adaptive 1
    }


    // Standard finish
    #declare StdFinish = finish { crand 0.01 diffuse 0.8 };

    //RaytracingContent

