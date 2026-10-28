# Proyecto Gorra Táctica — archivos de desarrollo

Este paquete contiene el código de la landing, el visor 3D, los modelos
editables, los materiales, los renders y los scripts que generan la geometría.

## Abrir la página

Descomprime el paquete y abre `dist/index.html` en un navegador con WebGL y
DecompressionStream. No necesita instalación ni compilación. También puedes
servir la carpeta desde la raíz con `python -m http.server 8000` y abrir
`http://localhost:8000/dist/`.

## Archivos principales

| Ruta | Contenido |
| --- | --- |
| `dist/index.html` | Estructura y textos de la landing |
| `dist/css/styles.css` | Estilos y adaptación a pantallas |
| `dist/js/app.js` | Visor, cámaras, despiece, selección y controles |
| `dist/js/textile.js` | Textura tejida y paletas negro, gris y beige |
| `dist/js/technical-data.js` | Ocho fichas técnicas transcritas de PLANOS.docx y cámaras por componente |
| `dist/js/dipro-texture.js` | Imagen original del escudo DIPRO para uso sin conexión |
| `dist/js/model-data.js` | Geometría, normales, UV y grupos del visor |
| `dist/vendor/` | Three.js y su licencia |
| `dist/assets/gorra_tactica.blend` | Modelo editable, materiales, cámaras, luces y animación |
| `dist/assets/gorra_tactica.glb` | Modelo portable con textura y animación incorporadas |
| `dist/assets/gorra-desarmada.png` | Despiece actualizado |
| `dist/assets/partes/` | Vistas del modelo real para las ocho tarjetas y referencias en tres colores |
| `dist/assets/plano-moldes.png` | Lámina de moldes extraída del documento de referencia |
| `reviews/*.png` | Vistas de revisión; imágenes vigentes: `gorra-render-realista.png` y `detalle-costuras-boton.png` |
| `dist/assets/icono-proyecto-gorra.jpg` | Icono de la landing |
| `source/crear_gorra.py` | Generador de todas las piezas y los relieves |
| `source/ajuste_visera.py` | Visera original activa; cordón y laureles |
| `source/curvatura_frontal.py` | Revisión histórica de 35°, desactivada |
| `source/actualizar_curvatura_frontal.py` | Exportador de la revisión histórica de 35°, desactivada |
| `source/proporcion_copa.py` | Reducción de altura de los paneles del 10% con base conservada |
| `source/actualizar_altura_paneles.py` | Exportación del modelo base con paneles al 90% |
| `source/remates_superiores.py` | Remates separados ocultos bajo el botón |
| `source/actualizar_remates.py` | Actualización y validación del modelo sin reconstruir las demás piezas |
| `source/estudio_realista.py` | Cajas de luz y acabado textil compartidos por Blender y los renders |
| `source/render_vistas_frontal.py` | Renders reales de revisión y referencias del visor |
| `source/cables_laterales.py` | Cables visibles de círculo a círculo y conexión al retorno interior |
| `source/paneles_copa.py` | Cuatro paneles reales, aberturas triangulares y mecanismo único con cableado interior |
| `source/acabados_cervical.py` | Dos pliegues, costuras integradas del protector y letras BOA del dial |
| `source/assets/cervical-dial-referencia.jpg` | Referencia del protector cervical y del dial |
| `source/acabados_dipro.py` | Geometría regular de visera y aplicación del escudo DIPRO |
| `source/preparar_escudo.py` | Construcción del bajorrelieve desde la imagen original |
| `source/exportar_visor.py` | Exportación por materiales, con UV del escudo |
| `source/assets/DIPRO.png` | Referencia original sin modificar |
| `source/assets/PLANOS.docx` | Documento técnico de referencia, conservado sin modificar |
| `source/assets/dipro-relieve.npz` | Malla precalculada del escudo |
| `source/textil.py` | Trama de 1024 px, coordenadas UV y materiales |
| `source/pack_model.py` | Conversión de geometría exportada al formato del visor |
| `source/assets/textura-tela-normal.png` | Mapa normal de la tela, también incorporado en Blender y GLB |
| `.openai/hosting.json` | Configuración del sitio original en Sites |

