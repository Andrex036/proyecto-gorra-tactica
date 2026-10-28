"""Actualiza un modelo existente sin reconstruir las piezas ya aprobadas.
python actualizar_remates.py ENTRADA.blend DIRECTORIO_SALIDA
"""
from pathlib import Path
import sys,json,struct,ast
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
import remates_superiores,estudio_realista,textil,exportar_visor
from proporcion_copa import coordenadas

src=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(src));scene=bpy.context.scene;scene.frame_set(1);bpy.context.view_layer.update()
model=bpy.data.collections['GORRA | piezas editables']
before={o.name:coordenadas(o)[1] for o in model.objects if o.type=='MESH'}
changed=remates_superiores.aplicar();assert len(changed)==8
unchanged=0
for n,p in before.items():
    if n not in changed:assert np.array_equal(p,coordenadas(bpy.data.objects[n])[1]),n;unchanged+=1
button=bpy.data.objects['03 Botón superior'];p=coordenadas(button)[1]
bvh=BVHTree.FromPolygons([Vector(v) for v in p],[tuple(f.vertices) for f in button.data.polygons])
hidden=0;endpoints=[]
for name in changed:
    o=bpy.data.objects[name];p=coordenadas(o)[1];r=np.linalg.norm(p[:,:2],axis=1)
    ends=p[r<.40] if name.startswith('Costura panel') else p[r<.42]
    assert len(ends)>0,name
    for v in ends:
        assert bvh.ray_cast(Vector(v),Vector((0,0,1)))[0] is not None,name+' expuesta arriba'
        assert bvh.ray_cast(Vector(v),Vector((0,0,-1)))[0] is not None,name+' expuesta debajo'
    hidden+=len(ends);endpoints.extend(ends.tolist())
assert min(np.linalg.norm(np.array(endpoints)[:,:2],axis=1))>.12
estudio_realista.iluminar();textil.set_palette('negro')
bpy.ops.object.select_all(action='DESELECT')
for o in model.objects:o.select_set(True)
bpy.context.view_layer.objects.active=bpy.data.objects['Panel Delantero']
bpy.ops.wm.save_as_mainfile(filepath=str(out/'gorra_tactica.blend'),compress=True)
bpy.ops.export_scene.gltf(filepath=str(out/'gorra_tactica.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_materials='EXPORT',export_cameras=False,export_lights=False,export_animations=True,export_animation_mode='SCENE',export_force_sampling=True)
tree=ast.parse((Path(__file__).parent/'crear_gorra.py').read_text())
fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='unificar_animacion_glb')
exec(compile(ast.Module(body=[fn],type_ignores=[]),'<animacion>','exec'));unificar_animacion_glb(out/'gorra_tactica.glb')
parts=exportar_visor.partes(model,only_names=set(changed));(out/'remates-data.json').write_text(json.dumps(parts,separators=(',',':')))
report={'mallas_modificadas':changed,'mallas_conservadas_exactamente':unchanged,'vertices_de_remate_dentro_del_boton':hidden,'radio_libre_central_cm':float(min(np.linalg.norm(np.array(endpoints)[:,:2],axis=1))),'paneles_altura_factor':bpy.data.objects['Panel Delantero']['factor_altura_paneles'],'color_inicial':'negro'}
(out/'validacion-remates.json').write_text(json.dumps(report,indent=2,ensure_ascii=False));print(json.dumps(report,ensure_ascii=False),flush=True)
