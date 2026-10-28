"""Cables exteriores entre las cuatro guías; retorno al dial por el interior."""
import math
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import paneles_copa

RADIUS=.052  # cm, mismo grosor del cable lateral original


def group_indices(obj,name):
 group=obj.vertex_groups.get(name)
 if group is None:raise ValueError('Falta el grupo: '+name)
 return {v.index for v in obj.data.vertices if any(g.group==group.index and g.weight>.5 for g in v.groups)}


def tree_from_meshes(objects,exclude=None):
 verts=[];faces=[]
 for obj in objects:
  offset=len(verts);verts.extend(obj.matrix_world@v.co for v in obj.data.vertices)
  faces.extend(tuple(offset+i for i in f.vertices) for f in obj.data.polygons if exclude is None or obj not in exclude or not any(i in exclude[obj] for i in f.vertices))
 return BVHTree.FromPolygons(verts,faces)


def aplicar():
 scene=bpy.context.scene;scene.frame_set(1);bpy.context.view_layer.update()
 model=bpy.data.collections['GORRA | piezas editables']
 obj=next(o for o in model.objects if o.type=='MESH' and o.get('conjunto')=='ajuste')
 # Idempotente: solo se sustituyen los ocho cables laterales interiores.
 old_names=[g.name for g in obj.vertex_groups if g.name.startswith('Cable interior cruzado ')]
 if not old_names:return obj
 removed=set().union(*(group_indices(obj,n) for n in old_names))
 cable_indices=set().union(*(group_indices(obj,g.name) for g in obj.vertex_groups if g.name.startswith(('Cable ','Retorno de guías'))))
 panels=[o for o in model.objects if o.type=='MESH' and o.name.startswith('Panel Lateral ')]
 surface=tree_from_meshes(panels+[obj],{obj:cable_indices})
 added=[];paths={};anchors_out={};hidden_targets={}
 for sign,side in [(-1,'izquierdo'),(1,'derecho')]:
  anchors=[]
  for suffix in ('','.001','.002','.003'):
   members=group_indices(obj,'Guía cable '+side+suffix)
   center=sum((obj.matrix_world@obj.data.vertices[i].co for i in members),Vector())/len(members)
   anchors.append(center*100)
  anchors_out[side]=[tuple(p) for p in anchors]
  # Extremos del retorno interior, bajo la trabilla y alineados con los círculos.
  inner=[]
  for y in (-3,3):
   ids=sorted(group_indices(obj,'Retorno de guías '+side+str(y)))
   for ring in (ids[:8],ids[-8:]):inner.append(sum((obj.matrix_world@obj.data.vertices[i].co for i in ring),Vector())/8)
  hidden_targets[side]=[tuple(p*100) for p in inner]
  for k,(a,b) in enumerate([(0,2),(1,3),(0,3),(1,2)]):
   p,q=anchors[a],anchors[b];profile=[];N=192
   length=math.hypot(q.y-p.y,q.z-p.z);ny=-(q.z-p.z)/length;nz=(q.y-p.y)/length
   for j in range(N+1):
    t=j/N;y=p.y*(1-t)+q.y*t;z=p.z*(1-t)+q.z*t;height=0
    # Holgura sobre tela, fuelle y ribete; se evalúa también el ancho del cable.
    for d in (-1,-.75,-.4,0,.4,.75,1):
     hit,n,_,_=surface.ray_cast(Vector((sign*.30,(y+ny*d*RADIUS)*.01,(z+nz*d*RADIUS)*.01)),Vector((-sign,0,0)),.6)
     assert hit is not None
     height=max(height,sign*hit.x*100+RADIUS*math.sqrt(max(0,1-d*d))/max(.8,abs(n.x))+.005)
    profile.append((height,y,z))
   points=[]
   for j,(height,y,z) in enumerate(profile):
    height=max(profile[i][0]-.65*((i-j)*length/N)**2 for i in range(max(0,j-14),min(N,j+14)+1))
    if k==3:height+=.125*math.exp(-((j/N-.5)/.065)**2)
    # Cada punta termina exactamente en el centro del círculo de su guía.
    distance=min(j,N-j)*length/N
    if distance<.12:
     anchor=sign*(p.x if j<N/2 else q.x);blend=math.sin(math.pi/2*distance/.12)
     height=anchor+(height-anchor)*blend
    points.append(Vector((sign*height,y,z))*.01)
   points[0]=p*.01;points[-1]=q*.01
   name='Cable lateral visible '+side+' '+str(k+1)
   cable=paneles_copa.tube(name,points,RADIUS*.01,model);added.append(cable);paths[name]=[tuple(p*100) for p in points]
  for i,(p,q) in enumerate(zip(inner,anchors)):
   points=[p.lerp(q*.01,j/16) for j in range(17)]
   added.append(paneles_copa.tube('Paso interior de guía '+side+' '+str(i+1),points,.024*.01,model))
 # Borrar solo la geometría de los cables sustituidos, conservando UV y materiales.
 bm=bmesh.new();bm.from_mesh(obj.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.verts[i] for i in removed],context='VERTS');bm.to_mesh(obj.data);bm.free();obj.data.update()
 for name in old_names:obj.vertex_groups.remove(obj.vertex_groups[name])
 bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
 for part in added:
  group=part.vertex_groups.new(name=part.name);group.add(list(range(len(part.data.vertices))),1.,'REPLACE');part.select_set(True)
 bpy.context.view_layer.objects.active=obj;bpy.ops.object.join()
 # Unificar las ranuras repetidas creadas por los cables nuevos.
 mats=list(obj.data.materials);unique=[];mapping={}
 for i,m in enumerate(mats):
  if m not in unique:unique.append(m)
  mapping[i]=unique.index(m)
 indices=[mapping[p.material_index] for p in obj.data.polygons];obj.data.materials.clear()
 for m in unique:obj.data.materials.append(m)
 for p,i in zip(obj.data.polygons,indices):p.material_index=i
 obj['descripcion']='Dial BOA, soporte y ajustes laterales unidos. Cables exteriores de círculo a círculo; conexiones al dial ocultas dentro de la copa.'
 obj['cables_laterales']='Dos tramos horizontales y dos cruzados por lateral, con paso superior en el cruce.'
 obj['uv_preservar']=True;obj['normal_bits']=16;obj['exportar_por_material']=True
 return {'obj':obj,'paths':paths,'anchors':anchors_out,'inner':hidden_targets,'removed_vertices':len(removed)}
