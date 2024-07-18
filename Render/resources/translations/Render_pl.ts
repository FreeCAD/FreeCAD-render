<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="pl" sourcelanguage="en">
  <context>
    <name>App::Property</name>
    <message>
      <location filename="../../camera.py" line="87"/>
      <source>Type of projection: Perspective/Orthographic</source>
      <translation>Typ projekcji: Perspektywiczny / Ortograficzny</translation>
    </message>
    <message>
      <location filename="../../camera.py" line="95"/>
      <source>(See Coin documentation)</source>
      <translation>(Patrz dokumentacja Coin)</translation>
    </message>
    <message>
      <location filename="../../camera.py" line="101"/>
      <source>Ratio width/height of the camera.</source>
      <translation>Stosunek szerokości do wysokości ujęcia widoku.</translation>
    </message>
    <message>
      <location filename="../../camera.py" line="109"/>
      <source>Near distance, for clipping</source>
      <translation>Niewielka odległość, w celu przycięcia</translation>
    </message>
    <message>
      <location filename="../../camera.py" line="115"/>
      <source>Far distance, for clipping</source>
      <translation>Duża odległość, w celu przycięcia</translation>
    </message>
    <message>
      <location filename="../../camera.py" line="121"/>
      <source>Focal distance</source>
      <translation>Odległość ogniskowania</translation>
    </message>
    <message>
      <location filename="../../camera.py" line="127"/>
      <source>Height, for orthographic camera</source>
      <translation>Wysokość, do aparatu z widokiem ortogonalnym</translation>
    </message>
    <message>
      <location filename="../../camera.py" line="135"/>
      <source>Height angle, for perspective camera, in degrees. Important: This value will be sent as &apos;Field of View&apos; to the renderers. Please note it is a *vertical* field-of-view.</source>
      <translation>Kąt wysokości dla kamery perspektywicznej, w stopniach. Ważne: Ta wartość zostanie wysłana jako "Pole widzenia" do programów renderujących. Należy pamiętać, że jest to *pionowe* pole widzenia.</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="609"/>
      <source>The Material for this object</source>
      <translation>Materiał dla tego obiektu</translation>
    </message>
    <message>
      <location filename="../../lights.py" line="98"/>
      <source>Location of light</source>
      <translation>Pozycja światła</translation>
    </message>
    <message>
      <location filename="../../lights.py" line="428"/>
      <location filename="../../lights.py" line="209"/>
      <location filename="../../lights.py" line="104"/>
      <source>Color of light</source>
      <translation>Kolor światła</translation>
    </message>
    <message>
      <location filename="../../lights.py" line="434"/>
      <location filename="../../lights.py" line="215"/>
      <location filename="../../lights.py" line="110"/>
      <source>Rendering power</source>
      <translation>Wydajność renderowania</translation>
    </message>
    <message>
      <location filename="../../lights.py" line="116"/>
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
      <translation>Rozmiar na osi V</translation>
    </message>
    <message>
      <location filename="../../lights.py" line="221"/>
      <source>Area light transparency</source>
      <translation>Przeźroczystość oświetlenia obszaru</translation>
    </message>
    <message>
      <location filename="../../lights.py" line="274"/>
      <source>Direction of sun from observer&apos;s point of view -- (0,0,1) is zenith</source>
      <translation>Kierunek słońca z punktu widzenia obserwatora - (0,0,1) to zenit.</translation>
    </message>
    <message>
      <location filename="../../lights.py" line="284"/>
      <source>Atmospheric haziness (turbidity can go from 2.0 to 30+. 2-6 are most useful for clear days)</source>
      <translation>Zamglenie atmosferyczne (zmętnienie może wahać się od 2,0 do 30+. 2-6 jest najbardziej przydatne dla pogodnych dni)</translation>
    </message>
    <message>
      <location filename="../../lights.py" line="294"/>
      <source>Ground albedo = reflection coefficient of the ground</source>
      <translation>Albedo podłoża = współczynnik odbicia gruntu</translation>
    </message>
    <message>
      <location filename="../../lights.py" line="303"/>
      <source>Factor to tune sun light intensity. Default at 1.0</source>
      <translation>Współczynnik dostosowujący intensywność światła słonecznego.
Wartość domyślna 1,0.</translation>
    </message>
    <message>
      <location filename="../../lights.py" line="312"/>
      <source>Factor to tune sky light intensity. Default at 1.0. WARNING: not supported by Ospray.</source>
      <translation>Współczynnik do dostrajania intensywności światła nieba.
Wartość domyślna 1.0.
OSTRZEŻENIE: nieobsługiwane przez Ospray.</translation>
    </message>
    <message>
      <location filename="../../lights.py" line="324"/>
      <source>The model to use for sun &amp; sky (Cycles only)</source>
      <translation>Model używany dla słońca i nieba (tylko Cycles).</translation>
    </message>
    <message>
      <location filename="../../lights.py" line="335"/>
      <source>The gain preset to use for sun &amp; sky (Luxcore only):
