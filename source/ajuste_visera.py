"""Ajuste localizado de la visera; coordenadas Blender en centímetros.

Mantiene el contorno y anclaje, aumenta la caída y añade 1° de inclinación.
Las hebras mantienen el margen frontal hasta los remates junto a la copa.
Los laureles se desplazan hacia el interior para respetar ese recorrido.
"""
import numpy as np
from math import pi
from functools import lru_cache

INCLINACION_ADICIONAL_GRADOS = 1.0
CAIDA_ADICIONAL_CM = .40
CURVA_TRANSVERSAL_ADICIONAL = .012


def superficie_base(x, y):
    x = np.clip(x, -8.9, 8.9)
    yi = -10.4*np.sqrt(np.maximum(.001, 1-(x/9.4)**2))
    shape = np.maximum(0, 1-np.abs(x/8.9)**2.4)**(1/2.4)
    end_y = -10.4*np.sqrt(1-(8.9/9.4)**2)
    outer = end_y+(-16.7-end_y)*shape
    v = np.divide(y-yi, outer-yi, out=np.zeros_like(x), where=np.abs(outer-yi)>1.e-7)
    v = np.clip(v, 0, 1.12)
    return yi, shape, v


def deformar_superficie(points):
    points = np.asarray(points, dtype=np.float64)
    x,y,z = points.T
    yi,shape,v = superficie_base(x,y)
    extra = -(CURVA_TRANSVERSAL_ADICIONAL*x*x*v+CAIDA_ADICIONAL_CM*v*v)*shape
    a = np.deg2rad(INCLINACION_ADICIONAL_GRADOS)
    dy=y-yi;dz=z+extra+.05
    return np.column_stack((x, yi+dy*np.cos(a)-dz*np.sin(a), -.05+dy*np.sin(a)+dz*np.cos(a)))


def visor_base(theta, v=.91, off=.13):
    x=8.9*np.sin(theta)
    yi=-10.4*np.sqrt(np.maximum(.001,1-(x/9.4)**2))
    shape=np.maximum(0,1-np.abs(np.sin(theta))**2.4)**(1/2.4)
    end_y=-10.4*np.sqrt(1-(8.9/9.4)**2)
    outer=end_y+(-16.7-end_y)*shape
    return np.column_stack((x,yi*(1-v)+outer*v,-.05-(.020*x*x*v+1.10*v*v)*shape+off))


# Margen sobre la superficie: la misma separación que tenía el frente.
MARGEN_BORDADO_CM = .62288
DESPLAZAMIENTO_LAURELES_CM = .70


def altura_base_xy(xy):
    x,y=np.asarray(xy).T
    _,shape,v=superficie_base(x,y)
    return -.05-(.020*x*x*v+1.10*v*v)*shape


def superficie_xy(xy):
    return deformar_superficie(np.column_stack((xy,altura_base_xy(xy))))


def borde_exterior(theta):
    return deformar_superficie(visor_base(theta,v=1,off=0))


def distancia_borde(points,theta):
    # Punto más cercano del borde, por Newton vectorizado y acotado.
    q=theta.copy();eps=1.e-5
    for _ in range(10):
        p=borde_exterior(q);plus=borde_exterior(q+eps);minus=borde_exterior(q-eps)
        d=(plus-minus)/(2*eps);dd=(plus+minus-2*p)/(eps*eps)
        delta=p-points;first=np.sum(delta*d,axis=1)
        second=np.maximum(np.sum(d*d+delta*dd,axis=1),1.e-6)
        q=np.clip(q-np.clip(first/second,-.06,.06),-pi/2+.00003,pi/2-.00003)
    return np.linalg.norm(borde_exterior(q)-points,axis=1)


@lru_cache(maxsize=1)
def recorrido_bordado():
    theta=np.linspace(-pi/2+.0001,pi/2-.0001,4097)
    edge=visor_base(theta,v=1,off=0)[:,:2]
    dt=np.gradient(edge,axis=0)
    inward=np.column_stack((-dt[:,1],dt[:,0]));inward/=np.linalg.norm(inward,axis=1)[:,None]
    lo=np.zeros(len(theta));hi=np.full(len(theta),.8)
    for _ in range(23):
        distance=(lo+hi)*.5
        xy=edge+inward*distance[:,None]
        actual=distancia_borde(superficie_xy(xy),theta)
        lo=np.where(actual<MARGEN_BORDADO_CM,distance,lo)
        hi=np.where(actual>=MARGEN_BORDADO_CM,distance,hi)
    xy=edge+inward*((lo+hi)*.5)[:,None]
    x,y=xy.T
    yi=-10.4*np.sqrt(np.maximum(.001,1-(x/9.4)**2))
    outer=-10.4*np.sqrt(1-(8.9/9.4)**2)
    outer+=(-16.7-outer)*np.maximum(0,1-np.abs(x/8.9)**2.4)**(1/2.4)
    v=(y-yi)/(outer-yi)
    # Terminar en el encuentro con la copa, antes de que se agote el margen.
    valid=(v>=.025)&(v<=1)&(np.abs(x)<8.9)
    xy=xy[valid];path=superficie_xy(xy)
    length=np.concatenate(([0],np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))))
    return xy,length/length[-1]


