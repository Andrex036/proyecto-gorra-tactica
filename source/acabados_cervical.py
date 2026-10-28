"""Protector cervical con dos pliegues, diagonales abiertas y texto BOA.

Las costuras se construyen sobre la misma superficie del acolchado. Las
magnitudes de diseño se expresan en centímetros.
"""
import math
import bpy,bmesh
import numpy as np
from mathutils import Vector
import textil

LIMIT=1.06
HEIGHT=8.5

def edge(a):return max(0.,math.cos(a/LIMIT*math.pi/2))**.65

def diagonal(d):return 2.60+.91*d

def fold(x,index):
    q,curve,width=[(1.82,.16,4.6),(3.72,.20,6.3)][index]
    return q+curve*(1-(x/width)**2)

def smooth(t):
    t=max(0.,min(1.,t));return t*t*(3-2*t)

def y_at(x,d):
    vv=(d+.02)/HEIGHT
    a=math.asin(max(-.999,min(.999,x/(9.4-1.25*vv))))
    e=max(.000001,edge(a));v=vv/e
    base=(10.4-1.45*vv)*math.cos(a)
    envelope=max(0.,math.sin(math.pi*max(0.,min(1.,v))))
    inside=smooth((diagonal(d)-abs(x)+.12)/.24)
    q1,q2=fold(x,0),fold(x,1)
    if d<q1:phase=max(0.,d/max(.01,q1));bulge=.19*math.sin(math.pi*phase)**2
    elif d<q2:phase=(d-q1)/(q2-q1);bulge=.24*math.sin(math.pi*phase)**2
    else:phase=(d-q2)/max(.01,HEIGHT*e-.02-q2);bulge=.12*math.sin(math.pi*min(1.,max(0.,phase)))**2
    pad=inside*bulge+(1-inside)*.11*envelope
    groove=sum(.095*math.exp(-((d-fold(x,i))/.105)**2) for i in [0,1])*inside
    diag=.055*math.exp(-((abs(x)-diagonal(d))/.13)**2)
    fade=smooth((d+.02)/.30)*smooth((HEIGHT*e-.02-d)/.25)
    return base+(pad-groove-diag)*fade

def point(x,d):return np.array([x,y_at(x,d),-d],float)

def surface(a,v):
    e=edge(a);d=HEIGHT*e*v-.02;x=(9.4-1.25*v*e)*math.sin(a)
    return point(x,d)

def normal(x,d):
    eps=.002
    dx=(y_at(x+eps,d)-y_at(x-eps,d))/(2*eps)
    dd=(y_at(x,d+eps)-y_at(x,d-eps))/(2*eps)
    n=np.array([-dx,1.,dd]);return n/np.linalg.norm(n)

def on_surface(x,d,offset=.006):return point(x,d)+offset*normal(x,d)

def diagonal_end():
    lo=0.;hi=LIMIT
    for _ in range(60):
        a=(lo+hi)/2;p=surface(a,1);d=-p[2]
        if p[0]>diagonal(d):hi=a
        else:lo=a
    p=surface((lo+hi)/2,1)
    return -p[2]

END_DEPTH=diagonal_end()

def fold_end(index):
    lo=0.;hi=END_DEPTH
    for _ in range(50):
        d=(lo+hi)/2
        if d>fold(diagonal(d),index):hi=d
        else:lo=d
    return diagonal((lo+hi)/2)

def mesh_object(name,verts,faces,role,group='cervical'):
    collection=bpy.data.collections['GORRA | piezas editables']
    data=bpy.data.meshes.new(name);data.from_pydata((np.asarray(verts)*.01).tolist(),[],np.asarray(faces,dtype=int).tolist());data.update()
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    obj=bpy.data.objects.new(name,data);collection.objects.link(obj)
    obj['conjunto']=group;obj['material_role']=role;obj['detalle_fino']=True
    obj.parent=next(o for o in collection.objects if o.type=='EMPTY' and o.get('pieza')==('Protector cervical' if group=='cervical' else 'Dial y soporte'))
    mat=next(m for m in bpy.data.materials if m.get('role')==role);data.materials.append(mat)
    for p in data.polygons:p.use_smooth=True
    textil.uv_for_mesh(data,obj.matrix_world,group)
    return obj