* &apos;Physical&apos; yields accurate real light power, needing tone mapping or camera advanced settings
* &apos;Mitigated&apos; allows to render without tone mapping
* &apos;Interior&apos; is intended for interior scenes (through glass...)
* &apos;Custom&apos; gives full control on gain value</source>
      <translation>Wstępne ustawienie wzmocnienia dla słońca i nieba (tylko Luxcore):
 * "Fizyczne" zapewnia dokładną moc światła rzeczywistego, wymagając mapowania tonów lub zaawansowanych ustawień kamery.
 * "Złagodzone" umożliwia renderowanie bez mapowania tonów.
 * "Wnętrze" jest przeznaczone do scen wewnętrznych (przez szkło ...).
 * "Niestandardowe" zapewnia pełną kontrolę nad wartością wzmocnienia.</translation>
    </message>
    <message>
      <location filename="../../lights.py" line="351"/>
      <source>The gain to use for sun &amp; sky when preset gain is set to &apos;Custom&apos; (Luxcore only)</source>
      <translation>Wzmocnienie używane dla słońca i nieba, gdy wstępnie ustawione wzmocnienie jest ustawione na "Niestandardowe" (tylko Luxcore).</translation>
    </message>
    <message>
      <location filename="../../lights.py" line="395"/>
      <source>Image file (included in document)</source>
      <translation>Plik obrazu (zawarty w dokumencie)</translation>
    </message>
    <message>
      <location filename="../../lights.py" line="440"/>
      <source>Direction of light from light&apos;s point of view </source>
      <translation>Kierunek światła z punktu widzenia światła </translation>
    </message>
    <message>
      <location filename="../../lights.py" line="449"/>
      <source>Apparent size of the light source, as an angle. Must be &gt; 0 for soft shadows.
Not all renderers support this parameter, please refer to your renderer&apos;s documentation.</source>
      <translation>Pozorny rozmiar źródła światła jako kąt. Musi być > 0 dla miękkich cieni.
Nie wszystkie programy renderujące obsługują ten parametr, należy zapoznać się z dokumentacją programu renderującego.</translation>
    </message>
    <message>
      <location filename="../../project.py" line="73"/>
      <source>The name of the raytracing engine to use</source>
      <translation>Nazwa silnika raytracin'gowego do użycia</translation>
    </message>
    <message>
      <location filename="../../project.py" line="82"/>
      <source>If true, the views will be updated on render only</source>
      <translation>Jeśli prawda, widoki będą odświeżone tylko na renderingu</translation>
    </message>
    <message>
      <location filename="../../project.py" line="91"/>
      <source>The template to be used by this rendering (use Project&apos;s context menu to modify)</source>
      <translation>Szablon, który ma być używany przez ten rendering
(użyj menu kontekstowego projektu, aby zmodyfikować).</translation>
    </message>
    <message>
      <location filename="../../project.py" line="102"/>
      <source>The width of the rendered image in pixels</source>
      <translation>Szerokość renderowanego obrazu w pikselach</translation>
    </message>
    <message>
      <location filename="../../project.py" line="114"/>
      <source>The height of the rendered image in pixels</source>
      <translation>Wysokość renderowanego obrazu w pikselach</translation>
    </message>
    <message>
      <location filename="../../project.py" line="126"/>
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
      <translation>Współczynnik rozmiaru płaszczyzny podłoża</translation>
    </message>
    <message>
      <location filename="../../project.py" line="153"/>
      <source>The image saved by this render</source>
      <translation>Obraz zapisany przez ten renderer</translation>
    </message>
    <message>
      <location filename="../../project.py" line="161"/>
      <source>If true, the rendered image is opened in FreeCAD after the rendering is finished</source>
      <translation>Jeśli parametr ma wartość Prawda, wyrenderowany obraz jest otwierany w programie FreeCAD po zakończeniu renderowania</translation>
    </message>
    <message>
      <location filename="../../project.py" line="171"/>
      <source>Linear deflection for the mesher: The maximum linear deviation of a mesh section from the surface of the object.</source>
      <translation>Odchylenie liniowe dla przetwarzania siatki: Maksymalne liniowe odchylenie fragmentu siatki od powierzchni obiektu.</translation>
    </message>
    <message>
      <location filename="../../project.py" line="182"/>
      <source>Angular deflection for the mesher: The maximum angular deviation from one mesh section to the next, in radians. This setting is used when meshing curved surfaces.</source>
      <translation>Odchylenie kątowe dla przetwarzania siatki: Maksymalne odchylenie kątowe od jednej sekcji siatki do następnej, w radianach. To ustawienie jest używane podczas tworzenia siatki dla zakrzywionych powierzchni.</translation>
    </message>
    <message>
      <location filename="../../project.py" line="194"/>
      <source>Overweigh transparency in rendering (0=None (default), 10=Very high).When this parameter is set, low transparency ratios will be rendered more transparent. NB: This parameter affects only implicit materials (generated via Shape Appearance), not explicit materials (defined via Material property).</source>
      <translation>Przewaga przezroczystości w renderowaniu (0=Brak (domyślnie), 10=Bardzo wysoka). Kiedy ten parametr jest ustawiony, niskie współczynniki przezroczystości spowodują, że renderowane materiały będą bardziej przezroczyste. Uwaga: Ten parametr wpływa tylko na materiały niejawne (generowane przez Wygląd kształtu), nie na materiały jawne (definiowane przez właściwość Materiał).</translation>
    </message>
    <message>
      <location filename="../../project.py" line="209"/>
      <source>Execute in batch mode (True) or GUI interactive mode (False)</source>
      <translation>Wykonanie w trybie wsadowym ("Prawda") lub w trybie interaktywnym GUI ("Fałsz").</translation>
    </message>
    <message>
      <location filename="../../project.py" line="218"/>
      <source>Halt condition: number of samples per pixel (0 or negative = indefinite).</source>
      <translation>Warunek zatrzymania:
liczba próbek na piksel (0 lub ujemna = nieokreślona).</translation>
    </message>
    <message>
      <location filename="../../project.py" line="228"/>
      <source>Make renderer invoke denoiser. WARNING: may not work with all renderers - the renderer must have denoising capabilities.</source>
      <translation>Sprawia, że renderer wywołuje "denoiser".
OSTRZEŻENIE: może nie działać ze wszystkimi rendererami - renderer musi mieć możliwość odszumiania.</translation>
    </message>
    <message>
      <location filename="../../project.py" line="239"/>
      <source>Activate caustics in Appleseed (useful for interior scenes ligthened by external light sources through glass)
