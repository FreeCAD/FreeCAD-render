<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="fr" sourcelanguage="en_US">
<context>
    <name>App::Property</name>
    <message>
        <location filename="../../camera.py" line="91"/>
        <source>Type of projection: Perspective/Orthographic</source>
        <translation>Type de projection : perspective/orthographique</translation>
    </message>
    <message>
        <location filename="../../camera.py" line="97"/>
        <source>(See Coin documentation)</source>
        <translation>(Voir la documentation de Coin)</translation>
    </message>
    <message>
        <location filename="../../camera.py" line="105"/>
        <source>Ratio width/height of the camera.</source>
        <translation>Ratio largeur/hauteur pour la caméra</translation>
    </message>
    <message>
        <location filename="../../camera.py" line="111"/>
        <source>Near distance, for clipping</source>
        <translation>Distance proche, pour l&apos;écrêtage</translation>
    </message>
    <message>
        <location filename="../../camera.py" line="117"/>
        <source>Far distance, for clipping</source>
        <translation>Distance lointaine, pour l&apos;écrêtage</translation>
    </message>
    <message>
        <location filename="../../camera.py" line="123"/>
        <source>Focal distance</source>
        <translation>Distance focale</translation>
    </message>
    <message>
        <location filename="../../camera.py" line="131"/>
        <source>Height, for orthographic camera</source>
        <translation>Hauteur pour la caméra orthographique</translation>
    </message>
    <message>
        <location filename="../../camera.py" line="143"/>
        <source>Height angle, for perspective camera, in degrees. Important: This value will be sent as &apos;Field of View&apos; to the renderers. Please note it is a *vertical* field-of-view.</source>
        <translation>Angle de hauteur pour la caméra en perspective, en degrés. Important : cette valeur sera envoyée en tant que &quot;champ de vision&quot; aux moteurs de rendu. Noter qu&apos;il s&apos;agit d&apos;un champ de vision &quot;vertical&quot;.</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="660"/>
        <source>The Material for this object</source>
        <translation>Le Matériau pour cet objet</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="98"/>
        <source>Location of light</source>
        <translation>Position de la lumière</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="104"/>
        <location filename="../../lights.py" line="209"/>
        <location filename="../../lights.py" line="428"/>
        <source>Color of light</source>
        <translation>Couleur de la lumière</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="110"/>
        <location filename="../../lights.py" line="215"/>
        <location filename="../../lights.py" line="434"/>
        <source>Rendering power</source>
        <translation>Puissance de rendu</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="121"/>
        <source>Light representation radius.
Note: This parameter has no impact on rendering</source>
        <translation>Rayon de représentation de la lumière
Remarque : ce paramètre n&apos;a aucun impact sur le rendu.</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="197"/>
        <source>Size on U axis</source>
        <translation>Dimension sur l&apos;axe U</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="203"/>
        <source>Size on V axis</source>
        <translation>Dimension sur l&apos;axe V</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="221"/>
        <source>Area light transparency</source>
        <translation>Transparence de la lumière de la zone</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="278"/>
        <source>Direction of sun from observer&apos;s point of view -- (0,0,1) is zenith</source>
        <translation>La direction du soleil depuis le point de vue de l&apos;observateur. (0,0,1) est le zénith.</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="288"/>
        <source>Atmospheric haziness (turbidity can go from 2.0 to 30+. 2-6 are most useful for clear days)</source>
        <translation>Nébulosité atmosphérique (la turbidité peut aller de 2.0 à 30+. Les valeurs 2-6 sont les plus communes pour les jours clairs).</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="297"/>
        <source>Ground albedo = reflection coefficient of the ground</source>
        <translation>Albédo du sol = coefficient de réflexion du sol</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="306"/>
        <source>Factor to tune sun light intensity. Default at 1.0</source>
        <translation>Facteur permettant de régler l&apos;intensité de la lumière du soleil. Valeur par défaut : 1.0</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="317"/>
        <source>Factor to tune sky light intensity. Default at 1.0. WARNING: not supported by Ospray.</source>
        <translation>Facteur permettant d&apos;ajuster l&apos;intensité de la lumière du ciel. La valeur par défaut est de 1.0.
ATTENTION : ce n&apos;est pas pris en charge par Ospray.</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="327"/>
        <source>The model to use for sun &amp; sky (Cycles only)</source>
        <translation>Le modèle à utiliser pour le soleil et le ciel (cycles uniquement)</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="344"/>
        <source>The gain preset to use for sun &amp; sky (Luxcore only):
* &apos;Physical&apos; yields accurate real light power, needing tone mapping or camera advanced settings
* &apos;Mitigated&apos; allows to render without tone mapping
* &apos;Interior&apos; is intended for interior scenes (through glass...)
* &apos;Custom&apos; gives full control on gain value</source>
        <translation>Le préréglage de gain à utiliser pour le soleil et le ciel (Luxcore uniquement) :
* &quot; Physique &quot; permet d&apos;obtenir une puissance de lumière réelle précise. Cela nécessite une correspondance des tonalités ou des réglages avancés de la caméra.
* &quot; Atténué &quot; permet d&apos;effectuer le rendu sans correspondance des tonalités.
* &quot; Intérieur &quot; pour les scènes d&apos;intérieur (à travers une vitre...).
* &quot; Personnalisé &quot; donne un contrôle total sur la valeur du gain.</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="355"/>
        <source>The gain to use for sun &amp; sky when preset gain is set to &apos;Custom&apos; (Luxcore only)</source>
        <translation>Gain à utiliser pour le soleil et le ciel lorsque le gain prédéfini est réglé sur &quot;Personnalisé&quot; (Luxcore uniquement).</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="397"/>
        <source>Image file (included in document)</source>
        <translation>Fichier de l&apos;image (inclus dans le document)</translation>
    </message>
    <message>
        <location filename="../../lights.py" line="443"/>
        <source>Direction of light from light&apos;s point of view </source>
        <translation>Direction de la lumière du point de vue de la lumière </translation>
    </message>
    <message>
        <location filename="../../lights.py" line="455"/>
        <source>Apparent size of the light source, as an angle. Must be &gt; 0 for soft shadows.
