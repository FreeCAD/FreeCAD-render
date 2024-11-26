<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="pl" sourcelanguage="en_US">
<context>
    <name>App::Property</name>
    <message>
        <location filename="../../camera.py" line="91"/>
        <source>Type of projection: Perspective/Orthographic</source>
        <translation>Typ projekcji: Perspektywa/Ortogonalna</translation>
    </message>
    <message>
        <location filename="../../camera.py" line="97"/>
        <source>(See Coin documentation)</source>
        <translation>(Patrz dokumentacja Coin)</translation>
    </message>
    <message>
        <location filename="../../camera.py" line="105"/>
        <source>Ratio width/height of the camera.</source>
        <translation>Stosunek szerokości do wysokości ujęcia widoku.</translation>
    </message>
    <message>
        <location filename="../../camera.py" line="111"/>
        <source>Near distance, for clipping</source>
        <translation>Niewielka odległość, w celu przycięcia</translation>
    </message>
    <message>
        <location filename="../../camera.py" line="117"/>
        <source>Far distance, for clipping</source>
        <translation>Duża odległość, w celu przycięcia</translation>
    </message>
    <message>
        <location filename="../../camera.py" line="123"/>
        <source>Focal distance</source>
        <translation>Odległość ogniskowania</translation>
    </message>
    <message>
        <location filename="../../camera.py" line="131"/>
        <source>Height, for orthographic camera</source>
        <translation>Wysokość, do aparatu z widokiem ortogonalnym</translation>
    </message>
    <message>
        <location filename="../../camera.py" line="143"/>
        <source>Height angle, for perspective camera, in degrees. Important: This value will be sent as &apos;Field of View&apos; to the renderers. Please note it is a *vertical* field-of-view.</source>
        <translation>Kąt wysokości dla kamery perspektywicznej, w stopniach.
Ważne: Ta wartość zostanie wysłana jako &quot;Pole widzenia&quot; do programów renderujących.
Należy pamiętać, że jest to *pionowe* pole widzenia.</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="660"/>
        <source>The Material for this object</source>
        <translation>Materiał dla tego obiektu</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="98"/>
        <source>Location of light</source>
        <translation>Pozycja światła</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="104"/>
        <location filename="../../lights.py" line="209"/>
        <location filename="../../lights.py" line="428"/>
        <source>Color of light</source>
        <translation>Kolor światła</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="110"/>
        <location filename="../../lights.py" line="215"/>
        <location filename="../../lights.py" line="434"/>
        <source>Rendering power</source>
        <translation>Wydajność renderowania</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="121"/>
        <source>Light representation radius.
Note: This parameter has no impact on rendering</source>
        <translation>Promień reprezentacji światła.
Uwaga: Ten parametr nie ma wpływu na renderowanie.</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="197"/>
        <source>Size on U axis</source>
        <translation>Rozmiar na osi U</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="203"/>
        <source>Size on V axis</source>
        <translation>Rozmiar równoległy do osi V</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="221"/>
        <source>Area light transparency</source>
        <translation>Przeźroczystość oświetlenia obszaru</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="278"/>
        <source>Direction of sun from observer&apos;s point of view -- (0,0,1) is zenith</source>
        <translation>Kierunek słońca z punktu widzenia obserwatora - (0,0,1) to zenit</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="288"/>
        <source>Atmospheric haziness (turbidity can go from 2.0 to 30+. 2-6 are most useful for clear days)</source>
        <translation>Zamglenie atmosferyczne
(zmętnienie może wahać się od 2,0 do 30+.
wartość 2-6 jest najbardziej przydatne dla pogodnych dni)</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="297"/>
        <source>Ground albedo = reflection coefficient of the ground</source>
        <translation>Albedo podłoża = współczynnik odbicia gruntu</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="306"/>
        <source>Factor to tune sun light intensity. Default at 1.0</source>
        <translation>Współczynnik dostosowujący intensywność światła słonecznego.
Wartość domyślna to 1,0</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="317"/>
        <source>Factor to tune sky light intensity. Default at 1.0. WARNING: not supported by Ospray.</source>
        <translation>Współczynnik do dostrajania intensywności światła nieba.
Wartość domyślna to 1.0.
OSTRZEŻENIE: nieobsługiwane przez Ospray.</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="327"/>
        <source>The model to use for sun &amp; sky (Cycles only)</source>
        <translation>Model używany dla słońca i nieba (tylko Cycles)</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="344"/>
        <source>The gain preset to use for sun &amp; sky (Luxcore only):
* &apos;Physical&apos; yields accurate real light power, needing tone mapping or camera advanced settings
* &apos;Mitigated&apos; allows to render without tone mapping
* &apos;Interior&apos; is intended for interior scenes (through glass...)
* &apos;Custom&apos; gives full control on gain value</source>
        <translation>Wstępne ustawienie wzmocnienia dla słońca i nieba (tylko Luxcore):
 * &quot;Fizyczne&quot; zapewnia dokładną moc światła rzeczywistego, wymagając mapowania tonów lub zaawansowanych ustawień kamery.
 * &quot;Złagodzone&quot; umożliwia renderowanie bez mapowania tonów.
 * &quot;Wnętrze&quot; jest przeznaczone do scen wewnętrznych (przez szkło ...).
 * &quot;Niestandardowe&quot; zapewnia pełną kontrolę nad wartością wzmocnienia.</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="355"/>
        <source>The gain to use for sun &amp; sky when preset gain is set to &apos;Custom&apos; (Luxcore only)</source>
        <translation>Wzmocnienie używane dla słońca i nieba, gdy wstępnie ustawione wzmocnienie jest ustawione na &quot;Niestandardowe&quot; (tylko Luxcore).</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="397"/>
        <source>Image file (included in document)</source>
        <translation>Plik obrazu (zawarty w dokumencie)</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="443"/>
        <source>Direction of light from light&apos;s point of view </source>
        <translation>Kierunek światła z punktu widzenia światła </translation>
    </message>
    <message>
        <location filename="../../lights.py" line="455"/>
        <source>Apparent size of the light source, as an angle. Must be &gt; 0 for soft shadows.