SPECIFIC TO APPLESEED</source>
      <translation>Aktywuje żrące efekty w Appleseed (przydatne do scen wewnętrznych oświetlonych zewnętrznymi źródłami światła przez szkło).
SPECYFICZNE DLA APPLESEED</translation>
    </message>
    <message>
      <location filename="../../texture.py" line="84"/>
      <source>Image(s)</source>
      <translation>Obraz(y)</translation>
    </message>
    <message>
      <location filename="../../texture.py" line="85"/>
      <source>Mapping</source>
      <translation>Odwzorowanie</translation>
    </message>
    <message>
      <location filename="../../texture.py" line="91"/>
      <source>Texture Image File</source>
      <translation>Plik z obrazem tekstury</translation>
    </message>
    <message>
      <location filename="../../texture.py" line="97"/>
      <source>UV rotation (in degrees)</source>
      <translation>Obrót UV (w stopniach).</translation>
    </message>
    <message>
      <location filename="../../texture.py" line="103"/>
      <source>UV scale</source>
      <translation>Skala UV</translation>
    </message>
    <message>
      <location filename="../../texture.py" line="109"/>
      <source>UV translation - U component</source>
      <translation>Przesunięcie UV — składnik U</translation>
    </message>
    <message>
      <location filename="../../texture.py" line="115"/>
      <source>UV translation - V component</source>
      <translation>Przesunięcie UV — składnik V</translation>
    </message>
    <message>
      <location filename="../../view.py" line="53"/>
      <source>The source object of this view</source>
      <translation>Obiekt źródłowy dla danego widoku</translation>
    </message>
    <message>
      <location filename="../../view.py" line="62"/>
      <source>The material of this view (optional, should preferably be set in the source object)</source>
      <translation>Materiał dla tego widoku (opcjonalne, najlepiej ustawić w obiekcie źródłowym).</translation>
    </message>
    <message>
      <location filename="../../view.py" line="73"/>
      <source>The rendering output of this view (computed)</source>
      <translation>Wynik renderowania tego widoku (wyliczony)</translation>
    </message>
    <message>
      <location filename="../../view.py" line="82"/>
      <source>The type of UV projection to use for textures</source>
      <translation>Typ projekcji UV używany dla tekstur</translation>
    </message>
    <message>
      <location filename="../../view.py" line="92"/>
      <source>Enable normal auto smoothing</source>
      <translation>Włącz normalne autowygładzanie</translation>
    </message>
    <message>
      <location filename="../../view.py" line="102"/>
      <source>Edges where an angle between the faces is smaller than specified in this Angle field will be smoothed, when auto smooth is enabled</source>
      <translation>Krawędzie, w których kąt między ścianami jest mniejszy niż określony w polu Kąt, zostaną wygładzone, gdy włączona jest funkcja automatycznego wygładzania</translation>
    </message>
    <message>
      <location filename="../../view.py" line="114"/>
      <source>Cycles only - Enable object to cast shadow caustics.
WARNING: require Cycles version &gt;= 4.0.3 (otherwise may crash).</source>
      <translation>Tylko Cycles — Umożliwia obiektowi rzucanie efektów kaustyki cienia.
OSTRZEŻENIE: wymaga wersji Cycles minimum 4.0.3 (w przeciwnym razie może wystąpić awaria).</translation>
    </message>
    <message>
      <location filename="../../view.py" line="128"/>
      <source>Cycles only - Enable object to receive shadow caustics.
WARNING: require Cycles version &gt;= 4.0.3 (otherwise may crash).</source>
      <translation>Tylko Cycles — umożliwia obiektowi odbieranie efektów kaustyki cienia.
OSTRZEŻENIE: wymaga wersji Cycles minimum 4.0.3 (w przeciwnym razie może wystąpić awaria).</translation>
    </message>
    <message>
      <location filename="../../view.py" line="142"/>
      <source>Cycles only - Enable light to generate caustics
WARNING: require Cycles version &gt;= 4.0.3 (otherwise may crash).</source>
      <translation>Tylko Cycles — Włącz światło do generowania kaustyki