Not all renderers support this parameter, please refer to your renderer&apos;s documentation.</source>
        <translation>Taille apparente de la source lumineuse, sous forme d&apos;angle. Doit être &gt; 0 pour des ombres douces.
Tous les moteurs de rendu ne prennent pas en charge ce paramètre. Référez-vous à la documentation de votre moteur de rendu.</translation>
    </message>
    <message>
        <location filename="../../project.py" line="76"/>
        <source>The name of the raytracing engine to use</source>
        <translation>Le nom du moteur de lancer de rayons à utiliser</translation>
    </message>
    <message>
        <location filename="../../project.py" line="85"/>
        <source>If true, the views will be updated on render only</source>
        <translation>Si vrai, les vues ne seront mises à jour que lors du rendu</translation>
    </message>
    <message>
        <location filename="../../project.py" line="95"/>
        <source>The template to be used by this rendering (use Project&apos;s context menu to modify)</source>
        <translation>Le modèle à utiliser pour ce rendu (utiliser le menu contextuel du projet pour le modifier)</translation>
    </message>
    <message>
        <location filename="../../project.py" line="104"/>
        <source>The width of the rendered image in pixels</source>
        <translation>La largeur de l&apos;image rendue en pixels</translation>
    </message>
    <message>
        <location filename="../../project.py" line="116"/>
        <source>The height of the rendered image in pixels</source>
        <translation>La hauteur de l&apos;image rendue en pixels</translation>
    </message>
    <message>
        <location filename="../../project.py" line="129"/>
        <source>If true, a default ground plane will be added to the scene</source>
        <translation>Si vrai, un plan de sol par défaut sera ajouté à la scène</translation>
    </message>
    <message>
        <location filename="../../project.py" line="135"/>
        <source>Z position for ground plane</source>
        <translation>Position Z pour le plan de sol</translation>
    </message>
    <message>
        <location filename="../../project.py" line="141"/>
        <source>Ground plane color</source>
        <translation>Couleur du plan de sol</translation>
    </message>
    <message>
        <location filename="../../project.py" line="147"/>
        <source>Ground plane size factor</source>
        <translation>Facteur de taille du plan de sol</translation>
    </message>
    <message>
        <location filename="../../project.py" line="155"/>
        <source>The image saved by this render</source>
        <translation>L&apos;image sauvegardée par ce rendu</translation>
    </message>
    <message>
        <location filename="../../project.py" line="165"/>
        <source>If true, the rendered image is opened in FreeCAD after the rendering is finished</source>
        <translation>Si vrai, l&apos;image rendue est ouverte dans FreeCAD après que le rendu est achevé</translation>
    </message>
    <message>
        <location filename="../../project.py" line="176"/>
        <source>Linear deflection for the mesher: The maximum linear deviation of a mesh section from the surface of the object.</source>
        <translation>Déflexion linéaire pour le mailleur: La déviation linéaire maximale pour une section de maillage à partir de la surface de l&apos;objet.</translation>
    </message>
    <message>
        <location filename="../../project.py" line="188"/>
        <source>Angular deflection for the mesher: The maximum angular deviation from one mesh section to the next, in radians. This setting is used when meshing curved surfaces.</source>
        <translation>Déflexion angulaire pour le mailleur: La déviation angulaire maximale d&apos;une section de maillage à la suivante, en radians. Ce paramètre est utilisé lors du maillage de surfaces courbes.</translation>
    </message>
    <message>
        <location filename="../../project.py" line="203"/>
        <source>Overweigh transparency in rendering (0=None (default), 10=Very high).When this parameter is set, low transparency ratios will be rendered more transparent. NB: This parameter affects only implicit materials (generated via Shape Appearance), not explicit materials (defined via Material property).</source>
        <translation>Surpondère la transparence lors du rendu (0=Aucun (défaut), 10=Très élevé). Quand ce paramètre est fixé, les ratios bas de transparence seront rendus plus transparents. NB: Ce paramètre n&apos;affecte que les matériaux implicites (générés avec l&apos;Apparence de forme), pas les matériaux explicites (définis via le paramètre Matériau).</translation>
    </message>
    <message>
        <location filename="../../project.py" line="212"/>
        <source>Execute in batch mode (True) or GUI interactive mode (False)</source>
        <translation>Exécuter en mode par lots (Vrai) ou en mode interactif de l&apos;interface graphique (Faux)</translation>
    </message>
    <message>
        <location filename="../../project.py" line="222"/>
        <source>Halt condition: number of samples per pixel (0 or negative = indefinite).</source>
        <translation>Condition d&apos;arrêt : nombre d&apos;échantillons par pixel (0 ou négatif = indéfini).</translation>
    </message>
    <message>
        <location filename="../../project.py" line="233"/>
        <source>Make renderer invoke denoiser. WARNING: may not work with all renderers - the renderer must have denoising capabilities.</source>
        <translation>Faire en sorte que le moteur de rendu lance le débruiteur.
ATTENTION : cela peut ne pas fonctionner avec tous les moteurs de rendu. Le moteur de rendu doit avoir des capacités de débruitage.</translation>
    </message>
    <message>
        <location filename="../../project.py" line="244"/>
        <source>Activate caustics in Appleseed (useful for interior scenes ligthened by external light sources through glass)
SPECIFIC TO APPLESEED</source>
        <translation>Activer les caustiques dans Appleseed (utile pour les scènes d&apos;intérieur éclairées par des sources de lumière externes à travers le verre)