## Editar el modelo

Abre `dist/assets/gorra_tactica.blend` con Blender 4.3 o posterior. Hay nueve
conjuntos independientes: Panel Delantero, Panel Trasero, Panel Lateral Izquierdo,
Panel Lateral Derecho, Sistema de ajuste, visera, protector cervical, escudo y
banda interior. La animación muestra el
modelo armado en los cuadros 1 y 120, y separado en el cuadro 60.

El visor presenta ocho componentes técnicos: el escudo se incluye al seleccionar
el Panel Delantero. El despiece completo conserva los nueve grupos geométricos.
El panel trasero y el protector cervical se inspeccionan por separado, aunque
el plano los describe como un solo pliego. Las medidas de las fichas son del
plano; no son mediciones de la geometría aproximada del visor.

## Interfaz y fichas técnicas

El visor ocupa todo el ancho disponible, con controles inferiores y ocho tarjetas
de componentes. Al seleccionar una tarjeta se aísla la pieza, se centra la cámara
y se abre su ficha. La interfaz se adapta a móvil, tablet y escritorio.
Las opciones de iluminación son Estudio, Luz suave e Interior y detalles.
El acabado elegido se conserva al cambiar de componente o restablecer la vista.

Edita medidas, materiales y notas en `dist/js/technical-data.js`. La propuesta de
capas balísticas del documento está marcada como pendiente de verificación.
Si WebGL no está disponible, las fichas siguen funcionando con renders de
referencia; las imágenes individuales de componentes están en negro.

Los cambios manuales al archivo Blender no actualizan automáticamente el
visor: `model-data.js` es una exportación independiente. Para regenerar la
geometría procedural y actualizar el visor, modifica los scripts de `source/`
y sigue el flujo siguiente.

## Regenerar el modelo y el visor

Necesitas Blender 4.3 o posterior para el modelado y Python 3 para empaquetar
los datos. El Python integrado de Blender incluye los módulos necesarios.
Ejecuta desde la raíz del proyecto. `blender` debe estar en el PATH; puedes
sustituirlo por la ruta completa a su ejecutable.

Windows PowerShell:

```powershell
$env:GORRA_OUTPUT_DIR = Join-Path $PWD "build/modelo"
$env:GORRA_RENDER = "0"
blender --background --python source/crear_gorra.py
python source/pack_model.py build/modelo/visor-data.json dist/js/model-data.js
Copy-Item build/modelo/gorra_tactica.blend dist/assets/
Copy-Item build/modelo/gorra_tactica.glb dist/assets/
```

macOS o Linux:

```bash
GORRA_OUTPUT_DIR="$PWD/build/modelo" GORRA_RENDER=0 blender --background --python source/crear_gorra.py
python3 source/pack_model.py build/modelo/visor-data.json dist/js/model-data.js
cp build/modelo/gorra_tactica.blend build/modelo/gorra_tactica.glb dist/assets/
```

Con `GORRA_RENDER=1`, el generador también produce vistas frontal, posterior y
desarmada en la carpeta de salida. Las paletas de `source/textil.py` y
`dist/js/textile.js` deben mantenerse coordinadas al cambiar los colores.

## Alojar en otro servidor

Publica el contenido de `dist/` conservando sus rutas relativas. No hace falta
un servidor de aplicaciones ni una base de datos. La configuración en
`.openai/hosting.json` identifica el proyecto original de Sites y no se necesita
en un alojamiento estático externo.

El paquete contiene los archivos de trabajo actuales; excluye el historial de
Git, cachés y ZIP anteriores que duplicaban estos mismos archivos.

## Escudo DIPRO y borde uniforme

El escudo incorpora la silueta y las capas principales en bajorrelieve y la
imagen original mediante UV para conservar los textos y símbolos. Sus colores
se mantienen en las tres paletas. El ribete de la visera tiene sección
circular constante, remates simétricos y una unión continua con la copa.

La malla del escudo ya está incluida. Solo si se cambia la referencia, instala
NumPy, SciPy y Pillow y ejecuta `python source/preparar_escudo.py` antes de
regenerar el modelo. Actualiza también `dist/js/dipro-texture.js` con la imagen
original codificada como URL de datos PNG.