OSTRZEŻENIE: wymaga wersji Cycles minimum 4.0.3 (w przeciwnym razie może wystąpić awaria).</translation>
    </message>
    <message>
      <location filename="../../view.py" line="156"/>
      <source>Force meshing even when &apos;skip_meshing&apos; is activated.</source>
      <translation>Wymusza tworzenie siatki nawet po aktywowaniu opcji "skip_meshing".</translation>
    </message>
  </context>
  <context>
    <name>MaterialMaterialXImportCommand</name>
    <message>
      <location filename="../../commands.py" line="406"/>
      <source>Import MaterialX file</source>
      <translation>Importuj plik MaterialX</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="410"/>
      <source>Import a material from MaterialX file</source>
      <translation>Importuje materiał z pliku MaterialX.</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="445"/>
      <source>GPUOpen Material Library</source>
      <translation>Biblioteka materiałów GPUOpen</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="449"/>
      <source>Open AMD GPUOpen Material Library</source>
      <translation>Otwórz bibliotekę materiałów AMD GPUOpen</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="473"/>
      <source>AmbientCG Material Library</source>
      <translation>Biblioteka materiałów AmbientCG</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="477"/>
      <source>Open AmbientCG Material Library</source>
      <translation>Otwórz bibliotekę materiałów AmbientCG</translation>
    </message>
  </context>
  <context>
    <name>MaterialSettingsTaskPanel</name>
    <message>
      <location filename="../../taskpanels.py" line="509"/>
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
      <location filename="../../base.py" line="667"/>
      <source>[Point at] Please select target (on geometry)</source>
      <translation>[Skieruj na] Proszę wybrać cel (na geometrii)</translation>
    </message>
    <message>
      <location filename="../../base.py" line="695"/>
      <source>[Point at] Target outside geometry -- Aborting</source>
      <translation>[Skieruj na] Cel na zewnątrz geometrii -- Przerywanie</translation>
    </message>
    <message>
      <location filename="../../base.py" line="706"/>
      <source>[Point at] Now pointing at ({0.x}, {0.y}, {0.z})</source>
      <translation>[Skieruj na] Teraz skierowano na ({0.x}, {0.y}, {0.z})</translation>
    </message>
    <message>
      <location filename="../../camera.py" line="167"/>
      <source>Set GUI to this camera</source>
      <translation>Ustaw GUI na tę kamerę</translation>
    </message>
    <message>
      <location filename="../../camera.py" line="171"/>
      <source>Set this camera to GUI</source>
      <translation>Ustaw tę kamerę na GUI</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="160"/>
      <source>[Render] Unable to find a valid project in selection or document</source>
      <translation>[Render] Nie można znaleźć prawidłowego projektu w zaznaczeniu lub dokumencie</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="384"/>
      <source>Create material</source>
      <translation>Utwórz materiał</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="549"/>
      <source>Empty Selection</source>
      <translation>Wybór jest pusty</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="550"/>
      <source>Please select object(s) before applying material.</source>
      <translation>Proszę, wybierz obiekt(y) przed przypisaniem materiału.</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="564"/>
      <source>No Material</source>
      <translation>Brak materiału</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="565"/>
      <source>No Material in document. Please create a Material before applying.</source>
      <translation>Brak materiału w dokumencie. Proszę, stwórz materiał przed zastosowaniem.</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="589"/>
      <source>Material Applier</source>
      <translation>Aplikator materiałów</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="590"/>
      <source>Choose Material to apply to selection:</source>
      <translation>Wybierz materiał, aby zastosować go do zaznaczenia:</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="617"/>
      <source>[Render][Material] Cannot apply Material to object &apos;%s&apos;: object&apos;s Material property is of wrong type</source>
      <translation>[Render][Material] Nie można zastosować materiału do obiektu "%s": właściwość Materiał obiektu jest niewłaściwego typu.</translation>
    </message>
    <message>
      <location filename="../../material.py" line="286"/>
      <source>Edit Render Settings</source>
      <translation>Edytuj ustawienia renderowania</translation>
    </message>
    <message>
      <location filename="../../material.py" line="297"/>
      <source>Edit General Settings</source>
      <translation>Ustawienia ogólne</translation>
    </message>
    <message>
      <location filename="../../material.py" line="307"/>
      <source>Add Texture</source>
      <translation>Dodaj teksturę</translation>
    </message>
    <message>
      <location filename="../../material.py" line="474"/>
      <source>Invalid image index (&apos;{}&apos;) in texture &apos;{}&apos; -- Skipping</source>
      <translation>Nieprawidłowy indeks obrazu ("{}") w teksturze "{}" — Pomijanie</translation>
    </message>
    <message>
      <location filename="../../material.py" line="520"/>
      <source>Invalid image path (&apos;{}&apos;) in texture &apos;{}&apos; -- Skipping</source>
      <translation>Nieprawidłowa ścieżka obrazu ("{}") w teksturze "{}" — Pomijanie</translation>
    </message>
    <message>
      <location filename="../../material.py" line="535"/>
      <source>Missing primary image (index 0) in texture &apos;{}&apos; -- Skipping texture</source>
      <translation>Brakujący obraz główny (indeks 0) w teksturze "{}" — Pomijanie tekstury</translation>
    </message>
    <message>
      <location filename="../../material.py" line="547"/>
      <source>No valid primary image (index 0) in texture &apos;{}&apos; -- Skipping texture</source>
      <translation>Brak prawidłowego obrazu głównego (indeks 0) w teksturze "{}" — Pomijanie tekstury</translation>
    </message>
    <message>
      <location filename="../../material.py" line="584"/>
      <source>Invalid attribute &apos;{}&apos; in texture &apos;{}&apos; -- Skipping attribute</source>
      <translation>Nieprawidłowy atrybut "{}" w teksturze "{}" — Pomijanie atrybutu</translation>
    </message>
    <message>
      <location filename="../../material.py" line="596"/>
      <source>Invalid type for attribute &apos;{}&apos; in texture &apos;{}&apos;: Cannot convert &apos;{}&apos; to &apos;{}&apos; -- Skipping attribute</source>
      <translation>Nieprawidłowy typ atrybutu "{}" w teksturze "{}": Nie można przekonwertować "{}" na "{}" — Pomijanie atrybutu.</translation>
    </message>
    <message>
      <location filename="../../material.py" line="654"/>
      <source>Invalid syntax for texture &apos;{}&apos;: No valid arguments in statement (&apos;{}&apos;) -- Skipping value</source>
      <translation>Nieprawidłowa składnia dla tekstury "{}": Brak prawidłowych argumentów w instrukcji ("{}") — Pomijanie wartości.</translation>
    </message>
    <message>
      <location filename="../../material.py" line="667"/>
      <source>Invalid syntax for attribute &apos;{}&apos; in texture &apos;{}&apos;: Expecting &apos;Texture(&quot;&lt;texname&gt;&quot;, &lt;texindex&gt;)&apos;, got &apos;{}&apos; instead -- Skipping value</source>
      <translation>Nieprawidłowa składnia atrybutu "{}" w teksturze "{}": Oczekiwano "Texture("&lt;texname>", &lt;texindex>)", zamiast tego otrzymano "{}" — Pomijanie wartości</translation>
    </message>
    <message>
      <location filename="../../material.py" line="680"/>
      <source>Invalid syntax for attribute &apos;{}&apos; in texture &apos;{}&apos;: Reference to texture should be a tuple (&apos;&lt;texture&gt;&apos;, &lt;index&gt;, [&lt;scalar&gt;]) -- Skipping value</source>
      <translation>Nieprawidłowa składnia atrybutu "{}" w teksturze "{}": Odwołanie do tekstury powinno być krotką ("&lt;tekstura>", &lt;indeks>, [&lt;skala>]) — Pomijanie wartości</translation>
    </message>
    <message>
      <location filename="../../material.py" line="704"/>
      <source>Invalid syntax for attribute &apos;{}&apos; in texture &apos;{}&apos;: Scalar should be a float -- Skipping value</source>
      <translation>Nieprawidłowa składnia atrybutu "{}" w teksturze "{}": Scalar powinien być typu float — Pomijanie wartości</translation>
    </message>
    <message>
      <location filename="../../project.py" line="341"/>
      <source>[Render] Unable to create rendering view for object &apos;{o}&apos;: unhandled object type</source>
      <translation>[Render] Nie można utworzyć widoku renderowania dla obiektu &apos;{o}&apos;: nieobsługiwany typ obiektu</translation>
    </message>
    <message>
      <location filename="../../project.py" line="424"/>
      <source>[Render][Project] CRITICAL ERROR - Negative or zero value(s) for Render Height and/or Render Width: cannot render. Aborting...