Spécifique à Appleseed</translation>
    </message>
    <message>
        <location filename="../../texture.py" line="85"/>
        <source>Image(s)</source>
        <translation>Image(s)</translation>
    </message>
    <message>
        <location filename="../../texture.py" line="87"/>
        <source>Mapping</source>
        <translation>Correspondre</translation>
    </message>
    <message>
        <location filename="../../texture.py" line="91"/>
        <source>Texture Image File</source>
        <translation>Fichier d&apos;image de texture</translation>
    </message>
    <message>
        <location filename="../../texture.py" line="97"/>
        <source>UV rotation (in degrees)</source>
        <translation>Rotation des UV (en degrés)</translation>
    </message>
    <message>
        <location filename="../../texture.py" line="103"/>
        <source>UV scale</source>
        <translation>Échelle des UV</translation>
    </message>
    <message>
        <location filename="../../texture.py" line="109"/>
        <source>UV translation - U component</source>
        <translation>Traduction des UV - Composante U</translation>
    </message>
    <message>
        <location filename="../../texture.py" line="115"/>
        <source>UV translation - V component</source>
        <translation>Traduction des UV - Composante V</translation>
    </message>
    <message>
        <location filename="../../view.py" line="55"/>
        <source>The source object of this view</source>
        <translation>L&apos;objet source pour cette vue</translation>
    </message>
    <message>
        <location filename="../../view.py" line="66"/>
        <source>The material of this view (optional, should preferably be set in the source object)</source>
        <translation>Le matériau de cette vue (facultatif, il serait préférable de le défini dans l&apos;objet source)</translation>
    </message>
    <message>
        <location filename="../../view.py" line="75"/>
        <source>The rendering output of this view (computed)</source>
        <translation>Le rendu de cette vue (calculé)</translation>
    </message>
    <message>
        <location filename="../../view.py" line="85"/>
        <source>The type of UV projection to use for textures</source>
        <translation>Le type de projection UV à utiliser pour les textures</translation>
    </message>
    <message>
        <location filename="../../view.py" line="95"/>
        <source>Enable normal auto smoothing</source>
        <translation>Activer le lissage automatique normal</translation>
    </message>
    <message>
        <location filename="../../view.py" line="107"/>
        <source>Edges where an angle between the faces is smaller than specified in this Angle field will be smoothed, when auto smooth is enabled</source>
        <translation>Les arêtes dont l&apos;angle entre les faces est inférieur à celui spécifié dans le champ Angle seront lissées, lorsque la fonction de lissage automatique est activée.</translation>
    </message>
    <message>
        <location filename="../../view.py" line="159"/>
        <source>Force meshing even when &apos;skip_meshing&apos; is activated.</source>
        <translation>Forcer le maillage même lorsque &quot;pas de maillage&quot; est activé.</translation>
    </message>
</context>
<context>
    <name>MaterialMaterialXImportCommand</name>
    <message>
        <location filename="../../commands.py" line="461"/>
        <source>Import MaterialX file</source>
        <translation>Importer un fichier MaterialX</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="465"/>
        <source>Import a material from MaterialX file</source>
        <translation>Importer un matériau à partir d&apos;un fichier MaterialX</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="491"/>
        <source>GPUOpen Material Library</source>
        <translation>Bibliothèque de matériaux de GPUOpen</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="495"/>
        <source>Open AMD GPUOpen Material Library</source>
        <translation>Ouvrir la bibliothèque de matériaux de GPUOpen AMD</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="521"/>
        <source>AmbientCG Material Library</source>
        <translation>Bibliothèque de matériaux de AmbientCG</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="525"/>
        <source>Open AmbientCG Material Library</source>
        <translation>Ouvrir la bibliothèque de matériaux d&apos;AmbientCG</translation>
    </message>
</context>
<context>
    <name>MaterialSettingsTaskPanel</name>
    <message>
        <location filename="../../taskpanels.py" line="513"/>
        <source>&lt;None&gt;</source>
        <translation>&lt;Aucun&gt;</translation>
    </message>