def make_shell():
    A=160;B=104
    a=np.linspace(-LIMIT,LIMIT,A+1)
    vertices=[surface(-LIMIT,0)]
    for ai in a[1:-1]:
        for v in np.linspace(0,1,B+1):vertices.append(surface(float(ai),float(v)))
    vertices.append(surface(LIMIT,0));top=np.array(vertices);n=len(top);faces=[]
    for j in range(B):faces.append((0,1+j,1+j+1))
    for i in range(A-2):
        for j in range(B):
            q=1+i*(B+1)+j;r=q+B+1;faces.extend(((q,r,q+1),(q+1,r,r+1)))
    for j in range(B):faces.append((n-1,1+(A-2)*(B+1)+j+1,1+(A-2)*(B+1)+j))
    f=np.array(faces,dtype=int);tri=top[f];norm=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
    if norm[:,1].mean()<0:f=f[:,::-1]
    # El forro sigue la curvatura de la nuca, sin copiar los surcos del acolchado.
    # Evita que el desplazamiento de las normales de pliegues estrechos cruce la malla.
    def base_y(x,d):
        v=(d+.02)/HEIGHT;rx=9.4-1.25*v;ry=10.4-1.45*v
        return ry*math.sqrt(max(.001,1-(x/rx)**2))
    def base_normal(x,d):
        eps=.001
        dx=(base_y(x+eps,d)-base_y(x-eps,d))/(2*eps)
        dd=(base_y(x,d+eps)-base_y(x,d-eps))/(2*eps)
        out=np.array([-dx,1.,dd]);return out/np.linalg.norm(out)
    bases=top.copy();bases[:,1]=[base_y(p[0],-p[2]) for p in top]
    normals=np.array([base_normal(p[0],-p[2]) for p in top]);back=bases-.28*normals
    edges=np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]);keys=np.sort(edges,axis=1)
    _,first,count=np.unique(keys,axis=0,return_index=True,return_counts=True);bd=edges[first[count==1]]
    successor={int(a):int(b) for a,b in bd};boundary=[int(bd[0,0])]
    while successor[boundary[-1]]!=boundary[0]:boundary.append(successor[boundary[-1]])
    boundary=np.asarray(boundary);K=len(boundary);front_edge=top[boundary];back_edge=back[boundary]
    tangent=np.roll(front_edge,-1,axis=0)-np.roll(front_edge,1,axis=0);tangent/=np.linalg.norm(tangent,axis=1)[:,None]
    outward=np.cross(tangent,normals[boundary]);outward/=np.linalg.norm(outward,axis=1)[:,None]
    center=(front_edge+back_edge)*.5;half=(front_edge-back_edge)*.5
    vertices=[top,back];rings=[boundary];profile=[front_edge];steps=8
    # Remate redondeado dentro del ribete existente: no queda un canto plano abierto.
    for k in range(1,steps):
        theta=math.pi*k/steps
        ring=center+half*math.cos(theta)+.045*outward*math.sin(theta)
        start=sum(len(v) for v in vertices);vertices.append(ring);rings.append(np.arange(start,start+K));profile.append(ring)
    rings.append(boundary+n);profile.append(back_edge)
    side=[]
    for k in range(steps):
        for j in range(K):
            jj=(j+1)%K;a,b,c,d=rings[k][j],rings[k][jj],rings[k+1][j],rings[k+1][jj]
            side.extend([(b,a,c),(b,c,d)])
    faces=np.vstack([f,f[:,::-1]+n,np.asarray(side)])
    obj=mesh_object('06 Protector cervical acolchado',np.vstack(vertices),faces,'fabric')
    # Trama más suave en el forro, con UV propias para el canto redondeado.
    lining=bpy.data.materials.get('Textil | lining')
    if lining is None:
        lining=obj.data.materials[0].copy();lining.name='Textil | lining';lining['role']='lining'
    for node in lining.node_tree.nodes:
        if node.type=='NORMAL_MAP':node.inputs['Strength'].default_value=.25
    lining.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.96
    obj.data.materials.append(lining)
    for poly in list(obj.data.polygons)[len(f):]:poly.material_index=1
    uv=obj.data.uv_layers.active
    perimeter=np.r_[0,np.cumsum(np.linalg.norm(np.roll(front_edge,-1,axis=0)-front_edge,axis=1))]
    across=np.zeros((steps+1,K))
    for k in range(1,steps+1):across[k]=across[k-1]+np.linalg.norm(profile[k]-profile[k-1],axis=1)
    row_for_vertex={int(index):(k,j) for k,ring in enumerate(rings) for j,index in enumerate(ring)}
    for poly in list(obj.data.polygons)[2*len(f):]:
        js=[row_for_vertex[int(obj.data.loops[li].vertex_index)][1] for li in poly.loop_indices]
        wraps=max(js)-min(js)>K/2
        for li in poly.loop_indices:
            k,j=row_for_vertex[int(obj.data.loops[li].vertex_index)]
            u=perimeter[-1] if wraps and j==0 else perimeter[j]
            uv.data[li].uv=(u/textil.TILE_CM,across[k,j]/textil.TILE_CM)
    obj['uv_preservar']=True;obj['normal_bits']=16
    obj['construccion']='Exterior acolchado conservado; forro liso independiente, cerrado y con canto redondeado. UV del forro y remates a escala física.'
    return obj