## Forro del protector cervical

El interior tiene una superficie lisa independiente de los pliegues exteriores
y un remate redondeado cerrado. El material `lining` mantiene el color de la
tela y reduce el relieve de la trama. Las UV del canto siguen su longitud y
anchura físicas. El exportador conserva estas UV y evita simplificar esta
pieza. El formato del visor admite un décimo campo opcional de cabecera con
valor `16` para las normales int16; su ausencia conserva normales int8.

## Paneles de la copa y sistema de ajuste

Los dos sectores frontales forman el **Panel Delantero**, sin costura central.
Los dos posteriores forman el **Panel Trasero**, también sin costura central.
Los paneles laterales conservan la envolvente original y tienen aberturas
triangulares reales coincidentes con los fuelles del mecanismo. Los cuatro
paneles son sólidos independientes, con sus ribetes, puntadas y ojales.

El **Sistema de ajuste** es una sola malla editable con materiales separados:
dial BOA, soporte, ambos ajustes laterales y cableado conectado. Conserva la
posición de montaje de los herrajes. Los cables horizontales y cruzados de los laterales se ven por fuera,
desde el centro de cada guía circular. Las conexiones hacia el dial recorren
el interior de la copa. Los fuelles conservan su forro interior. Al elegir
este conjunto en el visor se puede inspeccionar todo el recorrido. El despiece
mueve el sistema completo sin alterar las posiciones relativas de sus piezas.

La superficie original de la copa se recorta en cuatro paneles; la revisión actual reduce su altura un 10% conservando la base.
El exportador conserva los cantos mediante normales de esquina y precisión
int16 para los paneles y el mecanismo. Los otros conjuntos mantienen su malla.

## Estado actual: visera original y paneles al 90% de altura

La visera recupera exactamente la geometría anterior al ajuste de 35°,
incluidos su cuerpo, borde exterior, cordón y laureles. Se han retirado del
modelo activo el arco de 35° y la modificación posterior de sus laterales.
La restauración se documenta en `reviews/visera-original-restaurada.png`.
El acabado vigente se ve en `reviews/gorra-render-realista.png`.

Los cuatro paneles mantienen la reducción de altura del 10%: aproximadamente
11,60 cm a 10,44 cm, con el mismo ancho y base. Se conservan también sus
costuras, aberturas, escudo y el ajuste de guías, dial BOA y cables.
El protector cervical y la banda interior mantienen su geometría.

`crear_gorra.py` genera la visera original y después aplica `proporcion_copa.py`.
Para actualizar una copia del modelo base anterior al arco de 35°:
1. `python source/actualizar_altura_paneles.py BASE.blend SALIDA`
2. `python source/pack_model.py SALIDA/visor-data.json dist/js/model-data.js`

`curvatura_frontal.py` y `actualizar_curvatura_frontal.py` se conservan como
código histórico y no se ejecutan al generar el modelo actual.

## Color inicial y selección de piezas

El visor carga en negro con bordado dorado, tanto en 3D como en su imagen de referencia.
Las ocho miniaturas de selección de piezas se renderizan en negro. Los acabados
gris y beige continúan disponibles en el selector. Para regenerar las miniaturas:
`python source/render_vistas_frontal.py dist/assets/gorra_tactica.blend SALIDA parts`.


REMATES SUPERIORES E ILUMINACIÓN
Las cuatro costuras de unión y las ocho filas de puntadas terminan por
separado bajo el botón, dejando libre el centro. Las puntadas mantienen
separación lateral en la zona superior. El archivo conserva la visera
original y los paneles al 90% de altura.

El estudio usa cajas de luz amplias, relleno moderado y recorte posterior.
La tela incorpora brillo textil sutil y menor relieve de la trama. El visor
añade sombras de contacto y reflejos de estudio; mantiene sus tres opciones
de iluminación. Renders vigentes: reviews/gorra-render-realista.png y
reviews/detalle-costuras-boton.png.

La vista Superior permite inspeccionar el botón y las cuatro uniones.