</source>
      <translation>[Render][Project] BŁĄD KRYTYCZNY — Ujemne lub zerowe wartości dla wysokości renderowania i/lub szerokości renderowania: nie można renderować. Przerwano ...
</translation>
    </message>
    <message>
      <location filename="../../project.py" line="468"/>
      <source>Renderer not found (&apos;{}&apos;) </source>
      <translation>Renderer ("{}") nie został znaleziony </translation>
    </message>
    <message>
      <location filename="../../project.py" line="506"/>
      <source>Empty rendering command</source>
      <translation>Polecenie pustego renderowania</translation>
    </message>
    <message>
      <location filename="../../project.py" line="569"/>
      <source>Template not found (&apos;{}&apos;)</source>
      <translation>Nie znaleziono szablonu (&apos;{}&apos;)</translation>
    </message>
    <message>
      <location filename="../../project.py" line="728"/>
      <source>Cannot render project:</source>
      <translation>Nie można wyrenderować projektu:</translation>
    </message>
    <message>
      <location filename="../../project.py" line="739"/>
      <source>Render</source>
      <translation>Renderowanie</translation>
    </message>
    <message>
      <location filename="../../project.py" line="744"/>
      <source>Change template</source>
      <translation>Zmień szablon</translation>
    </message>
    <message>
      <location filename="../../project.py" line="763"/>
      <source>Warning: Deleting Non-Empty Project</source>
      <translation>Uwaga: Usuwa nie pusty projekt</translation>
    </message>
    <message>
      <location filename="../../project.py" line="764"/>
      <source>Project is not empty. All its contents will be deleted too.

Are you sure you want to continue?</source>
      <translation>Projekt nie jest pusty. Cała jego zawartość również zostanie usunięta.

Jesteś pewien, że chcesz kontynuować?</translation>
    </message>
    <message>
      <location filename="../../project.py" line="793"/>
      <source>[Render] Cannot render: {e}</source>
      <translation>[Render] Nie może renderować: {e}</translation>
    </message>
    <message>
      <location filename="../../project.py" line="838"/>
      <source>Select template</source>
      <translation>Wybierz szablon</translation>
    </message>
    <message>
      <location filename="../../rdrhandler.py" line="338"/>
      <source>Exporting</source>
      <translation>Eksportowanie</translation>
    </message>
    <message>
      <location filename="../../rdrhandler.py" line="825"/>
      <source>[Render] Error: Renderer &apos;%s&apos; not found</source>
      <translation>[Render] Błąd: silnik renderowania "%s" nie został znaleziony.</translation>
    </message>
    <message>
      <location filename="../../renderables.py" line="269"/>
      <source>Nothing to render</source>
      <translation>Nie ma nic do renderowania</translation>
    </message>
    <message>
      <location filename="../../renderables.py" line="278"/>
      <source>Cannot find mesh data</source>
      <translation>Nie można znaleźć danych siatki</translation>
    </message>
    <message>
      <location filename="../../renderables.py" line="285"/>
      <source>Mesh topology is empty</source>
      <translation>Topologia siatki jest pusta</translation>
    </message>
    <message>
      <location filename="../../renderables.py" line="647"/>
      <source>Incomplete multimaterial (missing {m})</source>
      <translation>Nie kompletne wszystkie materiały (brakuje {m})</translation>
    </message>
    <message>
      <location filename="../../taskpanels.py" line="275"/>
      <source>Use object color</source>
      <translation>Użyj koloru obiektu</translation>
    </message>
    <message>
      <location filename="../../taskpanels.py" line="281"/>
      <source>Use constant color</source>
      <translation>Użyj stałego koloru</translation>
    </message>
    <message>
      <location filename="../../taskpanels.py" line="471"/>
      <location filename="../../taskpanels.py" line="389"/>
      <location filename="../../taskpanels.py" line="294"/>
      <source>Use texture</source>
      <translation>Użyj teksturę</translation>
    </message>
    <message>
      <location filename="../../taskpanels.py" line="373"/>
      <source>Use constant value</source>
      <translation>Użyj stałej wartości</translation>
    </message>
    <message>
      <location filename="../../taskpanels.py" line="467"/>
      <source>Don&apos;t use</source>
      <translation>Nie używaj</translation>
    </message>
    <message>
      <location filename="../../taskpanels.py" line="782"/>
      <source>Factor:</source>
      <translation>Współczynnik:</translation>
    </message>
    <message>
      <location filename="../../texture.py" line="196"/>
      <source>Add Image Entry</source>
      <translation>Dodaj pozycję obrazu</translation>
    </message>
    <message>
      <location filename="../../texture.py" line="199"/>
      <source>Remove Image Entry</source>
      <translation>Usuń pozycję obrazu</translation>
    </message>
    <message>
      <location filename="../../texture.py" line="215"/>
      <source>Unallowed Image Removal</source>
      <translation>Usuń niedozwolony obraz</translation>
    </message>
    <message>
      <location filename="../../texture.py" line="216"/>
      <source>Unallowed removal: not enough images in texture (&lt;2)!
