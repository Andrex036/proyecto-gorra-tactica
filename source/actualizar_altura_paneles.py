"""Reduce la copa un 10% conservando la visera del modelo de entrada y el despiece.

python actualizar_altura_paneles.py MODELO_BASE.blend DIRECTORIO_SALIDA
Requiere bpy 4.3, NumPy y SciPy. El archivo base no se sobrescribe.
"""
from pathlib import Path
import sys,json,struct,hashlib
import bpy,bmesh,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
import proporcion_copa as proporcion
import exportar_visor

base,out=map(Path,sys.argv[1:3]);out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(base));scene=bpy.context.scene;scene.frame_set(1)
model=bpy.data.collections['GORRA | piezas editables']
def signature(o):
 a=np.empty(len(o.data.vertices)*3);o.data.vertices.foreach_get('co',a)
 return hashlib.sha256(a.tobytes()).hexdigest()
others={o.name:signature(o) for o in model.objects if o.type=='MESH' and o.get('conjunto') in {'visera','cervical','banda'}}
report={'altura_paneles':proporcion.aplicar(),'objetos':{}}
assert all(signature(bpy.data.objects[name])==value for name,value in others.items())
report['otras_mallas_sin_cambios']=len(others)
for name in ['04 Visera redondeada con caída','Ribete exterior visera']:
 o=bpy.data.objects[name];bm=bmesh.new();bm.from_mesh(o.data)
 assert all(e.is_manifold for e in bm.edges),name
 assert all(f.calc_area()>1e-15 for f in bm.faces),name
 report['objetos'][name]={}
 report['objetos'][name]['volumen_cm3']=abs(bm.calc_volume(signed=True))*1e6
 report['objetos'][name]['malla_cerrada']=True;bm.free()
scene.frame_set(1);bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT')
for o in model.objects:o.select_set(True)
bpy.context.view_layer.objects.active=bpy.data.objects['Panel Delantero']
bpy.ops.wm.save_as_mainfile(filepath=str(out/'gorra_tactica.blend'),compress=True)
glb=out/'gorra_tactica.glb'
bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_materials='EXPORT',export_cameras=False,export_lights=False,export_animations=True,export_animation_mode='SCENE',export_force_sampling=True)
raw=glb.read_bytes();size=struct.unpack_from('<I',raw,12)[0];data=json.loads(raw[20:20+size]);animations=data.get('animations',[])
if len(animations)>1:
 combined={'name':'Separar y ensamblar','channels':[],'samplers':[]}
 for animation in animations:
  offset=len(combined['samplers']);combined['samplers'].extend(animation['samplers'])
  for channel in animation['channels']:
   channel=dict(channel);channel['sampler']+=offset;combined['channels'].append(channel)
 data['animations']=[combined];encoded=json.dumps(data,separators=(',',':'),ensure_ascii=False).encode();encoded+=b' '*((-len(encoded))%4)
 rest=raw[20+size:];glb.write_bytes(struct.pack('<III',0x46546c67,2,20+len(encoded)+len(rest))+struct.pack('<II',len(encoded),0x4e4f534a)+encoded+rest)
parts=exportar_visor.partes(model)
(out/'visor-data.json').write_text(json.dumps(parts,separators=(',',':')))
(out/'validacion-paneles.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('PANELES_READY',len(parts),'partes',json.dumps(report['altura_paneles'],ensure_ascii=False),flush=True)