def tube_paths(name,paths,radius,role,closed=False):
    data=bpy.data.curves.new(name,'CURVE');data.dimensions='3D';data.resolution_u=1;data.bevel_depth=radius*.01;data.bevel_resolution=2;data.use_fill_caps=True
    for path in paths:
        sp=data.splines.new('POLY');sp.points.add(len(path)-1)
        for v,p in zip(sp.points,path):v.co=(*[float(x)*.01 for x in p],1)
        sp.use_cyclic_u=closed
    collection=bpy.data.collections['GORRA | piezas editables'];obj=bpy.data.objects.new(name,data);collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj;bpy.ops.object.convert(target='MESH')
    obj=bpy.context.object;obj['conjunto']='cervical';obj['material_role']=role;obj['detalle_fino']=True
    obj.parent=next(o for o in collection.objects if o.type=='EMPTY' and o.get('pieza')=='Protector cervical')
    obj.data.materials.append(next(m for m in bpy.data.materials if m.get('role')==role))
    for p in obj.data.polygons:p.use_smooth=True
    textil.uv_for_mesh(obj.data,obj.matrix_world,'cervical')
    return obj

def stitch_path(mapper,spacing=.16,radius=.012):
    dense=np.array([mapper(t) for t in np.linspace(0,1,1001)])
    arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(dense,axis=0),axis=1))]
    total=arc[-1];n=max(2,round(total/spacing));paths=[]
    for i in range(n):
        ds=total*(i+.5+np.linspace(-.31,.31,4))/n
        ts=np.interp(ds,arc,np.linspace(0,1,1001));paths.append([mapper(float(t)) for t in ts])
    return paths