</context>
<context>
    <name>Render</name>
    <message>
        <location filename="../../base.py" line="651"/>
        <source>Point at...</source>
        <translation>Pointer vers...</translation>
    </message>
    <message>
        <location filename="../../base.py" line="670"/>
        <source>[Point at] Please select target (on geometry)</source>
        <translation>[Pointer vers] Veuillez sélectionner la cible (sur la géométrie)</translation>
    </message>
    <message>
        <location filename="../../base.py" line="699"/>
        <source>[Point at] Target outside geometry -- Aborting</source>
        <translation>[Pointer vers] Cible en dehors de la géométrie -- Abandon</translation>
    </message>
    <message>
        <location filename="../../base.py" line="710"/>
        <source>[Point at] Now pointing at ({0.x}, {0.y}, {0.z})</source>
        <translation>[Pointer vers] Pointe maintenant vers ({0.x}, {0.y}, {0.z})</translation>
    </message>
    <message>
        <location filename="../../camera.py" line="169"/>
        <source>Set GUI to this camera</source>
        <translation>Régler l&apos;interface graphique sur cette caméra</translation>
    </message>
    <message>
        <location filename="../../camera.py" line="173"/>
        <source>Set this camera to GUI</source>
        <translation>Régler cette caméra sur l&apos;interface graphique</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="185"/>
        <source>[Render] Unable to find a valid project in selection or document</source>
        <translation>[Render] Impossible de trouver un projet valide dans la sélection ou le document</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="433"/>
        <source>Create material</source>
        <translation>Créer un matériau</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="599"/>
        <source>Empty Selection</source>
        <translation>Sélection Vide</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="603"/>
        <source>Please select object(s) before applying material.</source>
        <translation>Veuillez sélectionner un ou des objets avant d&apos;appliquer un matériau.</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="614"/>
        <source>No Material</source>
        <translation>Pas de Matériau</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="619"/>
        <source>No Material in document. Please create a Material before applying.</source>
        <translation>Pas de Matériau dans le document. Veuillez créer un Matériau avant d&apos;appliquer.</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="638"/>
        <source>Material Applier</source>
        <translation>Applicateur de Matériau</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="639"/>
        <source>Choose Material to apply to selection:</source>
        <translation>Choisir le matériau à appliquer à la sélection :</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="673"/>
        <source>[Render][Material] Cannot apply Material to object &apos;%s&apos;: object&apos;s Material property is of wrong type</source>
        <translation>[Render][Material] Impossible d&apos;appliquer un matériau à l&apos;objet &quot;%s&quot; : la propriété du matériau de l&apos;objet n&apos;est pas du bon type.</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="685"/>
        <source>[Render][Material] Cannot apply Material to object &apos;{obj.Label}&apos;: object&apos;s Material property does not accept provided material &apos;{material.Label}&apos;</source>
        <translation>[Render][Material] Impossible d&apos;appliquer un matériau à l&apos;objet &quot;{obj.Label}&quot; : la propriété du matériau de l&apos;objet n&apos;accepte pas le matériau fourni &quot;{material.Label}&quot;.</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="693"/>
        <source>[Render][Material] Object raises ValueError {err.args}</source>
        <translation>[Render][Material] L&apos;objet déclenche une erreur de valeur {err.args}.</translation>
    </message>
    <message>
        <location filename="../../material.py" line="286"/>
        <source>Edit Render Settings</source>
        <translation>Éditer les paramètres de Render</translation>
    </message>
    <message>
        <location filename="../../material.py" line="297"/>
        <source>Edit General Settings</source>
        <translation>Éditer les paramètres généraux</translation>
    </message>
    <message>
        <location filename="../../material.py" line="307"/>
        <source>Add Texture</source>
        <translation>Ajouter une texture</translation>
    </message>
    <message>
        <location filename="../../material.py" line="477"/>
        <source>Invalid image index (&apos;{}&apos;) in texture &apos;{}&apos; -- Skipping</source>
        <translation>L&apos;index de l&apos;image est non valide (&quot;{}&quot;) dans la texture &quot;{}&quot;. Passer outre.</translation>
    </message>
    <message>
        <location filename="../../material.py" line="523"/>
        <source>Invalid image path (&apos;{}&apos;) in texture &apos;{}&apos; -- Skipping</source>
        <translation>Le chemin d&apos;accès de l&apos;image est non valide (&quot;{}&quot;) dans la texture &quot;{}&quot;. Passer outre.</translation>
    </message>
    <message>
        <location filename="../../material.py" line="539"/>
        <source>Missing primary image (index 0) in texture &apos;{}&apos; -- Skipping texture</source>
        <translation>Image primaire manquante (index 0) dans la texture &quot;{}&quot;.  Passer outre la texture.</translation>
    </message>
    <message>
        <location filename="../../material.py" line="551"/>
        <source>No valid primary image (index 0) in texture &apos;{}&apos; -- Skipping texture</source>
        <translation>Pas d&apos;image primaire valide (index 0) dans la texture &quot;{}&quot;. Passer outre la texture.</translation>
    </message>
    <message>
        <location filename="../../material.py" line="588"/>
        <source>Invalid attribute &apos;{}&apos; in texture &apos;{}&apos; -- Skipping attribute</source>
        <translation>Attribut non valide &quot;{}&quot; dans la texture &quot;{}&quot;. Passer outre l&apos;attribut.</translation>
    </message>
    <message>
        <location filename="../../material.py" line="601"/>
        <source>Invalid type for attribute &apos;{}&apos; in texture &apos;{}&apos;: Cannot convert &apos;{}&apos; to &apos;{}&apos; -- Skipping attribute</source>
        <translation>Type non valide pour l&apos;attribut &quot;{}&quot; dans la texture &quot;{}&quot; : impossible de convertir &quot;{}&quot; en &quot;{}&quot;. Passer outre l&apos;attribut.</translation>
    </message>
    <message>
        <location filename="../../material.py" line="659"/>
        <source>Invalid syntax for texture &apos;{}&apos;: No valid arguments in statement (&apos;{}&apos;) -- Skipping value</source>
        <translation>Syntaxe non valide pour la texture &quot;{}&quot; : aucun argument valide dans l&apos;instruction (&quot;{}&quot;). Passer outre la valeur.</translation>
    </message>
    <message>
        <location filename="../../material.py" line="672"/>
        <source>Invalid syntax for attribute &apos;{}&apos; in texture &apos;{}&apos;: Expecting &apos;Texture(&quot;&lt;texname&gt;&quot;, &lt;texindex&gt;)&apos;, got &apos;{}&apos; instead -- Skipping value</source>
        <translation>Syntaxe non valide pour l&apos;attribut &quot;{}&quot; dans la texture &quot;{}&quot; : la &quot;texture (&quot;&lt;texname&gt;&quot;, &lt;texindex&gt;)&quot; attendue a &quot;{}&quot; à la place. Passer outre la valeur.</translation>
    </message>
    <message>
        <location filename="../../material.py" line="685"/>
        <source>Invalid syntax for attribute &apos;{}&apos; in texture &apos;{}&apos;: Reference to texture should be a tuple (&apos;&lt;texture&gt;&apos;, &lt;index&gt;, [&lt;scalar&gt;]) -- Skipping value</source>
        <translation>Syntaxe non valide pour l&apos;attribut &quot;{}&quot; dans la texture &quot;{}&quot; : la référence à la texture devrait être un tuple (&apos;&lt;texture&gt;&apos;, &lt;index&gt;, [&lt;scalar&gt;]). Passer outre la valeur.</translation>
    </message>
    <message>
        <location filename="../../material.py" line="708"/>
        <source>Invalid syntax for attribute &apos;{}&apos; in texture &apos;{}&apos;: Scalar should be a float -- Skipping value</source>
        <translation>Syntaxe non valide pour l&apos;attribut &quot;{}&quot; dans la texture &quot;{}&quot; : le scalaire devrait être une variable flottante. Passer outre la valeur.</translation>
    </message>
    <message>
        <location filename="../../project.py" line="346"/>
        <source>[Render] Unable to create rendering view for object &apos;{o}&apos;: unhandled object type</source>
        <translation>[Render] Impossible de créer une vue de rendu pour l&apos;objet &apos;{o}&apos;: type d&apos;objet non géré</translation>
    </message>
    <message>
        <location filename="../../project.py" line="430"/>
        <source>[Render][Project] CRITICAL ERROR - Negative or zero value(s) for Render Height and/or Render Width: cannot render. Aborting...