Not all renderers support this parameter, please refer to your renderer&apos;s documentation.</source>
        <translation type="unfinished">Apparent size of the light source, as an angle. Must be &gt; 0 for soft shadows.
Not all renderers support this parameter, please refer to your renderer&apos;s documentation.</translation>
    </message>
    <message>
        <location filename="../../project.py" line="76"/>
        <source>The name of the raytracing engine to use</source>
        <translation>Nazwa silnika raytracin&apos;gowego do użycia</translation>
    </message>
    <message>
        <location filename="../../project.py" line="85"/>
        <source>If true, the views will be updated on render only</source>
        <translation>Jeśli prawda, widoki będą odświeżone tylko na renderingu</translation>
    </message>
    <message>
        <location filename="../../project.py" line="95"/>
        <source>The template to be used by this rendering (use Project&apos;s context menu to modify)</source>
        <translation type="unfinished">The template to be used by this rendering (use Project&apos;s context menu to modify)</translation>
    </message>
    <message>
        <location filename="../../project.py" line="104"/>
        <source>The width of the rendered image in pixels</source>
        <translation>Szerokość renderowanego obrazu w pikselach</translation>
    </message>
    <message>
        <location filename="../../project.py" line="116"/>
        <source>The height of the rendered image in pixels</source>
        <translation>Wysokość renderowanego obrazu w pikselach</translation>
    </message>
    <message>
        <location filename="../../project.py" line="129"/>
        <source>If true, a default ground plane will be added to the scene</source>
        <translation>Jeśli parametr posiada wartość prawda, do sceny zostanie dodana domyślna płaszczyzna podłoża</translation>
    </message>
    <message>
        <location filename="../../project.py" line="135"/>
        <source>Z position for ground plane</source>
        <translation>Pozycja Z dla płaszczyzny podłoża</translation>
    </message>
    <message>
        <location filename="../../project.py" line="141"/>
        <source>Ground plane color</source>
        <translation>Kolor powierzchni podłoża</translation>
    </message>
    <message>
        <location filename="../../project.py" line="147"/>
        <source>Ground plane size factor</source>
        <translation type="unfinished">Ground plane size factor</translation>
    </message>
    <message>
        <location filename="../../project.py" line="155"/>
        <source>The image saved by this render</source>
        <translation>Obraz zapisany przez ten renderer</translation>
    </message>
    <message>
        <location filename="../../project.py" line="165"/>
        <source>If true, the rendered image is opened in FreeCAD after the rendering is finished</source>
        <translation>Jeśli parametr ma wartość Prawda, wyrenderowany obraz jest otwierany w programie FreeCAD po zakończeniu renderowania</translation>
    </message>
    <message>
        <location filename="../../project.py" line="176"/>
        <source>Linear deflection for the mesher: The maximum linear deviation of a mesh section from the surface of the object.</source>
        <translation>Odchylenie liniowe dla przetwarzania siatki: Maksymalne liniowe odchylenie fragmentu siatki od powierzchni obiektu.</translation>
    </message>
    <message>
        <location filename="../../project.py" line="188"/>
        <source>Angular deflection for the mesher: The maximum angular deviation from one mesh section to the next, in radians. This setting is used when meshing curved surfaces.</source>
        <translation>Odchylenie kątowe dla przetwarzania siatki: Maksymalne odchylenie kątowe od jednej sekcji siatki do następnej, w radianach. To ustawienie jest używane podczas tworzenia siatki dla zakrzywionych powierzchni.</translation>
    </message>
    <message>
        <location filename="../../project.py" line="203"/>
        <source>Overweigh transparency in rendering (0=None (default), 10=Very high).When this parameter is set, low transparency ratios will be rendered more transparent. NB: This parameter affects only implicit materials (generated via Shape Appearance), not explicit materials (defined via Material property).</source>
        <translation>Przewaga przezroczystości w renderowaniu (0=Brak (domyślnie), 10=Bardzo wysoka). Kiedy ten parametr jest ustawiony, niskie współczynniki przezroczystości spowodują, że renderowane materiały będą bardziej przezroczyste. Uwaga: Ten parametr wpływa tylko na materiały niejawne (generowane przez Wygląd kształtu), nie na materiały jawne (definiowane przez właściwość Materiał).</translation>
    </message>
    <message>
        <location filename="../../project.py" line="212"/>
        <source>Execute in batch mode (True) or GUI interactive mode (False)</source>
        <translation type="unfinished">Execute in batch mode (True) or GUI interactive mode (False)</translation>
    </message>
    <message>
        <location filename="../../project.py" line="222"/>
        <source>Halt condition: number of samples per pixel (0 or negative = indefinite).</source>
        <translation type="unfinished">Halt condition: number of samples per pixel (0 or negative = indefinite).</translation>
    </message>
    <message>
        <location filename="../../project.py" line="233"/>
        <source>Make renderer invoke denoiser. WARNING: may not work with all renderers - the renderer must have denoising capabilities.</source>
        <translation type="unfinished">Make renderer invoke denoiser. WARNING: may not work with all renderers - the renderer must have denoising capabilities.</translation>
    </message>
    <message>
        <location filename="../../project.py" line="244"/>
        <source>Activate caustics in Appleseed (useful for interior scenes ligthened by external light sources through glass)
SPECIFIC TO APPLESEED</source>
        <translation type="unfinished">Activate caustics in Appleseed (useful for interior scenes ligthened by external light sources through glass)
