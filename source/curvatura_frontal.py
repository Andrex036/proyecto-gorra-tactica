"""Curvatura frontal total de 35°, con asiento protegido sin desplazamiento.

Se aplica una vez sobre la visera anterior a esta revisión. Coordenadas en cm.
El arco central frontal de 15 cm abarca 35° en total (17,5° por tangente).
El centro frontal y el contorno en planta mantienen sus coordenadas anteriores.
Se inmoviliza una franja de 8 mm junto a la unión elíptica con los paneles.
"""
import numpy as np
import ajuste_visera as base
from functools import lru_cache

ARCO_TOTAL_GRADOS=35.0
SEMIANCHO_FRONTAL_CM=7.5
FRANJA_PROTEGIDA_CM=.8
RADIO_FRONTAL_CM=SEMIANCHO_FRONTAL_CM/np.sin(np.deg2rad(ARCO_TOTAL_GRADOS/2))
ALTURA_CENTRO_CM=float(base.borde_exterior(np.array([0.]))[0,2])

def suave(t):
 t=np.clip(t,0,1)
 return t*t*t*(10+t*(-15+6*t))

def distancia_union(points):
 p=np.asarray(points);x=np.clip(p[:,0],-8.9,8.9)
 yi=-10.4*np.sqrt(np.maximum(.001,1-(x/9.4)**2))
 return yi-p[:,1]

@lru_cache(maxsize=1)
def perfil_lateral():
 """Empalme C2 por longitud del borde: evita el pliegue al regresar a la copa."""
 from scipy.interpolate import CubicSpline,BPoly
 edge=base.borde_exterior(np.linspace(0,np.pi/2,50001))
 arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(edge[:,:2],axis=0),axis=1))]
 xx=CubicSpline(arc,edge[:,0]);zz=CubicSpline(arc,edge[:,2])
 start=float(np.interp(SEMIANCHO_FRONTAL_CM,edge[:,0],arc))
 # Conservar también el borde más cercano a los remates del cordón: su
 # separación se mide hasta el borde, aunque ese borde quede fuera del asiento.
 fin_protegido=FRANJA_PROTEGIDA_CM+base.MARGEN_BORDADO_CM+.4
 end=float(np.interp(fin_protegido,distancia_union(edge)[::-1],arc[::-1]))
 x=float(xx(start));dx=float(xx(start,1));ddx=float(xx(start,2))
 root=np.sqrt(RADIO_FRONTAL_CM**2-x*x)
 z=ALTURA_CENTRO_CM+root-RADIO_FRONTAL_CM
 dz=-x/root*dx
 ddz=-(RADIO_FRONTAL_CM**2/root**3)*dx*dx-x/root*ddx
 spline=BPoly.from_derivatives([start,end],[[z,dz,ddz],[zz(end),zz(end,1),zz(end,2)]])
 return CubicSpline(edge[:,0],arc),spline,end

def desplazamiento(x,y):
 x=np.asarray(x);y=np.asarray(y);xc=np.clip(x,-8.9,8.9)
 yi=-10.4*np.sqrt(np.maximum(.001,1-(xc/9.4)**2))
 old=base.borde_exterior(np.arcsin(xc/8.9))
 depth=yi-y;length=yi-old[:,1]
 frontal=ALTURA_CENTRO_CM+np.sqrt(np.maximum(0,RADIO_FRONTAL_CM**2-xc*xc))-RADIO_FRONTAL_CM
 arc_of_x,lateral,arc_end=perfil_lateral();arc=arc_of_x(np.abs(xc))
 frontal=np.where(np.abs(xc)>SEMIANCHO_FRONTAL_CM,lateral(np.minimum(arc,arc_end)),frontal)
 frontal=np.where(arc>=arc_end,old[:,2],frontal)
 peso=suave((depth-FRANJA_PROTEGIDA_CM)/np.maximum(.001,length-FRANJA_PROTEGIDA_CM))
 peso=np.where(length>FRANJA_PROTEGIDA_CM,peso,0)
 return (frontal-old[:,2])*peso