def centro_trenza(t,phase,nuevo=False):
    if nuevo:
        xy,arc=recorrido_bordado()
        uv=np.column_stack([np.interp(t,arc,xy[:,i]) for i in (0,1)])
        p=superficie_xy(uv)
        eps=1.e-4
        dx=superficie_xy(uv+[eps,0])-superficie_xy(uv-[eps,0])
        dy=superficie_xy(uv+[0,eps])-superficie_xy(uv-[0,eps])
        normal=np.cross(dx,dy);normal/=np.linalg.norm(normal,axis=1)[:,None]
        ta=np.maximum(0,t-1.e-5);tb=np.minimum(1,t+1.e-5)
        uva=np.column_stack([np.interp(ta,arc,xy[:,i]) for i in (0,1)])
        uvb=np.column_stack([np.interp(tb,arc,xy[:,i]) for i in (0,1)])
        dt=superficie_xy(uvb)-superficie_xy(uva);tangent=dt/np.linalg.norm(dt,axis=1)[:,None]
        lateral=np.cross(normal,tangent)
        fade=np.minimum(1,np.minimum(t,1-t)/.025);fade=fade*fade*(3-2*fade)
        wave=2*pi*80*t+phase
        p+=normal*(.08+.05*fade+.065*np.sin(wave)*fade)[:,None]
        p+=lateral*(.08*np.cos(wave)*fade)[:,None]
        return p
    theta=-1.44+2.88*t
    p=visor_base(theta)
    tangent=visor_base(theta+.001)-visor_base(theta-.001)
    normal=np.column_stack((-tangent[:,1],tangent[:,0],np.zeros(len(t))))
    normal/=np.linalg.norm(normal,axis=1)[:,None]
    wave=2*pi*80*t+phase
    p+=normal*(.08*np.cos(wave))[:,None]
    p[:,2]+=.065*np.sin(wave)
    return p


def desplazar_laureles(points):
    p=np.array(points,dtype=np.float64,copy=True)
    base=altura_base_xy(p[:,:2])
    p[:,0]-=np.sign(p[:,0])*DESPLAZAMIENTO_LAURELES_CM
    p[:,2]+=altura_base_xy(p[:,:2])-base
    return deformar_superficie(p)


def rotar_entre(vectors,a,b):
    """Rotación mínima entre tangentes, conservando el grosor del cordón."""
    cross=np.cross(a,b);dot=np.sum(a*b,axis=1)
    return vectors+np.cross(cross,vectors)+np.cross(cross,np.cross(cross,vectors))/(1+dot)[:,None]


def deformar_trenza(points,phase=0,normals=None):
    points=np.asarray(points,dtype=np.float64)
    ts=np.linspace(0,1,1401);old=centro_trenza(ts,phase);new=centro_trenza(ts,phase,True)
    nearest=[]
    for k in range(0,len(points),256):
        d=points[k:k+256,None,:]-old[None,:,:]
        nearest.extend(np.argmin(np.sum(d*d,axis=2),axis=1))
    ids=np.asarray(nearest)
    cand=np.clip(np.column_stack((ids-1,ids)),0,len(ts)-2)
    a=old[cand];d=old[cand+1]-a
    u=np.clip(np.sum((points[:,None,:]-a)*d,axis=2)/np.sum(d*d,axis=2),0,1)
    cp=a+d*u[:,:,None];best=np.argmin(np.sum((points[:,None,:]-cp)**2,axis=2),axis=1)
    ix=np.arange(len(points));seg=cand[ix,best];frac=u[ix,best]
    origin=cp[ix,best];dest=new[seg]+(new[seg+1]-new[seg])*frac[:,None]
    ta=old[seg+1]-old[seg];tb=new[seg+1]-new[seg]
    ta/=np.linalg.norm(ta,axis=1)[:,None];tb/=np.linalg.norm(tb,axis=1)[:,None]
    result=dest+rotar_entre(points-origin,ta,tb)
    nout=None if normals is None else rotar_entre(np.asarray(normals),ta,tb)
    return result,nout


def ajustar(points,name,normals=None):
    if 'trenza perimetral visera' in name.lower():
        return deformar_trenza(points,pi if name.endswith('.001') else 0,normals)
    points=np.asarray(points,dtype=np.float64)
    transformar=desplazar_laureles if any(word in name.lower() for word in ['laurel','nervadura']) else deformar_superficie
    result=transformar(points);nout=None
    if normals is not None:
        eps=1.e-4;basis=np.eye(3)*eps
        jac=np.stack([(transformar(points+d)-transformar(points-d))/(2*eps) for d in basis],axis=2)
        nout=np.linalg.solve(np.transpose(jac,(0,2,1)),np.asarray(normals)[...,None])[...,0]
    if nout is not None:nout/=np.maximum(np.linalg.norm(nout,axis=1)[:,None],1.e-12)
    return result,nout