def make_cervical():
    model=bpy.data.collections['GORRA | piezas editables']
    for o in list(model.objects):
        if o.type=='MESH' and o.get('conjunto')=='cervical':
            old=o.data;bpy.data.objects.remove(o,do_unlink=True)
            if old.users==0:bpy.data.meshes.remove(old)
    make_shell()
    upper=[surface(float(a),0) for a in np.linspace(-LIMIT,LIMIT,241)]
    lower=[surface(float(a),1) for a in np.linspace(LIMIT,-LIMIT,241)[1:-1]]
    tube_paths('Ribete continuo del protector cervical',[upper+lower],.105,'trim',True)
    stitches=[]
    for sign,label in [(-1,'izquierdo'),(1,'derecho')]:
        path=[on_surface(sign*diagonal(float(d)),float(d),.026) for d in np.linspace(-.02,END_DEPTH,181)]
        tube_paths('Unión diagonal cervical '+label,[path],.080,'fabric')
        for offset in [-.13,.13]:
            def mapper(t,sign=sign,offset=offset):
                d=.04+(END_DEPTH-.12)*t;x=sign*(diagonal(d)+offset)
                return on_surface(x,d,.006)
            stitches+=stitch_path(mapper,.16)
    for index in [0,1]:
        xmax=fold_end(index)-.075
        def mapper(t,index=index,xmax=xmax):
            x=-xmax+2*xmax*t;return on_surface(x,fold(x,index),.007)
        stitches+=stitch_path(mapper,.145)
    # Puntadas interiores del ribete: desplazamiento normal al contorno en X/Z.
    def outer(t):
        a=-LIMIT+.018+(2*LIMIT-.036)*t;p=surface(a,1);eps=.0001;dp=surface(a+eps,1)-surface(a-eps,1)
        inward=np.array([-dp[2],dp[0]]);inward/=np.linalg.norm(inward)
        x,z=p[[0,2]]+.19*inward;z=min(-.035,z)
        return on_surface(float(x),float(-z),.006)
    stitches+=stitch_path(outer,.145)
    tube_paths('Puntadas integradas del protector cervical',stitches,.012,'fabric')
    return {o.name for o in model.objects if o.type=='MESH' and o.get('conjunto')=='cervical'}

def make_boa():
    model=bpy.data.collections['GORRA | piezas editables'];name='BOA | letras del botón del dial'
    if name in bpy.data.objects:bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
    center=bpy.data.objects['Dial centro']
    data=bpy.data.curves.new('BOA | texto original','FONT');data.body='BOA';data.align_x='CENTER';data.align_y='CENTER';data.size=.0044;data.extrude=.000045;data.bevel_depth=.000008;data.bevel_resolution=2;data.resolution_u=12
    obj=bpy.data.objects.new(name,data);model.objects.link(obj);bpy.context.view_layer.update()
    # Ajuste proporcional: rótulo pequeño y centrado como en la referencia.
    coords=np.array([tuple(v) for v in obj.bound_box]);width=coords[:,0].ptp();factor=.0095/width
    data.size*=factor
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj;bpy.ops.object.convert(target='MESH');obj=bpy.context.object
    coords=np.array([tuple(v.co) for v in obj.data.vertices]);shift=(coords[:,:2].min(0)+coords[:,:2].max(0))/2
    for v in obj.data.vertices:v.co.x-=shift[0];v.co.y-=shift[1];v.co.z+=max(vv.co.z for vv in center.data.vertices)-.000008
    obj.matrix_world=center.matrix_world.copy();obj.parent=center.parent
    mat=bpy.data.materials.get('BOA | marca negra') or bpy.data.materials.new('BOA | marca negra');mat.use_nodes=True;mat['role']='boa';rgb=textil.linear_hex('080b0d');mat.diffuse_color=(*rgb,1)
    p=mat.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*rgb,1);p.inputs['Roughness'].default_value=.64;p.inputs['Metallic'].default_value=.05
    obj.data.materials.append(mat);obj['conjunto']='dial';obj['material_role']='boa';obj['detalle_fino']=True;obj['texto']='BOA'
    textil.uv_for_mesh(obj.data,obj.matrix_world,'dial')
    return obj

def aplicar():
    bpy.context.scene.frame_set(1);new=make_cervical();new.add(make_boa().name);bpy.context.view_layer.update();return new