SPECIFIC TO APPLESEED</translation>
    </message>
    <message>
        <location filename="../../texture.py" line="85"/>
        <source>Image(s)</source>
        <translation>Obraz(y)</translation>
    </message>
    <message>
        <location filename="../../texture.py" line="87"/>
        <source>Mapping</source>
        <translation type="unfinished">Mapping</translation>
    </message>
    <message>
        <location filename="../../texture.py" line="91"/>
        <source>Texture Image File</source>
        <translation type="unfinished">Texture Image File</translation>
    </message>
    <message>
        <location filename="../../texture.py" line="97"/>
        <source>UV rotation (in degrees)</source>
        <translation type="unfinished">UV rotation (in degrees)</translation>
    </message>
    <message>
        <location filename="../../texture.py" line="103"/>
        <source>UV scale</source>
        <translation type="unfinished">UV scale</translation>
    </message>
    <message>
        <location filename="../../texture.py" line="109"/>
        <source>UV translation - U component</source>
        <translation type="unfinished">UV translation - U component</translation>
    </message>
    <message>
        <location filename="../../texture.py" line="115"/>
        <source>UV translation - V component</source>
        <translation type="unfinished">UV translation - V component</translation>
    </message>
    <message>
        <location filename="../../view.py" line="55"/>
        <source>The source object of this view</source>
        <translation>Obiekt źródłowy dla danego widoku</translation>
    </message>
    <message>
        <location filename="../../view.py" line="66"/>
        <source>The material of this view (optional, should preferably be set in the source object)</source>
        <translation type="unfinished">The material of this view (optional, should preferably be set in the source object)</translation>
    </message>
    <message>
        <location filename="../../view.py" line="75"/>
        <source>The rendering output of this view (computed)</source>
        <translation type="unfinished">The rendering output of this view (computed)</translation>
    </message>
    <message>
        <location filename="../../view.py" line="85"/>
        <source>The type of UV projection to use for textures</source>
        <translation type="unfinished">The type of UV projection to use for textures</translation>
    </message>
    <message>
        <location filename="../../view.py" line="95"/>
        <source>Enable normal auto smoothing</source>
        <translation>Włącz normalne autowygładzanie</translation>
    </message>
    <message>
        <location filename="../../view.py" line="107"/>
        <source>Edges where an angle between the faces is smaller than specified in this Angle field will be smoothed, when auto smooth is enabled</source>
        <translation type="unfinished">Edges where an angle between the faces is smaller than specified in this Angle field will be smoothed, when auto smooth is enabled</translation>
    </message>
    <message>
        <location filename="../../view.py" line="159"/>
        <source>Force meshing even when &apos;skip_meshing&apos; is activated.</source>
        <translation type="unfinished">Force meshing even when &apos;skip_meshing&apos; is activated.</translation>
    </message>
</context>
<context>
    <name>MaterialMaterialXImportCommand</name>
    <message>
        <location filename="../../commands.py" line="461"/>
        <source>Import MaterialX file</source>
        <translation type="unfinished">Import MaterialX file</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="465"/>
        <source>Import a material from MaterialX file</source>
        <translation type="unfinished">Import a material from MaterialX file</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="491"/>
        <source>GPUOpen Material Library</source>
        <translation type="unfinished">GPUOpen Material Library</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="495"/>
        <source>Open AMD GPUOpen Material Library</source>
        <translation type="unfinished">Open AMD GPUOpen Material Library</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="521"/>
        <source>AmbientCG Material Library</source>
        <translation type="unfinished">AmbientCG Material Library</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="525"/>
        <source>Open AmbientCG Material Library</source>
        <translation type="unfinished">Open AmbientCG Material Library</translation>
    </message>
</context>
<context>
    <name>MaterialSettingsTaskPanel</name>
    <message>
        <location filename="../../taskpanels.py" line="513"/>
        <source>&lt;None&gt;</source>
        <translation>&lt;Nic&gt;</translation>
    </message>
