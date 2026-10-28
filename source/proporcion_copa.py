"""Reduce la altura útil de los cuatro paneles un 10%, con el asiento fijo.

La base de 4,5 mm, la visera, la banda y el protector cervical se conservan.
El escudo mantiene sus dimensiones X/Z y se adapta al nuevo apoyo frontal.
Los círculos de guía, el dial, BOA y las secciones de los cables no se aplastan.
Coordenadas de cálculo en centímetros; mallas de Blender en metros.
"""
import numpy as np
from ajuste_visera import rotar_entre

FACTOR_ALTURA=.9
BASE_FIJA_CM=.45
FIN_TRANSICION_CM=1.45

def suave(t):
 t=np.clip(t,0,1)
 return t*t*t*(10+t*(-15+6*t))

def altura(z,base):
 z=np.asarray(z)
 return z-(1-FACTOR_ALTURA)*(z-base)*suave((z-BASE_FIJA_CM)/(FIN_TRANSICION_CM-BASE_FIJA_CM))

def inversa_altura(z,base):
 lo=np.asarray(z).copy();hi=lo+2
 for _ in range(35):
  mid=(lo+hi)/2;mask=altura(mid,base)<z
  lo=np.where(mask,mid,lo);hi=np.where(mask,hi,mid)
 return (lo+hi)/2

def frontal_y(x,z):
 r=np.maximum(.001,1-(z/11.6)**2)**.425
 return -10.4*r*np.sqrt(np.maximum(.001,1-(x/(9.4*r))**2))

def coordenadas(o):
 a=np.empty(len(o.data.vertices)*3);o.data.vertices.foreach_get('co',a)
 local=a.reshape(-1,3);m=np.asarray(o.matrix_world)
 return local,(local@m[:3,:3].T+m[:3,3])*100

def escribir(o,local,world):
 inverse=np.asarray(o.matrix_world.inverted())
 result=(world*.01)@inverse[:3,:3].T+inverse[:3,3]
 _,old=coordenadas(o);same=np.all(world==old,axis=1);result[same]=local[same]
 o.data.vertices.foreach_set('co',result.reshape(-1));o.data.update()

def indices_grupos(o):
 result={g.name:[] for g in o.vertex_groups}
 names={g.index:g.name for g in o.vertex_groups}
 for v in o.data.vertices:
  for g in v.groups:
   if g.weight>.5:result[names[g.group]].append(v.index)
 return {k:np.array(v,dtype=int) for k,v in result.items()}

def aplicar():
 import bpy
 scene=bpy.context.scene;scene.frame_set(1);bpy.context.view_layer.update()
 model=bpy.data.collections['GORRA | piezas editables']
 panels=[bpy.data.objects[n] for n in ['Panel Delantero','Panel Trasero','Panel Lateral Izquierdo','Panel Lateral Derecho']]
 if panels[0].get('factor_altura_paneles'):
  raise RuntimeError('La reducción de altura ya está aplicada; usar un modelo anterior a esta revisión.')
 original={o.name:coordenadas(o) for o in model.objects if o.type=='MESH'}
 base=min(original[o.name][1][:,2].min() for o in panels)
 top=max(original[o.name][1][:,2].max() for o in panels)
 button_shift=float(altura(top,base)-top)
 for o in model.objects:
  if o.type!='MESH':continue
  group=o.get('conjunto');local,p=original[o.name];q=p.copy()
  if group.startswith('panel_'):
   q[:,2]=altura(p[:,2],base)
   if o.name=='03 Botón superior':q[:,2]=p[:,2]+button_shift
   elif o.name.startswith(('Ojal ventilación','Interior ojal')):
    anchor=original['Ojal ventilación '+o.name[-2:]][1].mean(0)
    q[:,2]=p[:,2]+float(altura(anchor[2],base)-anchor[2])
  elif group=='escudo':
   shift=float(altura(4.6,base)-4.6);q[:,2]+=shift
   q[:,1]+=frontal_y(p[:,0],inversa_altura(q[:,2],base))-frontal_y(p[:,0],p[:,2])
   o['adaptacion_copa']='Escudo con ancho, alto y UV originales; asiento adaptado a la copa de altura 90%.'
  elif group=='ajuste':
   q[:,2]=altura(p[:,2],base);groups=indices_grupos(o)
   center=p[groups['Dial cara']].mean(0);dial_shift=float(altura(center[2],base)-center[2])
   for name,ids in groups.items():
    if not len(ids):continue
    if name.startswith(('10 Dial','Dial ','Aro frontal','Estrías finas','BOA')):
     q[ids]=p[ids];q[ids,2]+=dial_shift
    elif name.startswith('Guía cable'):
     anchor=p[ids].mean(0);q[ids]=p[ids];q[ids,2]+=float(altura(anchor[2],base)-anchor[2])
    elif name.startswith(('Cable ','Retorno de guías','Paso interior')):
     assert len(ids)%8==0,name
     rings=p[ids].reshape(-1,8,3);old_center=rings.mean(1);new_center=old_center.copy();new_center[:,2]=altura(old_center[:,2],base)
     a=np.gradient(old_center,axis=0);b=np.gradient(new_center,axis=0)
     a/=np.linalg.norm(a,axis=1)[:,None];b/=np.linalg.norm(b,axis=1)[:,None]
     offset=rotar_entre((rings-old_center[:,None,:]).reshape(-1,3),np.repeat(a,8,axis=0),np.repeat(b,8,axis=0))
     q[ids]=(new_center[:,None,:]+offset.reshape(rings.shape)).reshape(-1,3)
   o['adaptacion_copa']='Soportes y cableado acompañan a los paneles; dial, BOA y guías conservan sus proporciones.'
  else:continue
  escribir(o,local,q)
  o['normal_bits']=16
 report={}
 for o in panels:
  before=original[o.name][1];_,after=coordenadas(o)
  h0=float(np.ptp(before[:,2]));h1=float(np.ptp(after[:,2]));ratio=h1/h0
  assert abs(ratio-FACTOR_ALTURA)<1e-5,(o.name,ratio)
  assert np.allclose(after[:,:2],before[:,:2],atol=1e-6)
  mask=before[:,2]<=BASE_FIJA_CM
  assert np.array_equal(after[mask],before[mask]),o.name
  o['factor_altura_paneles']=FACTOR_ALTURA;o['altura_anterior_cm']=h0;o['altura_actual_cm']=h1
  report[o.name]={'altura_antes_cm':h0,'altura_despues_cm':h1,'factor':ratio,'base_sin_desplazamiento':True}
 bpy.context.view_layer.update()
 return report