</source>
        <translation>[Render][Project] ERREUR CRITIQUE : valeur(s) négative(s) ou nulle(s) pour la hauteur et/ou la largeur du rendu : rendu impossible. Annulation...</translation>
    </message>
    <message>
        <location filename="../../project.py" line="444"/>
        <source>[Render][Project] WARNING - Output image path &apos;{params.output}&apos; does not seem to be a valid path on your system. This may cause the renderer to fail...
</source>
        <translation>[Render][Project] ATTENTION : le chemin d&apos;accès de l&apos;image de sortie &quot;{params.output}&quot; ne semble pas être un chemin valide sur votre système. Cela peut entraîner l&apos;échec du moteur de rendu...</translation>
    </message>
    <message>
        <location filename="../../project.py" line="471"/>
        <source>Renderer not found (&apos;{}&apos;) </source>
        <translation>Le moteur de rendu n&apos;a pas été trouvé (&quot;{}).</translation>
    </message>
    <message>
        <location filename="../../project.py" line="509"/>
        <source>Empty rendering command</source>
        <translation>Commande de rendu vide</translation>
    </message>
    <message>
        <location filename="../../project.py" line="572"/>
        <source>Template not found (&apos;{}&apos;)</source>
        <translation>Modèle non trouvé ({})</translation>
    </message>
    <message>
        <location filename="../../project.py" line="733"/>
        <source>Cannot render project:</source>
        <translation>Le projet ne peut pas être rendu :</translation>
    </message>
    <message>
        <location filename="../../project.py" line="743"/>
        <source>Render</source>
        <translation>Générer un rendu</translation>
    </message>
    <message>
        <location filename="../../project.py" line="748"/>
        <source>Change template</source>
        <translation>Changer de modèle</translation>
    </message>
    <message>
        <location filename="../../project.py" line="768"/>
        <source>Warning: Deleting Non-Empty Project</source>
        <translation>Attention : suppression d&apos;un projet non vide</translation>
    </message>
    <message>
        <location filename="../../project.py" line="774"/>
        <source>Project is not empty. All its contents will be deleted too.

Are you sure you want to continue?</source>
        <translation>Le projet n&apos;est pas vide. Tous ses contenus seront supprimés également.
Voulez-vous continuer ?</translation>
    </message>
    <message>
        <location filename="../../project.py" line="797"/>
        <source>[Render] Cannot render: {e}</source>
        <translation>[Render] Impossible de générer le rendu : {e}</translation>
    </message>
    <message>
        <location filename="../../project.py" line="843"/>
        <source>Select template</source>
        <translation>Sélectionner un modèle</translation>
    </message>
    <message>
        <location filename="../../rdrhandler.py" line="341"/>
        <source>Exporting</source>
        <translation>Exporter</translation>
    </message>
    <message>
        <location filename="../../rdrhandler.py" line="831"/>
        <source>[Render] Error: Renderer &apos;%s&apos; not found</source>
        <translation>[Render] Erreur : le moteur de rendu &quot;%s&quot; n&apos;a pas été trouvé.</translation>
    </message>
    <message>
        <location filename="../../renderables.py" line="254"/>
        <source>Unhandled object type (&apos;{name}&apos;: {ascendants})</source>
        <translation>Type d&apos;objet non traité ({name} : {ascendants})</translation>
    </message>
    <message>
        <location filename="../../renderables.py" line="274"/>
        <source>Nothing to render</source>
        <translation>Rien à rendre</translation>
    </message>
    <message>
        <location filename="../../renderables.py" line="283"/>
        <source>Cannot find mesh data</source>
        <translation>Impossible de trouver les données de maillage</translation>
    </message>
    <message>
        <location filename="../../renderables.py" line="290"/>
        <source>Mesh topology is empty</source>
        <translation>La topologie du maillage est vide</translation>
    </message>
    <message>
        <location filename="../../renderables.py" line="677"/>
        <source>Incomplete multimaterial (missing {m})</source>
        <translation>Multimatériau incomplet ({m} manquant(s))</translation>
    </message>
    <message>
        <location filename="../../taskpanels.py" line="276"/>
        <source>Use object color</source>
        <translation>Utiliser la couleur de l&apos;objet</translation>
    </message>
    <message>
        <location filename="../../taskpanels.py" line="282"/>
        <source>Use constant color</source>
        <translation>Utiliser une couleur constante</translation>
    </message>
    <message>
        <location filename="../../taskpanels.py" line="294"/>
        <location filename="../../taskpanels.py" line="389"/>
        <location filename="../../taskpanels.py" line="471"/>
        <source>Use texture</source>
        <translation>Utiliser une texture</translation>
    </message>
    <message>
        <location filename="../../taskpanels.py" line="374"/>
        <source>Use constant value</source>
        <translation>Utiliser une valeur constante</translation>
    </message>
    <message>
        <location filename="../../taskpanels.py" line="467"/>
        <source>Don&apos;t use</source>
        <translation>Ne pas utiliser</translation>
    </message>
    <message>
        <location filename="../../taskpanels.py" line="783"/>
        <source>Factor:</source>
        <translation>Facteur :</translation>
    </message>
    <message>
        <location filename="../../texture.py" line="196"/>
        <source>Add Image Entry</source>
        <translation>Ajouter une image</translation>
    </message>
    <message>
        <location filename="../../texture.py" line="199"/>
        <source>Remove Image Entry</source>
        <translation>Supprimer une image</translation>
    </message>
    <message>
        <location filename="../../texture.py" line="216"/>
        <source>Unallowed Image Removal</source>
        <translation>Suppression des images non autorisées</translation>
    </message>
    <message>
        <location filename="../../texture.py" line="220"/>
        <source>Unallowed removal: not enough images in texture (&lt;2)!
</source>
        <translation>Suppression non autorisée : pas assez d&apos;images dans la texture (&lt;2)!</translation>
    </message>
    <message>
        <location filename="../../texture.py" line="224"/>
        <source>Leaving less than 1 image in texture is not allowed...</source>
        <translation>Il est interdit de laisser moins d&apos;une image dans la texture...</translation>
    </message>
    <message>
        <location filename="../../texture.py" line="233"/>
        <source>Texture Image Removal</source>
        <translation>Suppression des images de texture</translation>
    </message>
    <message>
        <location filename="../../texture.py" line="234"/>
        <source>Choose Image to remove:</source>
        <translation>Choisir l&apos;image à supprimer :</translation>
    </message>