def deformar(points):
 p=np.array(points,dtype=np.float64,copy=True)
 p[:,2]+=desplazamiento(p[:,0],p[:,1])
 return p

def gradiente(xy):
 p=np.asarray(xy);h=1e-4;x,y=p.T
 return np.column_stack(((desplazamiento(x+h,y)-desplazamiento(x-h,y))/(2*h),
                         (desplazamiento(x,y+h)-desplazamiento(x,y-h))/(2*h)))

@lru_cache(maxsize=1)
def recorrido_bordado():
 from scipy.spatial import cKDTree
 xy,arc=base.recorrido_bordado()
 tangent=np.gradient(xy,axis=0)
 inward=np.column_stack((-tangent[:,1],tangent[:,0]));inward/=np.linalg.norm(inward,axis=1)[:,None]
 edge=deformar(base.borde_exterior(np.linspace(-np.pi/2,np.pi/2,60001)))
 tree=cKDTree(edge);lo=np.full(len(xy),-.4);hi=np.full(len(xy),.4)
 for _ in range(22):
  shift=(lo+hi)/2
  p=deformar(base.superficie_xy(xy+inward*shift[:,None]))
  distance=tree.query(p)[0]
  lo=np.where(distance<base.MARGEN_BORDADO_CM,shift,lo)
  hi=np.where(distance>=base.MARGEN_BORDADO_CM,shift,hi)
 depth=distancia_union(base.superficie_xy(xy))
 blend=suave((depth-FRANJA_PROTEGIDA_CM)/.4)
 result=xy+inward*((lo+hi)/2*blend)[:,None]
 return result,arc

def centro_trenza(t,phase):
 xy,arc=recorrido_bordado()
 uv=np.column_stack([np.interp(t,arc,xy[:,i]) for i in (0,1)])
 def surface(q):return deformar(base.superficie_xy(q))
 p=surface(uv);eps=1e-4
 dx=surface(uv+[eps,0])-surface(uv-[eps,0]);dy=surface(uv+[0,eps])-surface(uv-[0,eps])
 normal=np.cross(dx,dy);normal/=np.linalg.norm(normal,axis=1)[:,None]
 ta=np.maximum(0,t-1e-5);tb=np.minimum(1,t+1e-5)
 uva=np.column_stack([np.interp(ta,arc,xy[:,i]) for i in (0,1)])
 uvb=np.column_stack([np.interp(tb,arc,xy[:,i]) for i in (0,1)])
 tangent=surface(uvb)-surface(uva);tangent/=np.linalg.norm(tangent,axis=1)[:,None]
 lateral=np.cross(normal,tangent)
 fade=np.minimum(1,np.minimum(t,1-t)/.025);fade=fade*fade*(3-2*fade)
 wave=2*np.pi*80*t+phase
 p+=normal*(.08+.05*fade+.065*np.sin(wave)*fade)[:,None]
 p+=lateral*(.08*np.cos(wave)*fade)[:,None]
 old=base.centro_trenza(t,phase,True)
 blend=suave((distancia_union(old)-FRANJA_PROTEGIDA_CM)/.4)
 return old+(p-old)*blend[:,None]

def ajustar_trenza(points,phase):
 from scipy.spatial import cKDTree
 ts=np.linspace(0,1,1401);old=base.centro_trenza(ts,phase,True);new=centro_trenza(ts,phase)
 ids=cKDTree(old).query(points)[1]
 cand=np.clip(np.column_stack((ids-1,ids)),0,len(ts)-2)
 a=old[cand];delta=old[cand+1]-a
 frac=np.clip(np.sum((points[:,None,:]-a)*delta,axis=2)/np.sum(delta*delta,axis=2),0,1)
 cp=a+delta*frac[:,:,None];best=np.argmin(np.sum((points[:,None,:]-cp)**2,axis=2),axis=1)
 ix=np.arange(len(points));seg=cand[ix,best];u=frac[ix,best]
 origin=cp[ix,best];destination=new[seg]+(new[seg+1]-new[seg])*u[:,None]
 ta=old[seg+1]-old[seg];tb=new[seg+1]-new[seg]
 ta/=np.linalg.norm(ta,axis=1)[:,None];tb/=np.linalg.norm(tb,axis=1)[:,None]
 return destination+base.rotar_entre(points-origin,ta,tb)