</context>
<context>
    <name>Render</name>
    <message>
        <location filename="../../base.py" line="651"/>
        <source>Point at...</source>
        <translation>Skieruj na...</translation>
    </message>
    <message>
        <location filename="../../base.py" line="670"/>
        <source>[Point at] Please select target (on geometry)</source>
        <translation>[Skieruj na] Proszę wybrać cel (na geometrii)</translation>
    </message>
    <message>
        <location filename="../../base.py" line="699"/>
        <source>[Point at] Target outside geometry -- Aborting</source>
        <translation>[Skieruj na] Cel na zewnątrz geometrii -- Przerywanie</translation>
    </message>
    <message>
        <location filename="../../base.py" line="710"/>
        <source>[Point at] Now pointing at ({0.x}, {0.y}, {0.z})</source>
        <translation>[Skieruj na] Teraz skierowano na ({0.x}, {0.y}, {0.z})</translation>
    </message>
    <message>
        <location filename="../../camera.py" line="169"/>
        <source>Set GUI to this camera</source>
        <translation>Ustaw GUI na tę kamerę</translation>
    </message>
    <message>
        <location filename="../../camera.py" line="173"/>
        <source>Set this camera to GUI</source>
        <translation>Ustaw tę kamerę na GUI</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="185"/>
        <source>[Render] Unable to find a valid project in selection or document</source>
        <translation>[Render] Nie można znaleźć prawidłowego projektu w zaznaczeniu lub dokumencie</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="433"/>
        <source>Create material</source>
        <translation type="unfinished">Create material</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="599"/>
        <source>Empty Selection</source>
        <translation>Wybór jest pusty</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="603"/>
        <source>Please select object(s) before applying material.</source>
        <translation>Proszę, wybierz obiekt(y) przed przypisaniem materiału.</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="614"/>
        <source>No Material</source>
        <translation>Brak materiału</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="619"/>
        <source>No Material in document. Please create a Material before applying.</source>
        <translation>Brak materiału w dokumencie. Proszę, stwórz materiał przed zastosowaniem.</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="638"/>
        <source>Material Applier</source>
        <translation>Aplikator materiałów</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="639"/>
        <source>Choose Material to apply to selection:</source>
        <translation>Wybierz materiał, aby zastosować go do zaznaczenia:</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="673"/>
        <source>[Render][Material] Cannot apply Material to object &apos;%s&apos;: object&apos;s Material property is of wrong type</source>
        <translation type="unfinished">[Render][Material] Cannot apply Material to object &apos;%s&apos;: object&apos;s Material property is of wrong type</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="685"/>
        <source>[Render][Material] Cannot apply Material to object &apos;{obj.Label}&apos;: object&apos;s Material property does not accept provided material &apos;{material.Label}&apos;</source>
        <translation type="unfinished">[Render][Material] Cannot apply Material to object &apos;{obj.Label}&apos;: object&apos;s Material property does not accept provided material &apos;{material.Label}&apos;</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="693"/>
        <source>[Render][Material] Object raises ValueError {err.args}</source>
        <translation type="unfinished">[Render][Material] Object raises ValueError {err.args}</translation>
    </message>
    <message>
        <location filename="../../material.py" line="286"/>
        <source>Edit Render Settings</source>
        <translation type="unfinished">Edit Render Settings</translation>
    </message>
    <message>
        <location filename="../../material.py" line="297"/>
        <source>Edit General Settings</source>
        <translation type="unfinished">Edit General Settings</translation>
    </message>
    <message>
        <location filename="../../material.py" line="307"/>
        <source>Add Texture</source>
        <translation type="unfinished">Add Texture</translation>
    </message>
    <message>
        <location filename="../../material.py" line="477"/>
        <source>Invalid image index (&apos;{}&apos;) in texture &apos;{}&apos; -- Skipping</source>
        <translation type="unfinished">Invalid image index (&apos;{}&apos;) in texture &apos;{}&apos; -- Skipping</translation>
    </message>
    <message>
        <location filename="../../material.py" line="523"/>
        <source>Invalid image path (&apos;{}&apos;) in texture &apos;{}&apos; -- Skipping</source>
        <translation type="unfinished">Invalid image path (&apos;{}&apos;) in texture &apos;{}&apos; -- Skipping</translation>
    </message>
    <message>
        <location filename="../../material.py" line="539"/>
        <source>Missing primary image (index 0) in texture &apos;{}&apos; -- Skipping texture</source>
        <translation type="unfinished">Missing primary image (index 0) in texture &apos;{}&apos; -- Skipping texture</translation>
    </message>
    <message>
        <location filename="../../material.py" line="551"/>
        <source>No valid primary image (index 0) in texture &apos;{}&apos; -- Skipping texture</source>
        <translation type="unfinished">No valid primary image (index 0) in texture &apos;{}&apos; -- Skipping texture</translation>
    </message>
    <message>
        <location filename="../../material.py" line="588"/>
        <source>Invalid attribute &apos;{}&apos; in texture &apos;{}&apos; -- Skipping attribute</source>
        <translation type="unfinished">Invalid attribute &apos;{}&apos; in texture &apos;{}&apos; -- Skipping attribute</translation>
    </message>
    <message>
        <location filename="../../material.py" line="601"/>
        <source>Invalid type for attribute &apos;{}&apos; in texture &apos;{}&apos;: Cannot convert &apos;{}&apos; to &apos;{}&apos; -- Skipping attribute</source>
        <translation type="unfinished">Invalid type for attribute &apos;{}&apos; in texture &apos;{}&apos;: Cannot convert &apos;{}&apos; to &apos;{}&apos; -- Skipping attribute</translation>
    </message>
    <message>
        <location filename="../../material.py" line="659"/>
        <source>Invalid syntax for texture &apos;{}&apos;: No valid arguments in statement (&apos;{}&apos;) -- Skipping value</source>
        <translation type="unfinished">Invalid syntax for texture &apos;{}&apos;: No valid arguments in statement (&apos;{}&apos;) -- Skipping value</translation>
    </message>
    <message>
        <location filename="../../material.py" line="672"/>
        <source>Invalid syntax for attribute &apos;{}&apos; in texture &apos;{}&apos;: Expecting &apos;Texture(&quot;&lt;texname&gt;&quot;, &lt;texindex&gt;)&apos;, got &apos;{}&apos; instead -- Skipping value</source>
        <translation type="unfinished">Invalid syntax for attribute &apos;{}&apos; in texture &apos;{}&apos;: Expecting &apos;Texture(&quot;&lt;texname&gt;&quot;, &lt;texindex&gt;)&apos;, got &apos;{}&apos; instead -- Skipping value</translation>
    </message>
    <message>
        <location filename="../../material.py" line="685"/>
        <source>Invalid syntax for attribute &apos;{}&apos; in texture &apos;{}&apos;: Reference to texture should be a tuple (&apos;&lt;texture&gt;&apos;, &lt;index&gt;, [&lt;scalar&gt;]) -- Skipping value</source>
        <translation type="unfinished">Invalid syntax for attribute &apos;{}&apos; in texture &apos;{}&apos;: Reference to texture should be a tuple (&apos;&lt;texture&gt;&apos;, &lt;index&gt;, [&lt;scalar&gt;]) -- Skipping value</translation>
    </message>
    <message>
        <location filename="../../material.py" line="708"/>
        <source>Invalid syntax for attribute &apos;{}&apos; in texture &apos;{}&apos;: Scalar should be a float -- Skipping value</source>
        <translation type="unfinished">Invalid syntax for attribute &apos;{}&apos; in texture &apos;{}&apos;: Scalar should be a float -- Skipping value</translation>
    </message>
    <message>
        <location filename="../../project.py" line="346"/>
        <source>[Render] Unable to create rendering view for object &apos;{o}&apos;: unhandled object type</source>
        <translation>[Render] Nie można utworzyć widoku renderowania dla obiektu &apos;{o}&apos;: nieobsługiwany typ obiektu</translation>
    </message>
    <message>
        <location filename="../../project.py" line="430"/>
        <source>[Render][Project] CRITICAL ERROR - Negative or zero value(s) for Render Height and/or Render Width: cannot render. Aborting...
</source>
        <translation type="unfinished">[Render][Project] CRITICAL ERROR - Negative or zero value(s) for Render Height and/or Render Width: cannot render. Aborting...
</translation>
    </message>
    <message>
        <location filename="../../project.py" line="444"/>
        <source>[Render][Project] WARNING - Output image path &apos;{params.output}&apos; does not seem to be a valid path on your system. This may cause the renderer to fail...
</source>
        <translation type="unfinished">[Render][Project] WARNING - Output image path &apos;{params.output}&apos; does not seem to be a valid path on your system. This may cause the renderer to fail...