</context>
<context>
    <name>RenderMaterial</name>
    <message>
        <location filename="../ui/RenderMaterial.ui" line="14"/>
        <source>Material Rendering Settings</source>
        <translation>Paramètres de Rendu du Matériau</translation>
    </message>
    <message>
        <location filename="../ui/RenderMaterial.ui" line="28"/>
        <location filename="../ui/RenderMaterial.ui" line="32"/>
        <source>Choose material...</source>
        <translation>Choisissez un matériau...</translation>
    </message>
    <message>
        <location filename="../ui/RenderMaterial.ui" line="89"/>
        <source>Standard</source>
        <translation>Standard</translation>
    </message>
    <message>
        <location filename="../ui/RenderMaterial.ui" line="110"/>
        <source>Material Type:</source>
        <translation>Type de Matériau:</translation>
    </message>
    <message>
        <location filename="../ui/RenderMaterial.ui" line="121"/>
        <source>Choose material type...</source>
        <translation>Choisissez le type de matériau...</translation>
    </message>
    <message>
        <location filename="../ui/RenderMaterial.ui" line="130"/>
        <source>Passthrough</source>
        <translation>Passe-travers</translation>
    </message>
    <message>
        <location filename="../ui/RenderMaterial.ui" line="149"/>
        <source>Passthrough Text</source>
        <translation>Texte de passe-travers</translation>
    </message>
    <message>
        <location filename="../ui/RenderMaterial.ui" line="179"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;&lt;span style=&quot; font-size:8pt; font-style:italic;&quot;&gt;Warning: This text will be sent to renderer &amp;quot;as is&amp;quot; and will override any other material rendering settings. Be sure you know what you do when modifying it...&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;&lt;span style=&quot; font-size:8pt; font-style:italic;&quot;&gt;Attention: Ce texte sera envoyé au moteur de rendu &amp;quot;tel quel&amp;quot; et prendra le pas sur tous les autres paramètres de rendu. Assurez-vous de savoir ce que vous faites avant de le modifier...&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</translation>
    </message>
    <message>
        <location filename="../ui/RenderMaterial.ui" line="192"/>
        <source>Force UVMap computation</source>
        <translation>Forcer le calcul de la carte des UV</translation>
    </message>
    <message>
        <location filename="../ui/RenderMaterial.ui" line="206"/>
        <source>Fallback</source>
        <translation>Repli</translation>
    </message>
    <message>
        <location filename="../ui/RenderMaterial.ui" line="215"/>
        <source>Father Material:</source>
        <translation>Matériau père:</translation>
    </message>
</context>
<context>
    <name>RenderSettings</name>
    <message>
        <location filename="../ui/RenderSettings.ui" line="14"/>
        <source>Render preferences</source>
        <translation>Préférences de Render</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="20"/>
        <source>Plugins</source>
        <translation>Extensions</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="29"/>
        <source>Update Pip when reloading</source>
        <translation>Mettre à jour Pip lors du rechargement</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="39"/>
        <source>Disable GUI embedding</source>
        <translation>Désactiver l&apos;intégration de l&apos;interface graphique</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="65"/>
        <source>Enable MaterialX features</source>
        <translation>Activer les fonctionnalités de MaterialX</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="91"/>
        <source>Reset Plugins Environment</source>
        <extracomment>Reload all dependencies needed by plugins</extracomment>
        <translation>Réinitialiser l&apos;environnement des extensions</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="117"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Standard behavior is to download virtual environment package (&apos;venv&apos;)  from pypa.io.&lt;/p&gt;&lt;p&gt;If checked, Render will use the package provided by system Python installation instead.&lt;/p&gt;&lt;p&gt;&lt;br/&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation>Le comportement standard consiste à télécharger le paquet d&apos;environnement virtuel (&quot;venv&quot;) à partir de pypa.io.
Si cette case est cochée, Render utilisera le paquet fourni par l&apos;installation système de Python à la place.</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="139"/>
        <source>Use system virtualenv package</source>
        <translation>Utiliser le paquet virtuel &quot;env&quot; du système</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="149"/>
        <location filename="../ui/RenderSettings.ui" line="155"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Advanced and Debug parameters&lt;/p&gt;&lt;p&gt;&lt;span style=&quot; font-weight:600;&quot;&gt;WARNING&lt;/span&gt; - Do not modify if you don&apos;t know what you do - Unexpected behaviours may result...&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation>Paramètres avancés et de débogage
&lt;span style=&quot; font-weight:600;&quot;&gt;ATTENTION&lt;/span&gt; : ne pas modifier si vous ne savez pas ce que vous faites, des comportements inattendus peuvent en résulter...</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="152"/>
        <source>Advanced and Debug parameters WARNING - Do not modify if you don&apos;t know what you do - Unexpected behaviours may result...</source>
        <translation>Paramètres avancés et de débogage
