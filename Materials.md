# Material Parameters
## Usage
You can add these in the user defined section of your materials

## Renderer Definitions
name | type | description
-----|------|------------
**Appleseed_Material** | string | (lambertian, principled, glass) 
**LuxCore_Material** | string | (metal2, roughglass, glossy2, glass)

## Shader Definitions
### Blender

#### Principled shader
Source: [Disney's Principled Shader](https://disney-animation.s3.amazonaws.com/library/s2012_pbs_disney_brdf_notes_v2.pdf)

Sometimes referred to as the disney shader. The principled shader is a widely used PBR BRDF model. The parameters 
are designed for ease of use rather than using strictly physical ones. Some implementations provide extensions to this model.

#### Core
 name | type | description
------|------|------------
**DiffuseColor** | Color| surface color
**Principled_Roughness** | float | surface roughness, controls both diffuse and specular response
**Principled_Metallic** | float | the metallic-ness (0 = dielectric,  1 = metallic).
**Principled_Specular** | float| incident specular amount.  This is in lieu of an explicit index-of-refraction
**Principled_SpecularTint** |float| a concession for artistic control that tints incident specular towards the base color.Grazing specular is still achromatic
**Principled_Anisotropic** |float | Degree of anisotropy.  This controls the aspect ratio of the specular highlight.  (0 =isotropic, 1 = maximally anisotropic)
**Principled_Sheen** | float| an additional grazing component, primarily intended for cloth.
**Principled_SheenTint** | float| amount to tint sheen towards base color.
**Principled_Clearcoat** | float| a second, special-purpose specular lobe.
**Principled_ClearcoatRoughness** | float| controls clearcoat glossiness (0 = a "gloss" appearance, 1 = a "satin" appearance)
**Principled_Subsurface** | float | Mix between diffuse and subsurface scattering. 
**Principled_SubsurfaceColor** | color | Subsurface scattering base color (blender)
**Principled_IOR** | float | Index of refraction for transmission (blender)
**Principled_Transmission** | float | Mix between fully opaque surface at zero and fully glass like transmission at one (blender)
**Principled_TransmissionRoughness** | float | Controls roughness used for transmitted light. (blender)

### Appleseed
Most material parameters can also be used with a texture. To use this take the base parameter name and
append "_Texture". The argument should be the path to the texture. For example DiffuseColor becomes DiffuseColor_Texture

#### Appleseed Disney
See principled shader

 name | type | description
------|------|------------
**DiffuseColor** | Color, texture| surface color
**Principled_Roughness** | float, texture | surface roughness, controls both diffuse and specular response
**Principled_Metallic** | float, texture | the metallic-ness (0 = dielectric,  1 = metallic).
**Principled_Specular** | float, texture| incident specular amount.  This is in lieu of an explicit index-of-refraction
**Principled_SpecularTint** |float, texture| a concession for artistic control that tints incident specular towards the base color.Grazing specular is still achromatic
**Principled_Anisotropic** |float, texture | Degree of anisotropy.  This controls the aspect ratio of the specular highlight.  (0 =isotropic, 1 = maximally anisotropic)
**Principled_Sheen** | float, texture| an additional grazing component, primarily intended for cloth.
**Principled_SheenTint** | float, texture| amount to tint sheen towards base color.
**Principled_Clearcoat** | float, texture| a second, special-purpose specular lobe.
**Principled_ClearcoatRoughness** | float, texture| controls clearcoat glossiness (0 = a "gloss" appearance, 1 = a "satin" appearance)
**Principled_Subsurface** | float, texture | Mix between diffuse and subsurface scattering.

#### Appleseed Glass
 name | type |description
------|------|------------
**Appleseed_Glass_SurfaceTransmittance** | color, texture | The color that is transmitted to the underlying glass medium. A color of 0 will mean no transmittance will take place, a color of one will mean full transmittance.
**Appleseed_Glass_ReflectionTint** | color, texture | Overall tint for the reflection (BRDF) component of the glass BSDF.
**Appleseed_Glass_RefractionTint** | color,texture | Overall tint for the refraction (BTDF) component of the glass BSDF.
**Appleseed_Glass_IOR** | float | Absolute index of refraction
**Appleseed_Glass_Roughness** | float,texture | The apparent surface roughness, affecting both the reflection and refraction equally.
**Appleseed_Glass_Anisotropy** | float,texture | Overall intensity of the anisotropy effect, with a value of 0.0 representing isotropic specular highlights.
**Appleseed_Glass_VolumeParameterization** | string, texture | (absorption, transmittance) Transmittance is usually more intuitive to use. transmittance: Calculate absorption from `VolumeTransmittance` and `VolumeTransmittanceDistance` Absorption: Use `VolumeDensity` `VolumeScale` and `VolumeAbsorption` (Beer-Lambert law)
**Appleseed_Glass_VolumeTransmittance** | color, texture | Color of the volumetric transmittance as the refracted ray travels within the medium.
**Appleseed_Glass_VolumeTransmittanceDistance** | float, texture | The distance at which full absorption is supposed to occur. When this distance is set to 0, no absorption takes place. Lower values imply a stronger absorption, and higher values imply a weaker absorption effect as the ray would need to travel a greater distance for full absorption to take place.
**Appleseed_Glass_VolumeAbsorption** | color, texture | Color of the volumetric absorption as the refracted ray travels within the medium.
**Appleseed_Glass_VolumeDensity** | float | Concentration of the attenuating species
**Appleseed_Glass_VolumeScale** | float | Extra scaling factor for `VolumeDensity`
**Appleseed_Glass_EnergyCompensation** | float | This is a way to compensate for energy losses caused by microfacet models

### LuxCore

#### LuxCore Metal2
 name | type | description
------|------|------------
**LuxCore_Metal2_FresnelColor** | color| reflection color 
**LuxCore_Metal2_URoughness** | float | roughness value along u coordinate of the material (note: texture coordinates aren't exported yet, use the same value for u & v roughness)
**LuxCore_Metal2_VRoughness** | float | roughness value along u coordinate of the material 

#### LuxCore Glass
name | type | description
-----|------|------------
**LuxCore_Glass_Reflectance** | float | reflectance of the material
**LuxCore_Glass_Transmittance** | float | transmittance of the material
**LuxCore_Glass_InteriorIOR** | float | index of refraction inside the material
**LuxCore_Glass_ExteriorIOR** | float | index of refraction outside the material
**LuxCore_Glass_Dispersion** | float | if defined and > 0.0, enable dispersion. The value is the C term of the [Cauchy's equation](https://en.wikipedia.org/wiki/Cauchy%27s_equation)

#### LuxCore Rough Glass
name | type | description
-----|------|------------
**LuxCore_RoughGlass_ReflectedColor** | color | reflected color of the material
**LuxCore_RoughGlass_TransmittedColor** | color | transmitted color of the material
**LuxCore_RoughGlass_InteriorIOR** | float | index of refraction inside the material
**LuxCore_RoughGlass_ExteriorIOR** | float | index of refraction outside the material
**LuxCore_RoughGlass_URoughness** | float | roughness value along u coordinate of the material (texture coordinates currently not supported use the same value for u & v roughness)
**LuxCore_RoughGlass_VRoughness** | float | roughness value along v coordinate of the material

#### LuxCore Glossy2
name | type | description
-----|------|------------
**LuxCore_Glossy2_Diffuse** | color | diffuse color of the material
**LuxCore_Glossy2_Specular** | color | specular color of the material
**LuxCore_Glossy2_CoatingAbsorption** | color | coefficient of absorption of the coating layer
**LuxCore_Glossy2_CoatingIOR** | float | IOR of the coating. IOR overrides specular color if both are specified; specular will turn gray.
**LuxCore_Glossy2_CoatingDepth** | float | value of the depth (thickness) of the coating layer for absorption effects. (0 = disables) 
**LuxCore_Glossy2_URoughness** | float | roughness value along u coordinate of the material (texture coordinates currently not supported use the same value for u & v roughness)
**LuxCore_Glossy2_VRoughness** | float | roughness value along v coordinate of the material
**LuxCore_Glossy2_Multibounce** | bool | (true, false) The option will simulate light being scattered at the surface by things such as fuzz or fine hair. It is useful when using glossy for a skin or cloth material, and will give a soft, fuzzy appearance. 
 

## Glossary of Terms
* Beer-Lambert law: [Beer-Lambert law](https://en.wikipedia.org/wiki/Beer%E2%80%93Lambert_law)
* BRDF: [Bidirectional Reflectance Distribution Function](https://en.wikipedia.org/wiki/Bidirectional_reflectance_distribution_function)
* BSDF: [Bidirectional Scattering Distribution Function](https://en.wikipedia.org/wiki/Bidirectional_scattering_distribution_function)
* BTDF: [Bidirectional Transmittance Distribution Function](https://en.wikipedia.org/wiki/Bidirectional_scattering_distribution_function)
* GGX: A microfacet distribution
* IOR: Index of Refraction
* Microfacet: Microfacet models assume the surface consists of a large number of small flat “micromirrors” (facets) each of which reflect light only in the specular direction
* PBR: [Physically Based Rendering](https://en.wikipedia.org/wiki/Physically_based_rendering)