</translation>
    </message>
    <message>
        <location filename="../../project.py" line="471"/>
        <source>Renderer not found (&apos;{}&apos;) </source>
        <translation type="unfinished">Renderer not found (&apos;{}&apos;) </translation>
    </message>
    <message>
        <location filename="../../project.py" line="509"/>
        <source>Empty rendering command</source>
        <translation type="unfinished">Empty rendering command</translation>
    </message>
    <message>
        <location filename="../../project.py" line="572"/>
        <source>Template not found (&apos;{}&apos;)</source>
        <translation type="unfinished">Template not found (&apos;{}&apos;)</translation>
    </message>
    <message>
        <location filename="../../project.py" line="733"/>
        <source>Cannot render project:</source>
        <translation type="unfinished">Cannot render project:</translation>
    </message>
    <message>
        <location filename="../../project.py" line="743"/>
        <source>Render</source>
        <translation type="unfinished">Render</translation>
    </message>
    <message>
        <location filename="../../project.py" line="748"/>
        <source>Change template</source>
        <translation type="unfinished">Change template</translation>
    </message>
    <message>
        <location filename="../../project.py" line="768"/>
        <source>Warning: Deleting Non-Empty Project</source>
        <translation>Uwaga: Usuwa nie pusty projekt</translation>
    </message>
    <message>
        <location filename="../../project.py" line="774"/>
        <source>Project is not empty. All its contents will be deleted too.

Are you sure you want to continue?</source>
        <translation>Projekt nie jest pusty. Cała jego zawartość również zostanie usunięta.

Jesteś pewien, że chcesz kontynuować?</translation>
    </message>
    <message>
        <location filename="../../project.py" line="797"/>
        <source>[Render] Cannot render: {e}</source>
        <translation>[Render] Nie może renderować: {e}</translation>
    </message>
    <message>
        <location filename="../../project.py" line="843"/>
        <source>Select template</source>
        <translation type="unfinished">Select template</translation>
    </message>
    <message>
        <location filename="../../rdrhandler.py" line="341"/>
        <source>Exporting</source>
        <translation type="unfinished">Exporting</translation>
    </message>
    <message>
        <location filename="../../rdrhandler.py" line="831"/>
        <source>[Render] Error: Renderer &apos;%s&apos; not found</source>
        <translation type="unfinished">[Render] Error: Renderer &apos;%s&apos; not found</translation>
    </message>
    <message>
        <location filename="../../renderables.py" line="254"/>
        <source>Unhandled object type (&apos;{name}&apos;: {ascendants})</source>
        <translation type="unfinished">Unhandled object type (&apos;{name}&apos;: {ascendants})</translation>
    </message>
    <message>
        <location filename="../../renderables.py" line="274"/>
        <source>Nothing to render</source>
        <translation>Nie ma nic do renderowania</translation>
    </message>
    <message>
        <location filename="../../renderables.py" line="283"/>
        <source>Cannot find mesh data</source>
        <translation>Nie można znaleźć danych siatki</translation>
    </message>
    <message>
        <location filename="../../renderables.py" line="290"/>
        <source>Mesh topology is empty</source>
        <translation>Topologia siatki jest pusta</translation>
    </message>
    <message>
        <location filename="../../renderables.py" line="677"/>
        <source>Incomplete multimaterial (missing {m})</source>
        <translation>Nie kompletne wszystkie materiały (brakuje {m})</translation>
    </message>
    <message>
        <location filename="../../taskpanels.py" line="276"/>
        <source>Use object color</source>
        <translation type="unfinished">Use object color</translation>
    </message>
    <message>
        <location filename="../../taskpanels.py" line="282"/>
        <source>Use constant color</source>
        <translation type="unfinished">Use constant color</translation>
    </message>
    <message>
        <location filename="../../taskpanels.py" line="294"/>
        <location filename="../../taskpanels.py" line="389"/>
        <location filename="../../taskpanels.py" line="471"/>
        <source>Use texture</source>
        <translation type="unfinished">Use texture</translation>
    </message>
    <message>
        <location filename="../../taskpanels.py" line="374"/>
        <source>Use constant value</source>
        <translation type="unfinished">Use constant value</translation>
    </message>
    <message>
        <location filename="../../taskpanels.py" line="467"/>
        <source>Don&apos;t use</source>
        <translation type="unfinished">Don&apos;t use</translation>
    </message>
    <message>
        <location filename="../../taskpanels.py" line="783"/>
        <source>Factor:</source>
        <translation type="unfinished">Factor:</translation>
    </message>
    <message>
        <location filename="../../texture.py" line="196"/>
        <source>Add Image Entry</source>
        <translation type="unfinished">Add Image Entry</translation>
    </message>
    <message>
        <location filename="../../texture.py" line="199"/>
        <source>Remove Image Entry</source>
        <translation type="unfinished">Remove Image Entry</translation>
    </message>
    <message>
        <location filename="../../texture.py" line="216"/>
        <source>Unallowed Image Removal</source>
        <translation type="unfinished">Unallowed Image Removal</translation>
    </message>
    <message>
        <location filename="../../texture.py" line="220"/>
        <source>Unallowed removal: not enough images in texture (&lt;2)!
</source>
        <translation type="unfinished">Unallowed removal: not enough images in texture (&lt;2)!
</translation>
    </message>
    <message>
        <location filename="../../texture.py" line="224"/>
        <source>Leaving less than 1 image in texture is not allowed...</source>
        <translation type="unfinished">Leaving less than 1 image in texture is not allowed...</translation>
    </message>
    <message>
        <location filename="../../texture.py" line="233"/>
        <source>Texture Image Removal</source>
        <translation type="unfinished">Texture Image Removal</translation>
    </message>
    <message>
        <location filename="../../texture.py" line="234"/>
        <source>Choose Image to remove:</source>
        <translation type="unfinished">Choose Image to remove:</translation>
    </message>