ATTENTION : ne pas modifier si vous ne savez pas ce que vous faites, des comportements inattendus peuvent en résulter...</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="161"/>
        <source>Advanced &amp;&amp; Debug</source>
        <translation>Avancé &amp;&amp; Débogage</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="186"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Dry run &lt;span style=&quot; font-size:8pt; font-style:italic;&quot;&gt;(won&apos;t run renderer - debug purpose only)&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation>Essai &lt;span style=&quot; font-size:8pt; font-style:italic;&quot;&gt;(cela n&apos;exécute pas le moteur de rendu, uniquement à des fins de débogage)&lt;/span&gt;</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="193"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Enable multiprocessing &lt;span style=&quot; font-size:8pt; font-style:italic;&quot;&gt;(experimental)&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation>Activer le traitement multiple &lt;span style=&quot; font-size:8pt; font-style:italic;&quot;&gt;(expérimental)&lt;/span&gt;</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="216"/>
        <source>Do not modify ShapeColor when assigning material</source>
        <translation>Ne pas modifier ShapeColor lors de l&apos;attribution du matériau</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="223"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Disable Numpy&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation>Désactiver Numpy</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="243"/>
        <source>Use UUID for exported file names</source>
        <translation>Utiliser l&apos;UUID pour les noms de fichiers exportés</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="288"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Use FreeCAD materials directory &lt;span style=&quot; font-size:8pt; font-style:italic;&quot;&gt;(not recommended)&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation>Utiliser le répertoire des matériaux de FreeCAD &lt;span style=&quot; font-size:8pt; font-style:italic;&quot;&gt;(non recommandé)&lt;/span&gt;</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="321"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Multiprocessing threshold &lt;span style=&quot; font-size:8pt; font-style:italic;&quot;&gt;(number of points)&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation>Seuil du traitement multiple &lt;span style=&quot; font-size:8pt; font-style:italic;&quot;&gt;(nombre de points)&lt;/span&gt;</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="328"/>
        <source>Clear report view before each run</source>
        <translation>Effacer l&apos;affichage du rapport avant chaque exécution</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="361"/>
        <source>Auto import module at startup</source>
        <translation>Importer automatiquement le module au démarrage</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="374"/>
        <source>LuxRender (deprecated)</source>
        <translation>LuxRender (obsolète)</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="380"/>
        <location filename="../ui/RenderSettings.ui" line="603"/>
        <source>Optional parameters to be passed to Luxrender when rendering</source>
        <translation>Paramètres optionnels à fournir à Luxrender lors du rendu</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="402"/>
        <source>LuxRender UI path</source>
        <translation>Chemin d&apos;accès à l&apos;interface utilisateur de LuxRender</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="409"/>
        <location filename="../ui/RenderSettings.ui" line="473"/>
        <source>The path to the luxrender UI executable</source>
        <translation>Chemin d&apos;accès à l&apos;exécutable de l&apos;interface utilisateur de Luxrender</translation>
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
        <translation>Paramètres de Render</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="438"/>
        <source>LuxRender command (cli) path</source>
        <translation>Chemin d&apos;accès de la commande de LuxRender (console)</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="445"/>
        <location filename="../ui/RenderSettings.ui" line="489"/>
        <source>The path to the Luxrender console (luxconsole) executable</source>
        <translation>Chemin d&apos;accès à l&apos;exécutable de la console de Luxrender (luxconsole)</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="508"/>
        <source>LuxCore command (cli) path</source>
        <translation>Chemin d&apos;accès à la commande de LuxCore (console)</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="518"/>
        <source>LuxCore UI path</source>
        <translation>Chemin d&apos;accès à l&apos;interface utilisateur de LuxCore</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="596"/>
        <source>LuxCore engine</source>
        <translation>Moteur de LuxCore</translation>
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
        <translation>Chemin d&apos;accès à l&apos;exécutable OspStudio</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="744"/>
        <source>General</source>
        <translation>Général</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="753"/>
        <source>Default render width</source>
        <translation>Largeur de rendu par défaut</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="807"/>
        <source>Prefix</source>
        <translation>Préfixe</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="817"/>
        <source>Default render height</source>
        <translation>Hauteur de rendu par défaut</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="824"/>
        <source>A prefix that can be added before the renderer executable. This is useful, for example, to add environment variable or run the renderer inside a GPU switcher such as primusrun or optirun on linux</source>
        <translation>Un préfixe qui peut être ajouté avant l&apos;exécutable du moteur de rendu. Ceci est utile, par exemple, pour ajouter une variable d&apos;environnement ou faire exécuter le moteur de rendu à l&apos;intérieur d&apos;un sélecteur de GPU, comme primusrun ou optirun sous Linux.</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="858"/>
        <source>Appleseed Studio path</source>
        <translation>Chemin d&apos;accès vers Appleseed Studio</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="865"/>
        <source>The path to the Appleseed cli executable</source>
        <translation>Le chemin d&apos;accès à l&apos;exécutable de la console d&apos;Appleseed</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="881"/>
        <source>Optional rendering parameters to be passed to the Appleseed executable</source>
        <translation>Paramètres optionnels à fournir à Appleseed lors du rendu</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="910"/>
        <source>The path to the Appleseed studio executable (optional)</source>
        <translation>Le chemin d&apos;accès de l&apos;exécutable Appleseed Studio (optionnel)</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="929"/>
        <source>Appleseed command (cli) path</source>
        <translation>Chemin d&apos;accès de la commande d&apos;Appleseed (console)</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="974"/>
        <source>The path to the Pov-Ray executable</source>
        <translation>Le chemin d&apos;accès de l&apos;exécutable Pov-Ray</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="1000"/>
        <source>Optional parameters to be passed to Pov-Ray when rendering</source>
        <translation>Paramètres optionnels à fournir à Pov-Ray lors du rendu</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="1022"/>
        <source>PovRay executable path</source>
        <translation>Chemin d&apos;accès de l&apos;exécutable Pov-Ray</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="1077"/>
        <source>Pbrt executable path</source>
        <translation>Chemin d&apos;accès de l&apos;exécutable Pbrt</translation>
    </message>
    <message>
        <location filename="../ui/RenderSettings.ui" line="1147"/>
        <source>Cycles executable (standalone) path</source>
        <translation>Chemin d&apos;accès de l&apos;exécutable Cycles (mode autonome)</translation>
    </message>
</context>
<context>
    <name>Render_AreaLight</name>
    <message>
        <location filename="../../commands.py" line="298"/>
        <source>Area Light</source>
        <translation>Surface</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="301"/>
        <source>Create an Area Light object</source>
        <translation>Créer un objet Lumière de surface</translation>
    </message>
</context>
<context>
    <name>Render_Camera</name>
    <message>
        <location filename="../../commands.py" line="245"/>
        <source>Camera</source>
        <translation>Caméra</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="249"/>
        <source>Create a Camera object from the current camera position</source>
        <translation>Créer un objet Caméra à partir de la position actuelle de la caméra</translation>
    </message>
