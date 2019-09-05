# Material Parameters
## Usage
You can add these in the user defined section of your materials

## Definitions
### Principled shader
Source: [Disney's Principled Shader](https://disney-animation.s3.amazonaws.com/library/s2012_pbs_disney_brdf_notes_v2.pdf)

Sometimes referred to as the disney shader. The principled shader is a widely used PBR BRDF model. The parameters 
are designed for ease of use rather than using strictly physical ones. Some implementations provide extensions to this model.
#### Core
* **DiffuseColor**: surface color
* **Principled_Roughness**: surface roughness, controls both diffuse and specular response
* **Principled_Metallic**: the metallic-ness (0 = dielectric,  1 = metallic).
* **Principled_Specular**: incident specular amount.  This is in lieu of an explicit index-of-refraction
* **Principled_SpecularTint**: a concession for artistic control that tints incident specular towards the base color.Grazing specular is still achromatic
* **Principled_Anisotropic**: degree of anisotropy.  This controls the aspect ratio of the specular highlight.  (0 =isotropic, 1 = maximally anisotropic)
* **Principled_Sheen**: an additional grazing component, primarily intended for cloth.
* **Principled_SheenTint**: amount to tint sheen towards base color.
* **Principled_Clearcoat**: a second, special-purpose specular lobe.
* **Principled_ClearcoatRoughness**: controls clearcoat glossiness (0 = a “gloss” appearance, 1 = a “satin” appearance)


#### Extensions
* **Principled_SubsurfaceColor**: Subsurface scattering base color (blender)
* **Principled_Subsurface**: Mix between diffuse and subsurface scattering. 
* **Principled_IOR**: Index of refraction for transmission (blender)
* **Principled_Transmission**: Mix between fully opaque surface at zero and fully glass like transmission at one (blender)
* **Principled_TransmissionRoughness**: Controls roughness used for transmitted light.


## Glossary of Terms
* BRDF: [Bidirectional Reflectance Distribution Function](https://en.wikipedia.org/wiki/Bidirectional_reflectance_distribution_function)
* BSDF: [Bidirectional Scattering Distribution Function](https://en.wikipedia.org/wiki/Bidirectional_scattering_distribution_function)
* BTDF: [Bidirectional Transmittance Distribution Function](https://en.wikipedia.org/wiki/Bidirectional_scattering_distribution_function)
* GGX: A microfacet distribution
* IOR: Index of Refraction
* PBR: [Physically Based Rendering](https://en.wikipedia.org/wiki/Physically_based_rendering)