</context>
<context>
    <name>RenderMaterial</name>
    <message>
        <location filename="../ui/RenderMaterial.ui" line="14"/>
        <source>Material Rendering Settings</source>
        <translation>Ustawienia Renderowania Materiału</translation>
    </message>
    <message>
        <location filename="../ui/RenderMaterial.ui" line="28"/>
        <location filename="../ui/RenderMaterial.ui" line="32"/>
        <source>Choose material...</source>
        <translation>Wybierz materiał ...</translation>
    </message>
    <message>
        <location filename="../ui/RenderMaterial.ui" line="89"/>
        <source>Standard</source>
        <translation>Standardowy</translation>
    </message>
    <message>
        <location filename="../ui/RenderMaterial.ui" line="110"/>
        <source>Material Type:</source>
        <translation>Rodzaj materiału:</translation>
    </message>
    <message>
        <location filename="../ui/RenderMaterial.ui" line="121"/>
        <source>Choose material type...</source>
        <translation>Wybierz rodzaj materiału ...</translation>
    </message>
    <message>
        <location filename="../ui/RenderMaterial.ui" line="130"/>
        <source>Passthrough</source>
        <translation>Przejście</translation>
    </message>
    <message>
        <location filename="../ui/RenderMaterial.ui" line="149"/>
        <source>Passthrough Text</source>
        <translation>Tekst przejścia</translation>
    </message>
    <message>
        <location filename="../ui/RenderMaterial.ui" line="179"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;&lt;span style=&quot; font-size:8pt; font-style:italic;&quot;&gt;Warning: This text will be sent to renderer &amp;quot;as is&amp;quot; and will override any other material rendering settings. Be sure you know what you do when modifying it...&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;&lt;span style=&quot; font-size:8pt; font-style:italic;&quot;&gt;Ostrzeżenie: Ten tekst zostanie wysłany do renderera &amp;quot;w obecnym stanie&amp;quot; i zastąpi wszelkie inne ustawienia renderowania materiału. Upewnij się, że wiesz co robisz modyfikując go...&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</translation>
    </message>
    <message>
        <location filename="../ui/RenderMaterial.ui" line="192"/>
        <source>Force UVMap computation</source>
        <translation type="unfinished">Force UVMap computation</translation>
    </message>
    <message>
        <location filename="../ui/RenderMaterial.ui" line="206"/>
        <source>Fallback</source>
        <translation>Awaria/Powrót do góry</translation>
    </message>
    <message>
        <location filename="../ui/RenderMaterial.ui" line="215"/>
        <source>Father Material:</source>
        <translation>Materiał nadrzędny:</translation>
    </message>