</context>
<context>
    <name>Render_DistantLight</name>
    <message>
        <location filename="../../commands.py" line="380"/>
        <source>Distant Light</source>
        <translation>Distante</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="383"/>
        <source>Create an Distant Light object</source>
        <translation>Créer un objet Lumière distante</translation>
    </message>
</context>
<context>
    <name>Render_Help</name>
    <message>
        <location filename="../../commands.py" line="713"/>
        <source>Help</source>
        <translation>Aide</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="717"/>
        <source>Open Render help</source>
        <translation>Ouvrir l&apos;aide de Render</translation>
    </message>
</context>
<context>
    <name>Render_ImageLight</name>
    <message>
        <location filename="../../commands.py" line="352"/>
        <source>Image Light</source>
        <translation>Image</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="355"/>
        <source>Create an Image Light object</source>
        <translation>Créer un objet Lumière d&apos;une image</translation>
    </message>
</context>
<context>
    <name>Render_Libraries</name>
    <message>
        <location filename="../../commands.py" line="844"/>
        <source>Libraries</source>
        <translation>Bibliothèques</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="847"/>
        <source>Download from material libraries</source>
        <translation>Télécharger à partir des bibliothèques de matériaux</translation>
    </message>
</context>
<context>
    <name>Render_Lights</name>
    <message>
        <location filename="../../commands.py" line="822"/>
        <source>Lights</source>
        <translation>Lumières</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="823"/>
        <source>Create a Light</source>
        <translation>Créer une lumière</translation>
    </message>
</context>
<context>
    <name>Render_MaterialApplier</name>
    <message>
        <location filename="../../commands.py" line="582"/>
        <source>Apply Material</source>
        <translation>Appliquer un matériau</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="585"/>
        <source>Apply a Material to selection</source>
        <translation>Appliquer un matériau à une sélection</translation>
    </message>
</context>
<context>
    <name>Render_MaterialCreator</name>
    <message>
        <location filename="../../commands.py" line="414"/>
        <source>Internal Material Library</source>
        <translation>Bibliothèque de matériaux internes</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="418"/>
        <source>Create Material</source>
        <translation>Créer un matériau</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="425"/>
        <source>Create a new Material in current document from internal library</source>
        <translation>Créer un nouveau matériau dans le document en cours à partir de la bibliothèque interne</translation>
    </message>
</context>
<context>
    <name>Render_MaterialRenderSettings</name>
    <message>
        <location filename="../../commands.py" line="551"/>
        <source>Edit Material Render Settings</source>
        <translation>Éditer les paramètres de rendu du matériau</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="555"/>
        <source>Edit rendering parameters of the selected Material</source>
        <translation>Éditer les paramètres de rendu du matériau sélectionné</translation>
    </message>
</context>
<context>
    <name>Render_Materials</name>
    <message>
        <location filename="../../commands.py" line="832"/>
        <source>Materials</source>
        <translation>Matériaux</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="833"/>
        <source>Manage Materials</source>
        <translation>Gérer les matériaux</translation>
    </message>
</context>
<context>
    <name>Render_PointLight</name>
    <message>
        <location filename="../../commands.py" line="272"/>
        <source>Point Light</source>
        <translation>Point</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="275"/>
        <source>Create a Point Light object</source>
        <translation>Créer un objet Lumière de type point</translation>
    </message>
</context>
<context>
    <name>Render_Projects</name>
    <message>
        <location filename="../../commands.py" line="109"/>
        <source>{} Project</source>
        <translation>{} Projet</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="110"/>
        <source>Create a {} project</source>
        <translation>Créer un projet {}</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="809"/>
        <source>Projects</source>
        <translation>Projets</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="810"/>
        <source>Create a Rendering Project</source>
        <translation>Créer un projet de rendu</translation>
    </message>
</context>
<context>
    <name>Render_Render</name>
    <message>
        <location filename="../../commands.py" line="207"/>
        <source>Render project</source>
        <translation>Projet Render</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="213"/>
        <source>Perform the rendering of a selected project or the default project</source>
        <translation>Effectuer le rendu d&apos;un projet sélectionné ou du projet par défaut</translation>
    </message>
</context>
<context>
    <name>Render_Settings</name>
    <message>
        <location filename="../../commands.py" line="739"/>
        <source>Render settings</source>
        <translation>Paramètres de Render</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="743"/>
        <source>Open Render workbench settings</source>
        <translation>Ouvrir les paramètres de l&apos;atelier Render</translation>
    </message>
</context>
<context>
    <name>Render_SunskyLight</name>
    <message>
        <location filename="../../commands.py" line="326"/>
        <source>Sunsky Light</source>
        <translation>Lumière du jour</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="329"/>
        <source>Create a Sunsky Light object</source>
        <translation>Créer un objet Lumière du jour</translation>
    </message>
</context>
<context>
    <name>Render_View</name>
    <message>
        <location filename="../../commands.py" line="149"/>
        <source>Rendering View</source>
        <translation>Vue de rendu</translation>
    </message>
    <message>
        <location filename="../../commands.py" line="155"/>
        <source>Create a Rendering View of the selected object(s) in the selected project or the default project</source>
        <translation>Créer une vue de rendu de l&apos;objet ou des objets sélectionnés dans le projet sélectionné ou le projet par défaut</translation>
    </message>
</context>
<context>
    <name>Workbench</name>
    <message>
        <location filename="../../../InitGui.py" line="52"/>
        <source>The Render workbench is a modern replacement for the Raytracing workbench</source>
        <translation>L&apos;atelier Render est un remplacement moderne de l&apos;atelier Raytracing.</translation>
    </message>
    <message>
        <location filename="../../../InitGui.py" line="132"/>
        <source>Render</source>
        <translation>Générer un rendu</translation>
    </message>
    <message>
        <location filename="../../../InitGui.py" line="135"/>
        <source>&amp;Render</source>
        <translation>&amp;Rendu</translation>
    </message>
    <message>
        <location filename="../../../InitGui.py" line="139"/>
        <source>Loading Render module... done</source>
        <translation>Chargement de l&apos;atelier Render... fait</translation>
    </message>
</context>
</TS>