</source>
      <translation>Niedozwolone usunięcie: za mało obrazów w teksturze (&lt;2)!
</translation>
    </message>
    <message>
      <location filename="../../texture.py" line="220"/>
      <source>Leaving less than 1 image in texture is not allowed...</source>
      <translation>Pozostawienie mniej niż jednego obrazu w teksturze jest niedozwolone ...</translation>
    </message>
    <message>
      <location filename="../../texture.py" line="233"/>
      <source>Texture Image Removal</source>
      <translation>Usuń teksturę obrazu</translation>
    </message>
    <message>
      <location filename="../../texture.py" line="234"/>
      <source>Choose Image to remove:</source>
      <translation>Wybierz Obraz do usunięcia:</translation>
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
      <translation>Wymuś obliczenia UVMap</translation>
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
      <translation>Ustawienia renderowania</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="20"/>
      <source>Plugins</source>
      <translation>Wtyczki</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="29"/>
      <source>Enable MaterialX features</source>
      <translation>Włącz funkcje MaterialX</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="39"/>
      <source>Disable GUI embedding</source>
      <translation>Wyłącz osadzanie GUI</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="84"/>
      <source>Reset Plugins Environment</source>
      <extracomment>Reload all dependencies needed by plugins</extracomment>
      <translation>Resetowanie środowiska wtyczek</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="94"/>
      <location filename="../ui/RenderSettings.ui" line="100"/>
      <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Advanced and Debug parameters&lt;/p&gt;&lt;p&gt;&lt;span style=&quot; font-weight:600;&quot;&gt;WARNING&lt;/span&gt; - Do not modify if you don&apos;t know what you do - Unexpected behaviours may result...&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
      <translation>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Parametry zaawansowane i debugowania&lt;/p&gt;&lt;p&gt;&lt;span style=&quot; font-weight:600;&quot;&gt;UWAGA&lt;/span&gt; - Nie modyfikuj, jeśli nie wiesz, co robisz - może to spowodować nieoczekiwane skutki...&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="97"/>
      <source>Advanced and Debug parameters WARNING - Do not modify if you don&apos;t know what you do - Unexpected behaviours may result...</source>
      <translation>Parametry zaawansowane i debugowania OSTRZEŻENIE - Nie modyfikuj, jeśli nie wiesz, co robisz - może to spowodować nieoczekiwane zachowanie...</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="106"/>
      <source>Advanced &amp;&amp; Debug</source>
      <translation>Zaawansowane i debugowanie</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="118"/>
      <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Enable multiprocessing &lt;span style=&quot; font-size:8pt; font-style:italic;&quot;&gt;(experimental)&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
      <translation>&lt;html>&lt;head/>&lt;body>&lt;p>Włącz przetwarzanie wieloprocesowe &lt;span style=" font-size:8pt; font-style:italic;">(funkcja eksperymentalna)&lt;/span>&lt;/p>&lt;/body>&lt;/html></translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="183"/>
      <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Multiprocessing threshold &lt;span style=&quot; font-size:8pt; font-style:italic;&quot;&gt;(number of points)&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
      <translation>&lt;html>&lt;head/>&lt;body>&lt;p>Próg przetwarzania wieloprocesowego &lt;span style=" font-size:8pt; font-style:italic;">(liczba punktów)&lt;/span>&lt;/p>&lt;/body>&lt;/html></translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="203"/>
      <source>Do not modify ShapeColor when assigning material</source>
      <translation>Nie modyfikuj koloru kształtu podczas przypisywania materiału</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="213"/>
      <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Use FreeCAD materials directory &lt;span style=&quot; font-size:8pt; font-style:italic;&quot;&gt;(not recommended)&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
      <translation>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Użyj katalogu materiałów FreeCAD &lt;span style=&quot; font-size:8pt; font-style:italic;&quot;&gt;(nie zalecane)&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="220"/>
      <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Enable Numpy if available &lt;span style=&quot; font-size:8pt; font-style:italic;&quot;&gt;(experimental)&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
      <translation>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Włącz Numpy, jeśli jest dostępny &lt;span style=&quot; font-size:8pt; font-style:italic;&quot;&gt;(eksperymentalne)&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="246"/>
      <source>Clear report view before each run</source>
      <translation>Wyczyść okno Widoku raportu przed każdym uruchomieniem</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="253"/>
      <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Dry run &lt;span style=&quot; font-size:8pt; font-style:italic;&quot;&gt;(won&apos;t run renderer - debug purpose only)&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
      <translation>&lt;html>&lt;head/>&lt;body>&lt;p>Jałowy przebieg &lt;span style=" font-size:8pt; font-style:italic;">(nie uruchomi renderera — służy tylko do debugowania)&lt;/span>&lt;/p>&lt;/body>&lt;/html></translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="286"/>
      <source>Use UUID for exported file names</source>
      <translation>Użyj UUID w nazwach eksportowanych plików</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="299"/>
      <source>LuxRender (deprecated)</source>
      <translation>LuxRender (przestarzałe)</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="305"/>
      <location filename="../ui/RenderSettings.ui" line="528"/>
      <source>Optional parameters to be passed to Luxrender when rendering</source>
      <translation>Opcjonalne parametry przekazywane do Luxrender podczas renderowania</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="327"/>
      <source>LuxRender UI path</source>
      <translation>Ścieżka do LuxRender UI</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="334"/>
      <location filename="../ui/RenderSettings.ui" line="398"/>
      <source>The path to the luxrender UI executable</source>
      <translation>Ścieżka do plików wykonywalnych Luxrender UI</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="353"/>
      <location filename="../ui/RenderSettings.ui" line="453"/>
      <location filename="../ui/RenderSettings.ui" line="630"/>
      <location filename="../ui/RenderSettings.ui" line="828"/>
      <location filename="../ui/RenderSettings.ui" line="918"/>
      <location filename="../ui/RenderSettings.ui" line="979"/>
      <location filename="../ui/RenderSettings.ui" line="1095"/>
      <source>Render parameters</source>
      <translation>Parametry renderowania</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="363"/>
      <source>LuxRender command (cli) path</source>
      <translation>Ścieżka poleceń LuxRender (CLI)</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="370"/>
      <location filename="../ui/RenderSettings.ui" line="414"/>
      <source>The path to the Luxrender console (luxconsole) executable</source>
      <translation>Ścieżka do pliku wykonywalnego Luxrender'a (albo luxconsole)</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="433"/>
      <source>LuxCore command (cli) path</source>
      <translation>Ścieżka poleceń LuxCore (CLI)</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="443"/>
      <source>LuxCore UI path</source>
      <translation>Ścieżka LuxCore UI</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="521"/>
      <source>LuxCore engine</source>
      <translation>Silnik LuxCore</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="547"/>
      <location filename="../ui/RenderSettings.ui" line="560"/>
      <location filename="../ui/RenderSettings.ui" line="650"/>
      <location filename="../ui/RenderSettings.ui" line="861"/>
      <location filename="../ui/RenderSettings.ui" line="874"/>
      <location filename="../ui/RenderSettings.ui" line="954"/>
      <location filename="../ui/RenderSettings.ui" line="1028"/>
      <location filename="../ui/RenderSettings.ui" line="1102"/>
      <source>Test</source>
      <translation>Test</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="604"/>
      <source>OspStudio executable path</source>
      <translation>Ścieżka do pliku wykonywalnego OspStudio</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="669"/>
      <source>General</source>
      <translation>Ogólne</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="678"/>
      <source>Default render width</source>
      <translation>Standardowa szerokość renderowania</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="732"/>
      <source>Prefix</source>
      <translation>Przedrostek</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="742"/>
      <source>Default render height</source>
      <translation>Standardowa wysokość renderowania</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="749"/>
      <source>A prefix that can be added before the renderer executable. This is useful, for example, to add environment variable or run the renderer inside a GPU switcher such as primusrun or optirun on linux</source>
      <translation>Prefiks, który można dodać przed plikiem wykonywalnym renderera. Jest to przydatne, na przykład, aby dodać zmienną środowiskową lub uruchomić z przełącznikiem GPU, takim jak primusrun lub optirun w systemie Linux</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="783"/>
      <source>Appleseed Studio path</source>
      <translation>Ścieżka do Appleseed Studio</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="790"/>
      <source>The path to the Appleseed cli executable</source>
      <translation>Ścieżka do pliku wykonywalnego wiersza poleceń Appleseed</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="806"/>
      <source>Optional rendering parameters to be passed to the Appleseed executable</source>
      <translation>Opcjonalne parametry renderowania przekazywane do pliku wykonywalnego Appleseed</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="835"/>
      <source>The path to the Appleseed studio executable (optional)</source>
      <translation>Ścieżka do pliku wykonywalnego Appleseed Studio (opcjonalnie)</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="854"/>
      <source>Appleseed command (cli) path</source>
      <translation>Ścieżka do pliku Appleseed (CLI)</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="899"/>
      <source>The path to the Pov-Ray executable</source>
      <translation>Ścieżka do pliku wykonywalnego Pov-Ray</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="925"/>
      <source>Optional parameters to be passed to Pov-Ray when rendering</source>
      <translation>Opcjonalne parametry przekazywane do Pov-Ray podczas renderowania</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="947"/>
      <source>PovRay executable path</source>
      <translation>Ścieżka do pliku wykonywalnego PovRay</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="1002"/>
      <source>Pbrt executable path</source>
      <translation>Ścieżka pliku wykonywalnego Pbrt</translation>
    </message>
    <message>
      <location filename="../ui/RenderSettings.ui" line="1072"/>
      <source>Cycles executable (standalone) path</source>
      <translation>Ścieżka do pliku wykonywalnego Cycles</translation>
    </message>
  </context>
  <context>
    <name>Render_AreaLight</name>
    <message>
      <location filename="../../commands.py" line="266"/>
      <source>Area Light</source>
      <translation>Powierzchnia światła</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="267"/>
      <source>Create an Area Light object</source>
      <translation>Utwórz obiekt światła obszarowego</translation>
    </message>
  </context>
  <context>
    <name>Render_Camera</name>
    <message>
      <location filename="../../commands.py" line="221"/>
      <source>Camera</source>
      <translation>Kamera</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="222"/>
      <source>Create a Camera object from the current camera position</source>
      <translation>Tworzy ujęcie widoku obiektu z obecnej pozycji kamery</translation>
    </message>
  </context>
  <context>
    <name>Render_DistantLight</name>
    <message>
      <location filename="../../commands.py" line="334"/>
      <source>Distant Light</source>
      <translation>Światło z oddali</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="337"/>
      <source>Create an Distant Light object</source>
      <translation>Utwórz obiekt światła z oddali</translation>
    </message>
  </context>
  <context>
    <name>Render_Help</name>
    <message>
      <location filename="../../commands.py" line="664"/>
      <source>Help</source>
      <translation>Pomoc</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="665"/>
      <source>Open Render help</source>
      <translation>Otwórz pomoc środowiska Render</translation>
    </message>
  </context>
  <context>
    <name>Render_ImageLight</name>
    <message>
      <location filename="../../commands.py" line="312"/>
      <source>Image Light</source>
      <translation>Światło obrazu</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="313"/>
      <source>Create an Image Light object</source>
      <translation>Utwórz obiekt światła obrazu</translation>
    </message>
  </context>
  <context>
    <name>Render_Libraries</name>
    <message>
      <location filename="../../commands.py" line="794"/>
      <source>Libraries</source>
      <translation>Biblioteki</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="795"/>
      <source>Download from material libraries</source>
      <translation>Pobierz z bibliotek materiałów</translation>
    </message>
  </context>
  <context>
    <name>Render_Lights</name>
    <message>
      <location filename="../../commands.py" line="772"/>
      <source>Lights</source>
      <translation>Światła</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="773"/>
      <source>Create a Light</source>
      <translation>Utwórz światło</translation>
    </message>
  </context>
  <context>
    <name>Render_MaterialApplier</name>
    <message>
      <location filename="../../commands.py" line="531"/>
      <source>Apply Material</source>
      <translation>Zastosuj materiał</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="534"/>
      <source>Apply a Material to selection</source>
      <translation>Zastosuje materiał do zaznaczonych obiektów</translation>
    </message>
  </context>
  <context>
    <name>Render_MaterialCreator</name>
    <message>
      <location filename="../../commands.py" line="363"/>
      <source>Internal Material Library</source>
      <translation>Wewnętrzna biblioteka materiałów</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="367"/>
      <source>Create Material</source>
      <translation>Utwórz materiał</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="372"/>
      <source>Create a new Material in current document from internal library</source>
      <translation>Tworzy nowy materiał w bieżącym dokumencie z wewnętrznej biblioteki.</translation>
    </message>
  </context>
  <context>
    <name>Render_MaterialRenderSettings</name>
    <message>
      <location filename="../../commands.py" line="501"/>
      <source>Edit Material Render Settings</source>
      <translation>Edytuj ustawienia renderowania materiałów</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="505"/>
      <source>Edit rendering parameters of the selected Material</source>
      <translation>Edytuj parametry renderowania wybranego materiału</translation>
    </message>
  </context>
  <context>
    <name>Render_Materials</name>
    <message>
      <location filename="../../commands.py" line="782"/>
      <source>Materials</source>
      <translation>Materiały</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="783"/>
      <source>Manage Materials</source>
      <translation>Zarządzaj materiałami</translation>
    </message>
  </context>
  <context>
    <name>Render_PointLight</name>
    <message>
      <location filename="../../commands.py" line="244"/>
      <source>Point Light</source>
      <translation>Światło punktowe</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="245"/>
      <source>Create a Point Light object</source>
      <translation>Utwórz obiekt światła punktowego</translation>
    </message>
  </context>
  <context>
    <name>Render_Projects</name>
    <message>
      <location filename="../../commands.py" line="94"/>
      <location filename="../../commands.py" line="88"/>
      <source>{} Project</source>
      <translation>Projekt {}</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="95"/>
      <location filename="../../commands.py" line="89"/>
      <source>Create a {} project</source>
      <translation>Utwórz projekt {}</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="759"/>
      <source>Projects</source>
      <translation>Projekty</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="760"/>
      <source>Create a Rendering Project</source>
      <translation>Utwórz projekt renderowania</translation>
    </message>
  </context>
  <context>
    <name>Render_Render</name>
    <message>
      <location filename="../../commands.py" line="183"/>
      <source>Render project</source>
      <translation>Projekt renderowania</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="184"/>
      <source>Perform the rendering of a selected project or the default project</source>
      <translation>Wykonuje renderowanie wybranego projektu lub projektu domyślnego.</translation>
    </message>
  </context>
  <context>
    <name>Render_Settings</name>
    <message>
      <location filename="../../commands.py" line="687"/>
      <source>Render settings</source>
      <translation>Ustawienia dla Render</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="690"/>
      <source>Open Render workbench settings</source>
      <translation>Otwórz konfigurację środowiska pracy Render</translation>
    </message>
  </context>
  <context>
    <name>Render_SunskyLight</name>
    <message>
      <location filename="../../commands.py" line="288"/>
      <source>Sunsky Light</source>
      <translation>Światło słoneczne</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="291"/>
      <source>Create a Sunsky Light object</source>
      <translation>Utwórz obiekt światła słonecznego</translation>
    </message>
  </context>
  <context>
    <name>Render_View</name>
    <message>
      <location filename="../../commands.py" line="129"/>
      <source>Rendering View</source>
      <translation>Widok renderowania</translation>
    </message>
    <message>
      <location filename="../../commands.py" line="130"/>
      <source>Create a Rendering View of the selected object(s) in the selected project or the default project</source>
      <translation>Utwórz widok renderowania wybranych obiektów w wybranym projekcie lub projekcie domyślnym.</translation>
    </message>
  </context>
  <context>
    <name>Workbench</name>
    <message>
      <location filename="../../../InitGui.py" line="42"/>
      <source>The Render workbench is a modern replacement for the Raytracing workbench</source>
      <translation>Środowisko pracy Render jest nowoczesnym zamiennikiem środowiska pracy Raytracing</translation>
    </message>
    <message>
      <location filename="../../../InitGui.py" line="117"/>
      <source>Render</source>
      <translation>Renderowanie</translation>
    </message>
    <message>
      <location filename="../../../InitGui.py" line="120"/>
      <source>&amp;Render</source>
      <translation>&amp;Renderuj</translation>
    </message>
    <message>
      <location filename="../../../InitGui.py" line="124"/>
      <source>Loading Render module... done</source>
      <translation>Ładowanie modułu Render ... wykonane</translation>
    </message>
  </context>
</TS>
