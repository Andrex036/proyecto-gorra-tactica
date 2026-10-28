"""Renders reproducibles del modelo real para el visor y la revisión de visera.

python render_vistas_frontal.py ARCHIVO.blend DIRECTORIO [review|assets|parts|acabados]
Requiere bpy 4.3, NumPy y Pillow. No modifica el archivo Blender de entrada.
"""
from pathlib import Path
import sys,json,math,os
import bpy,numpy as np
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parent))
import textil,ajuste_visera,curvatura_frontal,estudio_realista

blend=Path(sys.argv[1]);out=Path(sys.argv[2]);mode=sys.argv[3] if len(sys.argv)>3 else 'review'
out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(blend));scene=bpy.context.scene;scene.frame_set(1)
model=bpy.data.collections['GORRA | piezas editables'];objects=[o for o in model.objects if o.type=='MESH']
estudio_realista.iluminar(samples=96 if mode=='acabados' else 64)
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.render.resolution_percentage=100
cam=bpy.data.objects.get('Cámara frontal 3-4');scene.camera=cam;cam.data.type='ORTHO';cam.data.clip_start=.001
def render(name,groups=None,color='negro',direction=(1,-1.5,.8),size=(1440,980),crop=True,detail=False):
 textil.set_palette(color)
 selected=[]
 for o in objects:
  o.hide_render=bool(groups and o.get('conjunto') not in groups)
  if not o.hide_render:selected.append(o)
 scene.render.resolution_x,scene.render.resolution_y=size
 points=np.array([tuple(o.matrix_world@Vector(c)) for o in selected for c in o.bound_box])
 center=Vector(((points.min(0)+points.max(0))/2).tolist())
 cam.location=center+Vector(direction).normalized()*.9
 cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
 rotation=cam.rotation_euler.to_matrix().transposed()
 projected=np.array([tuple(rotation@(Vector(p)-center)) for p in points])
 extent=projected.max(0)-projected.min(0);aspect=size[0]/size[1]
 cam.data.ortho_scale=max(extent[0],extent[1]*aspect)*1.12
 if detail:
  center=Vector((0,0,.104));cam.location=center+Vector(direction).normalized()*.9
  cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.053
 reference=os.environ.get('GORRA_CAMERAS')
 if reference and (Path(reference)/(name+'.json')).exists():
  camera=json.loads((Path(reference)/(name+'.json')).read_text());cam.location=camera['camera'];cam.data.ortho_scale=camera['scale'];bpy.context.view_layer.update()
 scene.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
 if crop:
  im=Image.open(scene.render.filepath);box=im.getchannel('A').getbbox()
  if box:
   im=im.crop(box);pad=max(12,int(max(im.size)*.035));padded=Image.new('RGBA',(im.width+2*pad,im.height+2*pad));padded.paste(im,(pad,pad));padded.save(scene.render.filepath)
 else:
  probes={}
  x=np.linspace(-7.5,7.5,101)
  edge=ajuste_visera.borde_exterior(np.arcsin(x/8.9))
  if bpy.data.objects['04 Visera redondeada con caída'].get('curvatura_frontal_total_grados'):edge=curvatura_frontal.deformar(edge)
  points=[('root',(0,-10.4,-.05)),('tip',tuple(edge[50])),('left',tuple(edge[0])),('right',tuple(edge[-1]))]
  points.extend(('curve_'+str(i),tuple(p)) for i,p in enumerate(edge))
  anchor=ajuste_visera.deformar_superficie(ajuste_visera.visor_base(np.linspace(-np.pi/2,np.pi/2,101),v=0,off=0))
  points.extend(('anchor_'+str(i),tuple(p)) for i,p in enumerate(anchor))
  for label,p in points:
   q=world_to_camera_view(scene,cam,Vector(p)*.01);probes[label]=[q.x*size[0],(1-q.y)*size[1]]
  (out/(name+'.json')).write_text(json.dumps({'width':size[0],'height':size[1],'probes':probes,'camera':list(cam.location),'scale':cam.data.ortho_scale}))
 print('RENDER_READY',name,flush=True)

if mode=='acabados':
 render('gorra-render-realista',color='negro',direction=(1,-1.6,.8),size=(1800,1300))
 render('detalle-costuras-boton',color='negro',direction=(.6,-.8,1.8),size=(1400,1100),crop=False,detail=True)
elif mode in {'assets','parts'}:
 if mode=='assets':
  for color in ['gris','negro','beige']:render('modelo-'+color,color=color)
 render('visera',groups={'visera'},direction=(.25,-1,1.15),size=(600,400))
 for name,direction in [('panel_delantero',(.2,-1,.45)),('panel_trasero',(.2,1,.45)),('panel_izquierdo',(-1,-.15,.4)),('panel_derecho',(1,-.15,.4)),('ajuste',(1,1,.45)),('cervical',(.2,1,.35)),('banda',(1,-1,1))]:
  render(name,groups={name,'escudo'} if name=='panel_delantero' else {name},direction=direction,size=(600,400))
 if mode=='assets':
  scene.frame_set(60);bpy.context.view_layer.update()
  render('gorra-desarmada',direction=(1,-1.5,.8),size=(1440,1100))
else:
 render('perspectiva',color='negro',direction=(1,-1.6,.55),size=(1440,1100),crop=False)
 render('frontal',color='negro',direction=(0,-1,0),size=(1440,1100),crop=False)
 render('lateral',color='negro',direction=(1,0,0),size=(1440,1100),crop=False)
 render('visera-detalle',groups={'visera'},color='negro',direction=(1,-1.6,.55),size=(1440,900),crop=True)
print('VIEWS_READY',flush=True)