</context>
<context>
    <name>RenderSettings</name>
    <message>
        <location filename="../ui/RenderSettings.ui" line="14"/>
        <source>Render preferences</source>
        <translation type="unfinished">Render preferences</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="20"/>
        <source>Plugins</source>
        <translation type="unfinished">Plugins</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="29"/>
        <source>Update Pip when reloading</source>
        <translation type="unfinished">Update Pip when reloading</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="39"/>
        <source>Disable GUI embedding</source>
        <translation type="unfinished">Disable GUI embedding</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="65"/>
        <source>Enable MaterialX features</source>
        <translation type="unfinished">Enable MaterialX features</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="91"/>
        <source>Reset Plugins Environment</source>
        <extracomment>Reload all dependencies needed by plugins</extracomment>
        <translation type="unfinished">Reset Plugins Environment</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="117"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Standard behavior is to download virtual environment package (&apos;venv&apos;)  from pypa.io.&lt;/p&gt;&lt;p&gt;If checked, Render will use the package provided by system Python installation instead.&lt;/p&gt;&lt;p&gt;&lt;br/&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation type="unfinished">&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Standard behavior is to download virtual environment package (&apos;venv&apos;)  from pypa.io.&lt;/p&gt;&lt;p&gt;If checked, Render will use the package provided by system Python installation instead.&lt;/p&gt;&lt;p&gt;&lt;br/&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="139"/>
        <source>Use system virtualenv package</source>
        <translation type="unfinished">Use system virtualenv package</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="149"/>
        <location filename="../ui/RenderSettings.ui" line="155"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Advanced and Debug parameters&lt;/p&gt;&lt;p&gt;&lt;span style=&quot; font-weight:600;&quot;&gt;WARNING&lt;/span&gt; - Do not modify if you don&apos;t know what you do - Unexpected behaviours may result...&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation type="unfinished">&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Advanced and Debug parameters&lt;/p&gt;&lt;p&gt;&lt;span style=&quot; font-weight:600;&quot;&gt;WARNING&lt;/span&gt; - Do not modify if you don&apos;t know what you do - Unexpected behaviours may result...&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="152"/>
        <source>Advanced and Debug parameters WARNING - Do not modify if you don&apos;t know what you do - Unexpected behaviours may result...</source>
        <translation type="unfinished">Advanced and Debug parameters WARNING - Do not modify if you don&apos;t know what you do - Unexpected behaviours may result...</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="161"/>
        <source>Advanced &amp;&amp; Debug</source>
        <translation type="unfinished">Advanced &amp;&amp; Debug</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="186"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Dry run &lt;span style=&quot; font-size:8pt; font-style:italic;&quot;&gt;(won&apos;t run renderer - debug purpose only)&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation type="unfinished">&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Dry run &lt;span style=&quot; font-size:8pt; font-style:italic;&quot;&gt;(won&apos;t run renderer - debug purpose only)&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="193"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Enable multiprocessing &lt;span style=&quot; font-size:8pt; font-style:italic;&quot;&gt;(experimental)&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation type="unfinished">&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Enable multiprocessing &lt;span style=&quot; font-size:8pt; font-style:italic;&quot;&gt;(experimental)&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="216"/>
        <source>Do not modify ShapeColor when assigning material</source>
        <translation type="unfinished">Do not modify ShapeColor when assigning material</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="223"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Disable Numpy&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation type="unfinished">&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Disable Numpy&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="243"/>
        <source>Use UUID for exported file names</source>
        <translation type="unfinished">Use UUID for exported file names</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="288"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Use FreeCAD materials directory &lt;span style=&quot; font-size:8pt; font-style:italic;&quot;&gt;(not recommended)&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation type="unfinished">&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Use FreeCAD materials directory &lt;span style=&quot; font-size:8pt; font-style:italic;&quot;&gt;(not recommended)&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="321"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Multiprocessing threshold &lt;span style=&quot; font-size:8pt; font-style:italic;&quot;&gt;(number of points)&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation type="unfinished">&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Multiprocessing threshold &lt;span style=&quot; font-size:8pt; font-style:italic;&quot;&gt;(number of points)&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="328"/>
        <source>Clear report view before each run</source>
        <translation type="unfinished">Clear report view before each run</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="361"/>
        <source>Auto import module at startup</source>
        <translation type="unfinished">Auto import module at startup</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="374"/>
        <source>LuxRender (deprecated)</source>
        <translation type="unfinished">LuxRender (deprecated)</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="380"/>
        <location filename="../ui/RenderSettings.ui" line="603"/>
        <source>Optional parameters to be passed to Luxrender when rendering</source>
        <translation type="unfinished">Optional parameters to be passed to Luxrender when rendering</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="402"/>
        <source>LuxRender UI path</source>
        <translation type="unfinished">LuxRender UI path</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="409"/>
        <location filename="../ui/RenderSettings.ui" line="473"/>
        <source>The path to the luxrender UI executable</source>
        <translation type="unfinished">The path to the luxrender UI executable</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="428"/>
        <location filename="../ui/RenderSettings.ui" line="528"/>
        <location filename="../ui/RenderSettings.ui" line="705"/>
        <location filename="../ui/RenderSettings.ui" line="903"/>
        <location filename="../ui/RenderSettings.ui" line="993"/>
        <location filename="../ui/RenderSettings.ui" line="1054"/>
        <location filename="../ui/RenderSettings.ui" line="1170"/>
        <source>Render parameters</source>
        <translation type="unfinished">Render parameters</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="438"/>
        <source>LuxRender command (cli) path</source>
        <translation type="unfinished">LuxRender command (cli) path</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="445"/>
        <location filename="../ui/RenderSettings.ui" line="489"/>
        <source>The path to the Luxrender console (luxconsole) executable</source>
        <translation type="unfinished">The path to the Luxrender console (luxconsole) executable</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="508"/>
        <source>LuxCore command (cli) path</source>
        <translation type="unfinished">LuxCore command (cli) path</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="518"/>
        <source>LuxCore UI path</source>
        <translation type="unfinished">LuxCore UI path</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="596"/>
        <source>LuxCore engine</source>
        <translation type="unfinished">LuxCore engine</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="622"/>
        <location filename="../ui/RenderSettings.ui" line="635"/>
        <location filename="../ui/RenderSettings.ui" line="725"/>
        <location filename="../ui/RenderSettings.ui" line="936"/>
        <location filename="../ui/RenderSettings.ui" line="949"/>
        <location filename="../ui/RenderSettings.ui" line="1029"/>
        <location filename="../ui/RenderSettings.ui" line="1103"/>
        <location filename="../ui/RenderSettings.ui" line="1177"/>
        <source>Test</source>
        <translation>Test</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="679"/>
        <source>OspStudio executable path</source>
        <translation type="unfinished">OspStudio executable path</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="744"/>
        <source>General</source>
        <translation type="unfinished">General</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="753"/>
        <source>Default render width</source>
        <translation type="unfinished">Default render width</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="807"/>
        <source>Prefix</source>
        <translation type="unfinished">Prefix</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="817"/>
        <source>Default render height</source>
        <translation type="unfinished">Default render height</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="824"/>
        <source>A prefix that can be added before the renderer executable. This is useful, for example, to add environment variable or run the renderer inside a GPU switcher such as primusrun or optirun on linux</source>
        <translation type="unfinished">A prefix that can be added before the renderer executable. This is useful, for example, to add environment variable or run the renderer inside a GPU switcher such as primusrun or optirun on linux</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="858"/>
        <source>Appleseed Studio path</source>
        <translation type="unfinished">Appleseed Studio path</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="865"/>
        <source>The path to the Appleseed cli executable</source>
        <translation type="unfinished">The path to the Appleseed cli executable</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="881"/>
        <source>Optional rendering parameters to be passed to the Appleseed executable</source>
        <translation type="unfinished">Optional rendering parameters to be passed to the Appleseed executable</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="910"/>
        <source>The path to the Appleseed studio executable (optional)</source>
        <translation type="unfinished">The path to the Appleseed studio executable (optional)</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="929"/>
        <source>Appleseed command (cli) path</source>
        <translation type="unfinished">Appleseed command (cli) path</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="974"/>
        <source>The path to the Pov-Ray executable</source>
        <translation type="unfinished">The path to the Pov-Ray executable</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="1000"/>
        <source>Optional parameters to be passed to Pov-Ray when rendering</source>
        <translation type="unfinished">Optional parameters to be passed to Pov-Ray when rendering</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="1022"/>
        <source>PovRay executable path</source>
        <translation type="unfinished">PovRay executable path</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="1077"/>
        <source>Pbrt executable path</source>
        <translation type="unfinished">Pbrt executable path</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="1147"/>
        <source>Cycles executable (standalone) path</source>
        <translation type="unfinished">Cycles executable (standalone) path</translation>
    </message>
</context>
<context>
    <name>Render_AreaLight</name>
    <message>
        <location filename="../../commands.py" line="298"/>
        <source>Area Light</source>
        <translation type="unfinished">Area Light</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="301"/>
        <source>Create an Area Light object</source>
        <translation type="unfinished">Create an Area Light object</translation>
    </message>
</context>
<context>
    <name>Render_Camera</name>
    <message>
        <location filename="../../commands.py" line="245"/>
        <source>Camera</source>
        <translation type="unfinished">Camera</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="249"/>
        <source>Create a Camera object from the current camera position</source>
        <translation type="unfinished">Create a Camera object from the current camera position</translation>
    </message>
