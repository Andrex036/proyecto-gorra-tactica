"""Remates independientes bajo el botón; geometría en centímetros.

Conserva las cuatro rutas y la copa. Extiende sólo el extremo superior de
las costuras y completa el pespunte sin reunir los hilos en el eje central.
"""
import math
import bpy,bmesh,numpy as np
from mathutils import Vector
from proporcion_copa import coordenadas,escribir,altura,suave
import textil

ANGLES=[-math.pi/6,math.pi/6,5*math.pi/6,7*math.pi/6]

def punto(r,a,offset,base):
    lo,hi=0,math.pi/2
    def surface(t):
        rr=max(0,math.cos(t))**.85
        p=np.array([9.4*rr*math.cos(a),10.4*rr*math.sin(a),11.6*math.sin(t)])
        n=np.array([p[0]/9.4**2,p[1]/10.4**2,max(.1,p[2])/11.6**2]);p+=offset*n/np.linalg.norm(n)
        p[2]=altura(p[2],base)
        return p
    for _ in range(45):
        mid=(lo+hi)/2
        if np.linalg.norm(surface(mid)[:2])>r:lo=mid
        else:hi=mid
    return surface((lo+hi)/2)

def componentes(bm):
    pending=set(bm.verts);out=[]
    while pending:
        first=pending.pop();part=[first];queue=[first]
        while queue:
            v=queue.pop()
            for e in v.link_edges:
                w=e.other_vert(v)
                if w in pending:pending.remove(w);part.append(w);queue.append(w)
        out.append(part)
    return out

def tubo(bm,points,radius=.022):
    rings=[]
    for i,p in enumerate(points):
        tangent=Vector(points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized()
        side=tangent.cross(Vector((0,0,1))).normalized();up=side.cross(tangent).normalized()
        rings.append([bm.verts.new((Vector(p)+(side*math.cos(j*math.tau/6)+up*math.sin(j*math.tau/6))*radius)*.01) for j in range(6)])
    for a,b in zip(rings,rings[1:]):
        for j in range(6):bm.faces.new((a[j],a[(j+1)%6],b[(j+1)%6],b[j]))
    bm.faces.new(tuple(reversed(rings[0])));bm.faces.new(tuple(rings[-1]))

def aplicar():
    scene=bpy.context.scene;scene.frame_set(1);bpy.context.view_layer.update()
    button=bpy.data.objects['03 Botón superior']
    if button.get('remates_independientes'):return []
    panels=[o for o in bpy.data.objects if o.name in ['Panel Delantero','Panel Trasero','Panel Lateral Izquierdo','Panel Lateral Derecho']]
    base=min(coordenadas(o)[1][:,2].min() for o in panels)
    changed=[]
    for n,a in zip([1,2,4,5],ANGLES):
        o=bpy.data.objects['Costura panel %02d'%n];local,p=coordenadas(o);q=p.copy()
        # El tubo original tiene anillos de ocho vértices, incluidas las tapas.
        assert len(p)%8==0
        for first in range(0,len(p),8):
            ids=slice(first,first+8);center=p[ids].mean(0);r=np.linalg.norm(center[:2])
            if r<2:
                new_r=r-(.6545-.32)*float(suave((2-r)/(2-.6545)))
                q[ids]+=punto(new_r,a,.035,base)-punto(r,a,.035,base)
        escribir(o,local,q)
        bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-8)
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
        o['remate_bajo_boton']=True;o['uv_preservar']=True;o['normal_bits']=16;changed.append(o.name)
    for o in list(bpy.data.objects):
        if not o.name.startswith('Puntadas dobles de los paneles |'):continue
        assert np.allclose(np.asarray(o.matrix_world),np.eye(4))
        bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-8)
        rows={}
        for island in componentes(bm):
            center=np.mean([tuple(v.co*100) for v in island],axis=0);r=np.linalg.norm(center[:2])
            angle=math.atan2(center[1]/10.4,center[0]/9.4)
            a=min(ANGLES,key=lambda a:abs(math.atan2(math.sin(angle-a),math.cos(angle-a))))
            u=np.array([9.4*math.cos(a),10.4*math.sin(a)]);u/=np.linalg.norm(u);side=np.array([-u[1],u[0]])
            lateral=float(center[:2]@side);sign=1 if lateral>0 else -1
            key=(a,sign);along=float(center[:2]@u);rows[key]=min(rows.get(key,100),along)
            if r<3:
                shift=side*(sign*.085-lateral)*float(suave((3-r)/1.3))
                for v in island:v.co.x+=shift[0]*.01;v.co.y+=shift[1]*.01
        assert len(rows)==2
        for (a,sign),last in rows.items():
            u=np.array([9.4*math.cos(a),10.4*math.sin(a)]);u/=np.linalg.norm(u);side=np.array([-u[1],u[0],0])
            for center in np.arange(last-.30,.20,-.30):
                points=[punto(float(r),a,.068,base)+side*(sign*.085) for r in np.linspace(center+.095,center-.095,4)]
                tubo(bm,points)
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        for face in bm.faces:face.smooth=True
        assert all(len(e.link_faces)==2 for e in bm.edges),'Tubo abierto en '+o.name
        bm.to_mesh(o.data);bm.free();o.data.update()
        textil.uv_for_mesh(o.data,o.matrix_world,o['conjunto'])
        o['remate_bajo_boton']=True;o['uv_preservar']=True;o['normal_bits']=16;changed.append(o.name)
    button['remates_independientes']=True
    button['detalle_remates']='Cuatro costuras y ocho filas de puntadas independientes, ocultas bajo el botón.'
    return changed