def aplicar():
 import bpy
 model=bpy.data.collections['GORRA | piezas editables']
 body=bpy.data.objects['04 Visera redondeada con caída']
 if body.get('curvatura_frontal_total_grados'):
  raise RuntimeError('Usar el modelo base anterior a esta revisión para evitar deformaciones acumuladas.')
 bpy.context.scene.frame_set(1);report={};total_fixed=0
 for o in model.objects:
  if o.type!='MESH' or o.get('conjunto')!='visera':continue
  coords=np.empty(len(o.data.vertices)*3);o.data.vertices.foreach_get('co',coords)
  original=coords.reshape(-1,3);p=original*100
  protected=distancia_union(p)<=FRANJA_PROTEGIDA_CM
  result=deformar(p)
  if 'Trenza perimetral visera' in o.name:
   result=ajustar_trenza(p,np.pi if o.name.endswith('.001') else 0)
  elif o.name=='04 Visera redondeada con caída':
   n=len(p)//2;assert n*2==len(p)
   top,bottom=p[:n],p[n:];normal=(top-bottom)/np.linalg.norm(top-bottom,axis=1)[:,None]
   grad=gradiente(top[:,:2]);normal[:,:2]-=grad*normal[:,2,None]
   normal/=np.linalg.norm(normal,axis=1)[:,None]
   result[n:]=result[:n]-.25*normal
   pair_fixed=protected[:n]|protected[n:]
   protected[:n]=pair_fixed;protected[n:]=pair_fixed
  elif o.name=='Ribete exterior visera':
   rings=p[:-2].reshape(-1,12,3);old_center=rings.mean(1);new_center=deformar(old_center)
   ta=np.gradient(old_center,axis=0);tb=np.gradient(new_center,axis=0)
   ta/=np.linalg.norm(ta,axis=1)[:,None];tb/=np.linalg.norm(tb,axis=1)[:,None]
   offsets=rings-old_center[:,None,:]
   rotated=base.rotar_entre(offsets.reshape(-1,3),np.repeat(ta,12,axis=0),np.repeat(tb,12,axis=0)).reshape(rings.shape)
   result[:-2]=(new_center[:,None,:]+rotated).reshape(-1,3)
   # Los anillos de los remates se conservan completos para mantener su sección.
   ring_fixed=protected[:-2].reshape(-1,12).any(1)
   protected[:-2]=np.repeat(ring_fixed,12)
  converted=result*.01
  converted[protected]=original[protected]
  o.data.vertices.foreach_set('co',converted.reshape(-1));o.data.update()
  check=np.empty(len(coords));o.data.vertices.foreach_get('co',check)
  assert np.array_equal(check.reshape(-1,3)[protected],original[protected]),o.name
  report[o.name]={'vertices':len(p),'vertices_protegidos':int(protected.sum()),'desplazamiento_protegido_mm':0.0}
  total_fixed+=int(protected.sum())
  o['normal_bits']=16
 body['curvatura_frontal_total_grados']=ARCO_TOTAL_GRADOS
 body['tangente_frontal_grados']=ARCO_TOTAL_GRADOS/2
 body['franja_union_inmovil_cm']=FRANJA_PROTEGIDA_CM
 body['criterio_curvatura']='35° de arco frontal total; 17,5° por tangente en x=±7,5 cm.'
 body['laterales']='Transición C2 por longitud del contorno; continuidad de posición, tangente y curvatura.'
 body['acabado']='Curvatura frontal localizada; unión y franja de 8 mm conservadas vértice por vértice.'
 bpy.context.view_layer.update()
 return {'vertices_protegidos':total_fixed,'objetos':report}