</context>
<context>
    <name>Render_DistantLight</name>
    <message>
        <location filename="../../commands.py" line="380"/>
        <source>Distant Light</source>
        <translation type="unfinished">Distant Light</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="383"/>
        <source>Create an Distant Light object</source>
        <translation type="unfinished">Create an Distant Light object</translation>
    </message>
</context>
<context>
    <name>Render_Help</name>
    <message>
        <location filename="../../commands.py" line="713"/>
        <source>Help</source>
        <translation>Pomoc</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="717"/>
        <source>Open Render help</source>
        <translation type="unfinished">Open Render help</translation>
    </message>
</context>
<context>
    <name>Render_ImageLight</name>
    <message>
        <location filename="../../commands.py" line="352"/>
        <source>Image Light</source>
        <translation type="unfinished">Image Light</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="355"/>
        <source>Create an Image Light object</source>
        <translation type="unfinished">Create an Image Light object</translation>
    </message>
</context>
<context>
    <name>Render_Libraries</name>
    <message>
        <location filename="../../commands.py" line="844"/>
        <source>Libraries</source>
        <translation type="unfinished">Libraries</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="847"/>
        <source>Download from material libraries</source>
        <translation type="unfinished">Download from material libraries</translation>
    </message>
</context>
<context>
    <name>Render_Lights</name>
    <message>
        <location filename="../../commands.py" line="822"/>
        <source>Lights</source>
        <translation type="unfinished">Lights</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="823"/>
        <source>Create a Light</source>
        <translation type="unfinished">Create a Light</translation>
    </message>
</context>
<context>
    <name>Render_MaterialApplier</name>
    <message>
        <location filename="../../commands.py" line="582"/>
        <source>Apply Material</source>
        <translation type="unfinished">Apply Material</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="585"/>
        <source>Apply a Material to selection</source>
        <translation type="unfinished">Apply a Material to selection</translation>
    </message>
</context>
<context>
    <name>Render_MaterialCreator</name>
    <message>
        <location filename="../../commands.py" line="414"/>
        <source>Internal Material Library</source>
        <translation type="unfinished">Internal Material Library</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="418"/>
        <source>Create Material</source>
        <translation type="unfinished">Create Material</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="425"/>
        <source>Create a new Material in current document from internal library</source>
        <translation type="unfinished">Create a new Material in current document from internal library</translation>
    </message>
</context>
<context>
    <name>Render_MaterialRenderSettings</name>
    <message>
        <location filename="../../commands.py" line="551"/>
        <source>Edit Material Render Settings</source>
        <translation type="unfinished">Edit Material Render Settings</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="555"/>
        <source>Edit rendering parameters of the selected Material</source>
        <translation type="unfinished">Edit rendering parameters of the selected Material</translation>
    </message>
</context>
<context>
    <name>Render_Materials</name>
    <message>
        <location filename="../../commands.py" line="832"/>
        <source>Materials</source>
        <translation>Materiały</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="833"/>
        <source>Manage Materials</source>
        <translation type="unfinished">Manage Materials</translation>
    </message>
</context>
<context>
    <name>Render_PointLight</name>
    <message>
        <location filename="../../commands.py" line="272"/>
        <source>Point Light</source>
        <translation type="unfinished">Point Light</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="275"/>
        <source>Create a Point Light object</source>
        <translation type="unfinished">Create a Point Light object</translation>
    </message>
</context>
<context>
    <name>Render_Projects</name>
    <message>
        <location filename="../../commands.py" line="109"/>
        <source>{} Project</source>
        <translation type="unfinished">{} Project</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="110"/>
        <source>Create a {} project</source>
        <translation type="unfinished">Create a {} project</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="809"/>
        <source>Projects</source>
        <translation type="unfinished">Projects</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="810"/>
        <source>Create a Rendering Project</source>
        <translation type="unfinished">Create a Rendering Project</translation>
    </message>
</context>
<context>
    <name>Render_Render</name>
    <message>
        <location filename="../../commands.py" line="207"/>
        <source>Render project</source>
        <translation type="unfinished">Render project</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="213"/>
        <source>Perform the rendering of a selected project or the default project</source>
        <translation type="unfinished">Perform the rendering of a selected project or the default project</translation>
    </message>
</context>
<context>
    <name>Render_Settings</name>
    <message>
        <location filename="../../commands.py" line="739"/>
        <source>Render settings</source>
        <translation type="unfinished">Render settings</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="743"/>
        <source>Open Render workbench settings</source>
        <translation type="unfinished">Open Render workbench settings</translation>
    </message>
</context>
<context>
    <name>Render_SunskyLight</name>
    <message>
        <location filename="../../commands.py" line="326"/>
        <source>Sunsky Light</source>
        <translation type="unfinished">Sunsky Light</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="329"/>
        <source>Create a Sunsky Light object</source>
        <translation type="unfinished">Create a Sunsky Light object</translation>
    </message>
</context>
<context>
    <name>Render_View</name>
    <message>
        <location filename="../../commands.py" line="149"/>
        <source>Rendering View</source>
        <translation type="unfinished">Rendering View</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="155"/>
        <source>Create a Rendering View of the selected object(s) in the selected project or the default project</source>
        <translation type="unfinished">Create a Rendering View of the selected object(s) in the selected project or the default project</translation>
    </message>
</context>
<context>
    <name>Workbench</name>
    <message>
        <location filename="../../../InitGui.py" line="52"/>
        <source>The Render workbench is a modern replacement for the Raytracing workbench</source>
        <translation type="unfinished">The Render workbench is a modern replacement for the Raytracing workbench</translation>
    </message>
    <message>
        <location filename="../../../InitGui.py" line="132"/>
        <source>Render</source>
        <translation type="unfinished">Render</translation>
    </message>
    <message>
        <location filename="../../../InitGui.py" line="135"/>
        <source>&amp;Render</source>
        <translation>&amp;Renderuj</translation>
    </message>
    <message>
        <location filename="../../../InitGui.py" line="139"/>
        <source>Loading Render module... done</source>
        <translation type="unfinished">Loading Render module... done</translation>
    </message>
</context>
</TS>
