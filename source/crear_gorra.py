"""Reconstrucción aproximada de la gorra de referencia. Ejecutar con Blender 4.3+.
Blender --background --python crear_gorra.py
Las medidas de diseño se expresan en cm y se convierten a metros al crear cada pieza.
"""
import bpy, bmesh, math, json, os, struct, base64, zlib, sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import textil
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from math import sin, cos, sqrt, pi, exp

def unificar_animacion_glb(path):
    """Unifica los movimientos de los conjuntos en una sola animación glTF."""
    with open(path,'rb') as f:raw=f.read()
    size=struct.unpack_from('<I',raw,12)[0]
    data=json.loads(raw[20:20+size]);animations=data.get('animations',[])
    if len(animations)<2:return
    combined={'name':'Separar y ensamblar','channels':[],'samplers':[]}
    for anim in animations:
        offset=len(combined['samplers'])
        combined['samplers'].extend(anim['samplers'])
        for channel in anim['channels']:
            channel=dict(channel);channel['sampler']+=offset;combined['channels'].append(channel)
    data['animations']=[combined]
    encoded=json.dumps(data,separators=(',',':'),ensure_ascii=False).encode('utf-8')
    encoded+=b' '*((-len(encoded))%4)
    rest=raw[20+size:]
    result=struct.pack('<III',0x46546c67,2,20+len(encoded)+len(rest))+struct.pack('<II',len(encoded),0x4e4f534a)+encoded+rest
    with open(path,'wb') as f:f.write(result)

OUT = os.environ.get("GORRA_OUTPUT_DIR", os.path.dirname(os.path.abspath(__file__)))
os.makedirs(OUT, exist_ok=True)
S = .01
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for c in list(bpy.data.collections):
    if c.name != 'Collection' and c.users == 0: bpy.data.collections.remove(c)
model = bpy.data.collections.new('GORRA | piezas editables')
bpy.context.scene.collection.children.link(model)
studio = bpy.data.collections.new('ESTUDIO | luces y cámaras')
bpy.context.scene.collection.children.link(studio)

def material(name, rgb, rough=.72):
    m=bpy.data.materials.new(name); m.diffuse_color=(*rgb,1)
    m.use_nodes=True; p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*rgb,1); p.inputs['Roughness'].default_value=rough
    return m
clay=material('Arcilla gris | cuerpo',(.42,.44,.47))
trim=material('Arcilla gris | bordes',(.33,.355,.39))
relief=material('Arcilla gris | relieve',(.59,.61,.64))
inset=material('Arcilla gris | fuelles',(.27,.29,.32))
hardware=material('Arcilla gris | mecanismo',(.34,.36,.4),.5)
thread=material('Arcilla gris | costuras',(.56,.58,.61),.68)

def move_collection(o,col=model):
    for c in list(o.users_collection): c.objects.unlink(o)
    col.objects.link(o)
    return o

def mesh(name,vs,fs,mat=clay,solid=0,sub=0):
    d=bpy.data.meshes.new(name); d.from_pydata([tuple(v*S for v in p) for p in vs],[],fs); d.update()
    o=bpy.data.objects.new(name,d); model.objects.link(o); o.data.materials.append(mat)
    for p in d.polygons:p.use_smooth=True
    if sub:
        q=o.modifiers.new('Superficie suavizada','SUBSURF');q.levels=sub;q.render_levels=sub
    if solid:
        q=o.modifiers.new('Espesor real','SOLIDIFY');q.thickness=solid*S;q.offset=-1
    return o

def tube(name,points,r=.055,mat=trim,closed=False,res=2,taper=False,min_radius=.035):
    d=bpy.data.curves.new(name,'CURVE');d.dimensions='3D';d.resolution_u=1
    sp=d.splines.new('POLY');sp.points.add(len(points)-1)
    for i,(p,v) in enumerate(zip(sp.points,points)):
        p.co=(*[x*S for x in v],1)
        if taper:p.radius=max(min_radius,min(1.,min(i,len(points)-1-i)/9))
    sp.use_cyclic_u=closed;d.bevel_depth=r*S;d.bevel_resolution=res;d.use_fill_caps=True
    o=bpy.data.objects.new(name,d);model.objects.link(o);o.data.materials.append(mat);return o

def multi_tube(name,paths,r=.022,mat=thread,res=1):
    """Un solo objeto para muchas puntadas/nervaduras con volumen real."""
    d=bpy.data.curves.new(name,'CURVE');d.dimensions='3D';d.resolution_u=1
    for points in paths:
        if len(points)<2:continue
        sp=d.splines.new('POLY');sp.points.add(len(points)-1)
        for p,v in zip(sp.points,points):p.co=(*[x*S for x in v],1)
    d.bevel_depth=r*S;d.bevel_resolution=res;d.use_fill_caps=True
    o=bpy.data.objects.new(name,d);model.objects.link(o);o.data.materials.append(mat)
    o['detalle_fino']=True
    return o

def stitches(mapper,count,fill=.66):
    return [[mapper((i+.5+fill*(j/3-.5))/count) for j in range(4)] for i in range(count)]

def cylinder(name,center,r,depth,mat=hardware,normal=(0,0,1),vertices=64):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=r*S,depth=depth*S,location=[v*S for v in center])
    o=bpy.context.object;o.name=name;move_collection(o);o.rotation_mode='QUATERNION';o.rotation_quaternion=Vector(normal).to_track_quat('Z','Y')
    o.data.materials.append(mat)
    for p in o.data.polygons:p.use_smooth=True
    b=o.modifiers.new('Cantos redondeados','BEVEL');b.width=.06*S;b.segments=3
    o.modifiers.new('Normales','WEIGHTED_NORMAL');return o

def torus(name,center,r,minor,mat=trim,normal=(0,0,1),major_segments=64):
    bpy.ops.mesh.primitive_torus_add(major_segments=major_segments,minor_segments=8,location=[v*S for v in center],major_radius=r*S,minor_radius=minor*S)
    o=bpy.context.object;o.name=name;move_collection(o);o.rotation_mode='QUATERNION';o.rotation_quaternion=Vector(normal).to_track_quat('Z','Y');o.data.materials.append(mat)
    for p in o.data.polygons:p.use_smooth=True
    return o

def cap_point(a,t,offset=0):
    # t=0: borde inferior; t=pi/2: cima
    rr=max(0,cos(t))**.85
    x=9.4*rr*cos(a);y=10.4*rr*sin(a);z=11.6*sin(t)
    n=Vector((x/(9.4**2),y/(10.4**2),max(.1,z)/(11.6**2))).normalized()
    return tuple(Vector((x,y,z))+offset*n)

def rad_at(z):return max(.001,1-(z/11.6)**2)**.425
def front(x,z,off=.08):
    r=rad_at(z);return (x,-10.4*r*sqrt(max(.001,1-(x/(9.4*r))**2))-off,z)
def back(x,z,off=.08):
    p=front(x,z,off);return (p[0],-p[1],p[2])
def side(sign,y,z,off=.1):
    r=rad_at(z);return (sign*(9.4*r*sqrt(max(.001,1-(y/(10.4*r))**2))+off),y,z)

# Copa hueca, abierta abajo; superficie de doble pared.
N=80;M=28;vs=[];fs=[]
for j in range(M):
    for i in range(N):vs.append(cap_point(2*pi*i/N,(pi/2)*j/M))
for j in range(M-1):
    for i in range(N):
        a=j*N+i;b=j*N+(i+1)%N;fs.append((a,b,b+N,a+N))
top=len(vs);vs.append((0,0,11.6))
for i in range(N):fs.append(((M-1)*N+i,(M-1)*N+(i+1)%N,top))
crown=mesh('01 Copa hueca',vs,fs,clay,.16,1)

# Banda perimetral y banda interior.
for z,rad,name in [(0,.12,'Ribete inferior'),(.38,.045,'Costura del borde')]:
    tube(name,[(9.43*cos(a),10.43*sin(a),z) for a in [2*pi*i/144 for i in range(144)]],rad,trim,True)
vs=[];fs=[]
for j in range(2):
    for i in range(96):vs.append((9.18*cos(2*pi*i/96),10.18*sin(2*pi*i/96),j*1.7))
for i in range(96):fs.append((i,(i+1)%96,(i+1)%96+96,i+96))
mesh('02 Banda interior',vs,fs,inset,.12)

crown_stitches=[]
for k in range(6):
    a=-pi/2+k*pi/3
    tube('Costura panel %02d'%k,[cap_point(a,.018+(pi/2-.06)*j/64,.035) for j in range(65)],.035,thread)
    for d in [-.019,.019]:
        crown_stitches.extend(stitches(lambda t:cap_point(a+d,.035+(pi/2-.13)*t,.068),55))
multi_tube('Puntadas dobles de los paneles',crown_stitches,.022)
multi_tube('Puntadas alrededor de la copa',stitches(lambda t:(9.46*cos(2*pi*t),10.46*sin(2*pi*t),.39),220),.025)

bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=12,radius=1,location=(0,0,11.7*S))
o=bpy.context.object;o.name='03 Botón superior';o.scale=(.66*S,.66*S,.29*S);move_collection(o);o.data.materials.append(clay)
for p in o.data.polygons:p.use_smooth=True

for i in range(6):
    a=-pi/2+(i+.5)*pi/3;p=cap_point(a,.63,.04)
    n=Vector((p[0]/(9.4**2),p[1]/(10.4**2),p[2]/(11.6**2))).normalized()
    torus('Ojal ventilación %02d'%i,p,.19,.055,trim,n,32)
    cylinder('Interior ojal %02d'%i,Vector(p)-.025*n,.13,.025,inset,n,24)

# Visera de contorno más redondeado, 6,3 cm de proyección y mayor caída.
def visor(theta,v,off=0):
    x=8.9*sin(theta);yi=-10.4*sqrt(max(.001,1-(x/9.4)**2))
    shape=max(0,1-abs(sin(theta))**2.4)**(1/2.4)
    end_y=-10.4*sqrt(1-(8.9/9.4)**2)
    outer_y=end_y+(-16.7-end_y)*shape
    y=yi*(1-v)+outer_y*v
    z=-.05-(.020*x*x*v+1.10*v*v)*shape+off
    return x,y,z
vs=[];fs=[];A=64;B=14
for j in range(B+1):
    for i in range(A+1):vs.append(visor(-pi/2+pi*i/A,j/B))
for j in range(B):
    for i in range(A):
        a=j*(A+1)+i;fs.append((a,a+A+1,a+A+2,a+1))
brim=mesh('04 Visera redondeada con caída',vs,fs,clay,.27,1)
bm=bmesh.new();bm.from_mesh(brim.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0000002)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(brim.data);bm.free()
thickness=brim.vertex_groups.new(name='Espesor de los remates laterales')
for v in brim.data.vertices:
    weight=max(.28,max(0,1-(v.co.x/(8.9*S))**2)**.24)
    thickness.add([v.index],weight,'REPLACE')
brim.modifiers['Espesor real'].vertex_group=thickness.name
brim.modifiers['Espesor real'].thickness_vertex_group=.28
brim['cambio']='Contorno frontal redondeado; proyección de 6,3 cm y caída central de 1,1 cm.'
tube('Ribete exterior visera',[visor(-pi/2+pi*i/160,1,.01) for i in range(161)],.1,trim,taper=True,min_radius=.4)
# Visera sin costura de hilo; se conserva la trenza decorativa y los laureles.
# Cordón trenzado del borde, construido con dos hebras helicoidales.
for phase in [0,pi]:
    braid=[]
    for i in range(1401):
        t=i/1400;th=-1.44+2.88*t;p=Vector(visor(th,.91,.13))
        tangent=Vector(visor(th+.001,.91,.13))-Vector(visor(th-.001,.91,.13))
        normal=Vector((-tangent.y,tangent.x,0)).normalized()
        wave=2*pi*80*t+phase
        p+=normal*(.08*cos(wave));p.z+=.065*sin(wave)
        braid.append(tuple(p))
    tube('Trenza perimetral visera',braid,.046,relief,res=1,taper=True)['detalle_fino']=True

def brim_surface(x,y,off=.1):
    th=math.asin(max(-.999,min(.999,x/8.9)));yi=-10.4*sqrt(max(.001,1-(x/9.4)**2))
    outer=visor(th,1)[1];v=(y-yi)/(outer-yi)
    return visor(th,v,off)

# Hojas con nervaduras, verdaderas mallas de volumen.
leaf_veins=[];leaf_secondary=[]
def leaf(name,p0,p1,width,mapper,mat=relief):
    ax=p1[0]-p0[0];ay=p1[1]-p0[1];ll=sqrt(ax*ax+ay*ay);nx=-ay/ll;ny=ax/ll
    vs=[];fs=[];nt=14;nu=8
    def leaf_point(t,u):
        w=width*sin(pi*t)**.85
        x=p0[0]+ax*t+nx*w*u;y=p0[1]+ay*t+ny*w*u
        p=list(mapper(x,y));p[2]+=.145*sin(pi*t)*(1-u*u)
        return p
    for j in range(nt+1):
        t=j/nt;w=width*sin(pi*t)**.85
        for i in range(nu+1):
            u=-1+2*i/nu;x=p0[0]+ax*t+nx*w*u;y=p0[1]+ay*t+ny*w*u
            vs.append(leaf_point(t,u))
    for j in range(nt):
        for i in range(nu):
            a=j*(nu+1)+i;fs.append((a,a+1,a+nu+2,a+nu+1))
    pts=[]
    for i in range(17):
        p=leaf_point(.045+.91*i/16,0);p[2]+=.015;pts.append(p)
    leaf_veins.append(pts)
    for t in [.22,.40,.58,.72]:
        for sign in [-1,1]:
            pts=[]
            for i in range(6):
                v=i/5;p=leaf_point(t+.13*v,sign*.77*v);p[2]+=.008;pts.append(p)
            leaf_secondary.append(pts)
    return mesh(name,vs,fs,mat,.07)

for sign in [-1,1]:
    pts=[visor(sign*(.12+1.02*i/48),.62,.13) for i in range(49)]
    tube('Laurel visera rama',pts,.07,relief)
    for i in range(8):
        t=.03+i*.117;theta=sign*(.12+1.02*t)
        for side_v in [-1,1]:
            leaf('Laurel visera hoja',(theta,.62),(theta+sign*.20,.62+side_v*.23),.062,lambda a,v:visor(a,v,.18))
multi_tube('Nervaduras centrales laurel visera',leaf_veins,.022,relief)
multi_tube('Nervaduras finas laurel visera',leaf_secondary,.009,relief)

# Escudo frontal curvado sobre la copa.
zc=5.6;R=2.65;vs=[front(0,zc,.25)];fs=[]
for j in range(1,13):
    r=R*j/12
    for i in range(96):
        a=2*pi*i/96;vs.append(front(r*cos(a),zc+r*sin(a),.20+.05*(1-(r/R)**2)))
for i in range(96):fs.append((0,i+1,(i+1)%96+1))
for j in range(11):
    for i in range(96):
        a=1+j*96+i;b=1+j*96+(i+1)%96;fs.append((a,a+96,b+96,b))
badge=mesh('05 Base escudo frontal',vs,fs,trim,.12)
# Asegurar normales hacia fuera antes del espesor.
bm=bmesh.new();bm.from_mesh(badge.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
if sum(f.normal.y for f in bm.faces)>0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
bm.to_mesh(badge.data);bm.free()
for r,thick in [(R,.125),(R-.23,.045),(1.65,.078)]:
    tube('Anillo escudo', [front(r*cos(a),zc+r*sin(a),.33) for a in [2*pi*i/160 for i in range(160)]],thick,relief,True)

# Estrella de cinco puntas con centro elevado.
vs=[front(0,zc,.86)];fs=[]
for i in range(10):
    a=pi/2+i*pi/5;r=1.48 if i%2==0 else .62;vs.append(front(r*cos(a),zc+r*sin(a),.43 if i%2==0 else .34))
for i in range(10):fs.append((0,i+1,(i+1)%10+1))
star=mesh('Estrella en relieve',vs,fs,relief,.08)
for p in star.data.polygons:p.use_smooth=False

# Laurel del escudo: hojas curvas en el plano frontal.
crest_veins=[]
def crest_leaf(p0,p1,width):
    ax=p1[0]-p0[0];az=p1[1]-p0[1];ll=sqrt(ax*ax+az*az);nx=-az/ll;nz=ax/ll;vs=[];fs=[]
    for j in range(9):
        t=j/8
        for i in range(5):
            u=-1+2*i/4;w=width*sin(pi*t);x=p0[0]+ax*t+nx*w*u;z=p0[1]+az*t+nz*w*u
            vs.append(front(x,z,.35+.14*sin(pi*t)*(1-u*u)))
    for j in range(8):
        for i in range(4):
            a=j*5+i;fs.append((a,a+1,a+6,a+5))
    mesh('Hoja laurel escudo',vs,fs,relief,.035)
    crest_veins.append([front(p0[0]+ax*t,p0[1]+az*t,.365+.14*sin(pi*t)) for t in [i/12 for i in range(1,12)]])
for sign in [-1,1]:
    aa=[-1.42+2.67*i/60 for i in range(61)]
    tube('Rama laurel escudo',[front(sign*2.02*cos(a),zc+2.02*sin(a),.35) for a in aa],.055,relief)
    for j in range(10):
        a=-1.30+2.5*j/10;x=sign*2.02*cos(a);z=zc+2.02*sin(a)
        for k in [-1,1]:
            b=a+.2;rr=2.02+k*.28
            crest_leaf((x,z),(sign*rr*cos(b),zc+rr*sin(b)),.115)
multi_tube('Nervaduras del laurel escudo',crest_veins,.012,relief)
vs=[front(0,zc+2.15,.56)];fs=[]
for i in range(10):
    a=pi/2+i*pi/5;r=.29 if i%2==0 else .12;vs.append(front(r*cos(a),zc+2.15+r*sin(a),.36))
for i in range(10):fs.append((0,i+1,(i+1)%10+1))
small_star=mesh('Estrella superior escudo',vs,fs,relief,.04)
for p in small_star.data.polygons:p.use_smooth=False
for sign in [-1,1]:
    tube('Lazo inferior escudo',[front(sign*(-.46+.92*i/24),zc-2.08+.14*sin(pi*i/24),.4) for i in range(25)],.04,relief)

# Protector cervical acolchado. La parte superior continúa el borde de la copa.
limit=1.06
def nape(a,v,off=0):
    edge=max(0,cos((a/limit)*pi/2))**.65
    bottom=-8.5*edge
    z=.02+bottom*v;x=(9.4-1.25*v*edge)*sin(a)
    groove=sum(.16*exp(-((z+q)/.12)**2) for q in [2.3,4.4,6.45])
    padding=sum(.20*exp(-((z+q)/.72)**2) for q in [1.2,3.35,5.45,7.5])
    y=(10.4-1.45*v*edge)*cos(a)+(.26*sin(pi*v)+(padding-groove)*sin(pi*v)**.4)*edge+off*edge
    return x,y,z
A=80;B=64;vs=[];fs=[]
for j in range(B+1):
    for i in range(A+1):vs.append(nape(-limit+2*limit*i/A,j/B))
for j in range(B):
    for i in range(A):
        a=j*(A+1)+i;fs.append((a,a+1,a+A+2,a+A+1))
nape_obj=mesh('06 Protector cervical acolchado',vs,fs,clay,.30,1)
bm=bmesh.new();bm.from_mesh(nape_obj.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0000002)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
if sum(f.normal.y for f in bm.faces)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
crease=bm.edges.layers.float.get('crease_edge') or bm.edges.layers.float.new('crease_edge')
for e in bm.edges:
    if e.is_boundary:e[crease]=1
bm.to_mesh(nape_obj.data);bm.free()
nape_obj['cambio']='Remates superiores cerrados y unidos en un ribete continuo, ajustados al borde elíptico de la copa.'
# Un solo ribete cerrado: no hay tres tubos independientes ni cabos sueltos.
perimeter=[nape(-limit+2*limit*i/160,0,.015) for i in range(161)]
perimeter += [nape(-limit+2*limit*i/160,1,.025) for i in range(159,0,-1)]
tube('Ribete continuo del protector cervical',perimeter,.11,trim,closed=True,res=3)
for q in [2.3,4.4,6.45]:
    pts=[]
    for i in range(161):
        a=-limit+2*limit*i/160;bottom=nape(a,1)[2]
        if bottom < -q-.28:pts.append(nape(a,-q/bottom,.015))
    tube('Canal acolchado cervical',pts,.035,thread)
nape_stitches=stitches(lambda t:nape(-limit+.05+(2*limit-.10)*t,.975,.13),180)
# El ribete continuo sustituye las antiguas costuras laterales comprimidas.
for sign in [-1,1]:
    band_verts=[];band_faces=[]
    for j in range(81):
        t=j/80;a=sign*(.86-.74*t);v=.91*t
        for d in [-.038,.038]:band_verts.append(nape(a+d,v,.08+.09*sin(pi*t/2)))
    for j in range(80):
        a=j*2;band_faces.append((a,a+1,a+3,a+2))
    mesh('Refuerzo diagonal cervical',band_verts,band_faces,clay,.07)
    for d in [-.030,.030]:
        nape_stitches.extend(stitches(lambda t:nape(sign*(.86-.74*t)+d,.015+.88*t,.12+.09*sin(pi*t/2)),52))
for q in [2.3,4.4,6.45]:
    amax=limit
    while nape(amax,1)[2]>-q-.30:amax-=.005
    nape_stitches.extend(stitches(lambda t:nape(-amax+2*amax*t,-q/nape(-amax+2*amax*t,1)[2],.09),int(120*amax)))
multi_tube('Puntadas del acolchado cervical',nape_stitches,.024)

# Ajuste de herrajes: únicamente profundidad y asiento, con los contornos
# originales en Y/Z (laterales) y X/Z (placa posterior).
def surface_tree(objects):
    bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
    vertices=[];faces=[]
    for obj in objects:
        evaluated=obj.evaluated_get(deps);data=evaluated.to_mesh();offset=len(vertices)
        vertices.extend(evaluated.matrix_world@v.co for v in data.vertices)
        faces.extend(tuple(offset+i for i in p.vertices) for p in data.polygons)
        evaluated.to_mesh_clear()
    return BVHTree.FromPolygons(vertices,faces)
crown_surface=surface_tree([crown])

def side_contact(sign,y,z,thickness,extra=0):
    p,n,_,_=crown_surface.ray_cast(Vector((sign*.25,y*S,z*S)),Vector((-sign,0,0)),.5)
    assert p is not None
    return (p.x/S+sign*(thickness/max(.7,abs(n.x))+.004+extra),y,z)

def rear_contact(x,z,thickness=.12,extra=0):
    p,n,_,_=crown_surface.ray_cast(Vector((x*S,.25,z*S)),Vector((0,-1,0)),.5)
    assert p is not None
    return (x,p.y/S+thickness/max(.7,abs(n.y))+.014+extra,z)

for sign in [-1,1]:
    side_name='derecho' if sign>0 else 'izquierdo'
    coords=[(-1.6,5.3),(1.6,5.3),(0,1.25)]
    vs=[];fs=[];index={};N=36
    for j in range(N+1):
        for i in range(N+1-j):
            a=i/N;b=j/N;y=coords[0][0]*(1-a-b)+coords[1][0]*a+coords[2][0]*b
            z=coords[0][1]*(1-a-b)+coords[1][1]*a+coords[2][1]*b
            index[i,j]=len(vs);vs.append(side_contact(sign,y,z,.07))
    for j in range(N):
        for i in range(N-j):
            f=(index[i,j],index[i+1,j],index[i,j+1]);fs.append(f[::-1] if sign>0 else f)
            if i+j<N-1:
                f=(index[i+1,j],index[i+1,j+1],index[i,j+1]);fs.append(f[::-1] if sign>0 else f)
    support=mesh('07 Fuelle lateral '+side_name,vs,fs,inset,.07)
    support['cambio']='Contorno triangular original, sin pliegue central; cara ajustada a la copa sin atravesarla.'
    outline=[]
    triangle_stitches=[]
    for i in range(3):
        p=Vector(coords[i]);q=Vector(coords[(i+1)%3])
        for j in range(65):
            yz=p.lerp(q,j/65);outline.append(side_contact(sign,*yz,.07))
        triangle_stitches.extend(stitches(lambda t:side_contact(sign,*p.lerp(q,t),.07,.022),16))
    tube('Borde fuelle '+side_name,outline,.07,trim,True)
    multi_tube('Puntadas soporte triangular '+side_name,triangle_stitches,.018)
    anchors=[]
    for y in [-3,3]:
        for z in [1.7,3.75]:
            p=side_contact(sign,y,z,.065);anchors.append(p)
            _,normal,_,_=crown_surface.ray_cast(Vector((sign*.25,y*S,z*S)),Vector((-sign,0,0)),.5)
            torus('Guía cable '+side_name,p,.16,.065,hardware,normal,24)
        # Trabilla rectangular que une las dos guías del cable.
        vs=[];fs=[]
        for j in range(13):
            z=1.92+1.60*j/12
            for i in range(5):
                yy=y-.23+.46*i/4
                vs.append(side_contact(sign,yy,z,.08))
        for j in range(12):
            for i in range(4):
                a=j*5+i;fs.append((a,a+5,a+6,a+1) if sign>0 else (a,a+1,a+6,a+5))
        mesh('Trabilla guía '+side_name,vs,fs,clay,.08)
        path=[side_contact(sign,y-.23+.46*t,1.92,.08,.018) for t in [i/8 for i in range(9)]]
        path+=[side_contact(sign,y+.23,1.92+1.60*t,.08,.018) for t in [i/20 for i in range(1,21)]]
        path+=[side_contact(sign,y+.23-.46*t,3.52,.08,.018) for t in [i/8 for i in range(1,9)]]
        path+=[side_contact(sign,y-.23,3.52-1.60*t,.08,.018) for t in [i/20 for i in range(1,20)]]
        tube('Borde trabilla '+side_name,path,.035,trim,True)
    seated=surface_tree([crown]+[o for o in model.objects if side_name in o.name])
    for k,(a,b) in enumerate([(0,2),(1,3),(0,3),(1,2)]):
        p=anchors[a];q=anchors[b];profile=[];N=192;radius=.052
        length=math.hypot(q[1]-p[1],q[2]-p[2]);ny=-(q[2]-p[2])/length;nz=(q[1]-p[1])/length
        for j in range(N+1):
            t=j/N;y=p[1]*(1-t)+q[1]*t;z=p[2]*(1-t)+q[2]*t;height=0
            # El cable envuelve la superficie real de la copa y los bordes.
            for d in [-1,-.75,-.4,0,.4,.75,1]:
                h,n,_,_=seated.ray_cast(Vector((sign*.25,(y+ny*d*radius)*S,(z+nz*d*radius)*S)),Vector((-sign,0,0)),.5)
                assert h is not None
                height=max(height,sign*h.x/S+radius*sqrt(max(0,1-d*d))/max(.8,abs(n.x))+.003)
            if j in [0,N]:height=max(height,sign*(p[0] if j==0 else q[0]))
            profile.append((height,y,z))
        pts=[]
        for j,(height,y,z) in enumerate(profile):
            # Suavizado por encima de la envolvente: sin atravesar los ribetes.
            height=max(profile[i][0]-.65*((i-j)*length/N)**2 for i in range(max(0,j-14),min(N,j+14)+1))
            if k==3:height+=.125*exp(-((j/N-.5)/.065)**2)
            distance=min(j,N-j)*length/N
            if distance<.08:
                anchor=sign*(p[0] if j<N/2 else q[0])
                height=max(profile[j][0],anchor+(height-anchor)*sin(pi/2*distance/.08))
            pts.append((sign*height,y,z))
        cable=tube('08 Cable '+side_name+' '+str(k+1),pts,radius,hardware,res=2)
        cable['cambio']='Recorrido cruzado original; profundidad ceñida al soporte, con paso superior en el cruce.'

# Soporte trasero de esquinas redondeadas, doble costura y dial estriado.
def dial_outline(t,scale=1,off=0):
    a=2*pi*t;c=cos(a);s=sin(a)
    x=2.65*math.copysign(abs(c)**.36,c)*scale
    z=2.22+1.78*math.copysign(abs(s)**.36,s)*scale
    return rear_contact(x,z,.12,off)
vs=[rear_contact(0,2.22)];fs=[];A=128;B=12
for j in range(1,B+1):
    for i in range(A):vs.append(dial_outline(i/A,j/B))
for i in range(A):fs.append((0,(i+1)%A+1,i+1))
for j in range(B-1):
    for i in range(A):
        a=1+j*A+i;b=1+j*A+(i+1)%A;fs.append((a,b,b+A,a+A))
plate=mesh('09 Soporte del dial',vs,fs,clay,.12)
bm=bmesh.new();bm.from_mesh(plate.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
if sum(f.normal.y for f in bm.faces)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
bm.to_mesh(plate.data);bm.free()
tube('Ribete soporte dial',[dial_outline(i/192,1,.035) for i in range(192)],.08,trim,True)
multi_tube('Puntadas soporte dial',stitches(lambda t:dial_outline(t,.955,.024),100),.022)
for z in [1.15,3.28]:
    tube('Canal horizontal soporte dial',[rear_contact(-2.48+4.96*i/64,z,.12,.025) for i in range(65)],.045,trim)
housing_before=set(model.objects)
cylinder('10 Dial cuerpo',(0,10.84,2.22),1.35,.62,hardware,(0,1,0),96)
cylinder('Dial cara',(0,11.21,2.22),1.16,.16,relief,(0,1,0),96)
cylinder('Dial centro',(0,11.31,2.22),1.01,.07,clay,(0,1,0),96)
torus('Aro frontal del dial',(0,11.32,2.22),1.14,.035,trim,(0,1,0),96)
knurls=[]
for i in range(80):
    a=2*pi*i/80
    knurls.append([(1.35*cos(a),y,2.22+1.35*sin(a)) for y in [10.60,10.83,11.09]])
multi_tube('Estrías finas dial',knurls,.026,relief)
# Traslado y giro rígidos: el dial mantiene sus diámetros y su contorno circular.
_,normal,_,_=crown_surface.ray_cast(Vector((0,.25,2.22*S)),Vector((0,-1,0)),.5)
normal=Vector((0,normal.y,normal.z)).normalized()
rotation=Matrix.Rotation(math.atan2(normal.z,normal.y),4,'X')
contact=Vector(rear_contact(0,2.22))*S+normal*(.020*S)
old_rear=Vector((0,10.53,2.22))*S
transform=Matrix.Translation(contact)@rotation@Matrix.Translation(-old_rear)
bpy.context.view_layer.update()
housing=[(obj,obj.matrix_world.copy()) for obj in set(model.objects)-housing_before]
for obj,world in housing:obj.matrix_world=transform@world

# Asiento inferior integrado en la carcasa: cierra la cuña contra la base curva.
# Solo modifica la cara de apoyo; las caras visibles conservan el giro rígido.
base_tree=surface_tree([plate]);vs=[];fs=[];A=96;B=12
for layer in [0,1]:
    for j in range(B+1):
        r=1.29*j/B
        for i in range(A):
            a=2*pi*i/A;p=contact+rotation.to_3x3()@Vector((r*cos(a)*S,0,r*sin(a)*S))
            if layer==0:
                loc,_,_,_=base_tree.ray_cast(p+normal*(.1*S),-normal,.05)
                assert loc is not None
                p=loc+normal*(.008*S)
            else:p+=normal*(.004*S)
            vs.append(tuple(p/S))
size=(B+1)*A
for layer in [0,1]:
    for j in range(B):
        for i in range(A):
            a=layer*size+j*A+i;b=layer*size+j*A+(i+1)%A
            f=(a,b,b+A,a+A);fs.append(f if layer else f[::-1])
for i in range(A):
    a=B*A+i;b=B*A+(i+1)%A;fs.append((a,a+size,b+size,b))
seat=mesh('Asiento interior del dial',vs,fs,hardware)
bm=bmesh.new();bm.from_mesh(seat.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0000002)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(seat.data);bm.free()

# Metadatos útiles en el archivo, sin pretender exactitud industrial.
crown['descripcion']='Reconstrucción visual aproximada con detalles geométricos de la referencia: costuras, bordados, trenza, escudo, acolchado y dial.'
crown['referencia_perimetro_cm']='58–62; aproximado'
crown['visera_proyeccion_cm']=6.3
crown['protector_altura_cm']=8.5
crown['uso']='Visualización de diseño. No es un patrón de fabricación validado.'

# Escena de render real, lista para abrir y renderizar en Blender.
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.length_unit='CENTIMETERS'
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=1280;scene.render.resolution_y=1120;scene.render.resolution_percentage=100
scene.world.color=(.4,.4,.4);scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.65,.69,.76,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.35
scene.view_settings.view_transform='AgX'
scene.view_settings.look='AgX - Medium High Contrast'
scene.view_settings.exposure=-.35

def camera(name,pos,target):
    bpy.ops.object.camera_add(location=[x*S for x in pos]);o=bpy.context.object;o.name=name;move_collection(o,studio)
    o.rotation_euler=(Vector([x*S for x in target])-o.location).to_track_quat('-Z','Y').to_euler()
    o.data.type='ORTHO';o.data.ortho_scale=.39;o.data.lens=55;o.data.clip_start=.001
    return o
cam=camera('Cámara frontal 3-4',(34,-48,27),(0,-2,2));rear=camera('Cámara posterior 3-4',(34,48,22),(0,0,2));scene.camera=cam
def light(name,pos,power,size):
    bpy.ops.object.light_add(type='AREA',location=[x*S for x in pos]);o=bpy.context.object;o.name=name;move_collection(o,studio)
    o.data.energy=power;o.data.shape='DISK';o.data.size=size*S
    o.rotation_euler=(-o.location).to_track_quat('-Z','Y').to_euler()
light('Softbox principal',(-25,-30,50),5,35)
light('Softbox relleno',(35,-15,18),1.4,30)
light('Luz de borde',(0,30,40),3.5,28)
bpy.ops.mesh.primitive_plane_add(size=200*S,location=(0,0,-8.75*S));plane=bpy.context.object;plane.name='Suelo estudio';move_collection(plane,studio)
plane.data.materials.append(material('Fondo estudio',(.72,.74,.77)))

# Despiece por conjuntos: cada detalle se desplaza junto con su pieza principal.
# Blender: cuadro 1 = armada, cuadro 60 = separada, cuadro 120 = armada.
group_specs={
    'copa':('Copa',(0,0,7)),
    'visera':('Visera',(0,-11,-3)),
    'cervical':('Protector cervical',(0,10,-5)),
    'dial':('Dial y soporte',(0,17,5)),
    'izquierdo':('Ajuste izquierdo',(-11,0,2)),
    'derecho':('Ajuste derecho',(11,0,2)),
    'escudo':('Escudo frontal',(0,-10,8)),
    'banda':('Banda interior',(0,0,-10)),
}
def group_of(name):
    n=name.lower()
    if 'visera' in n:return 'visera'
    if 'escudo' in n or 'estrella' in n:return 'escudo'
    if 'cervical' in n:return 'cervical'
    if 'dial' in n:return 'dial'
    if 'izquierdo' in n:return 'izquierdo'
    if 'derecho' in n:return 'derecho'
    if 'banda interior' in n:return 'banda'
    return 'copa'
# Congelar superficies evaluadas en mallas editables y asignar UV físicas.
# El generador conserva las fórmulas y los nueve conjuntos siguen independientes.
bpy.ops.object.select_all(action='DESELECT')
for obj in model.objects:obj.select_set(True)
bpy.context.view_layer.objects.active=crown
bpy.ops.object.convert(target='MESH')
# La superficie de asiento forma parte de la carcasa ya existente.
bpy.ops.object.select_all(action='DESELECT')
bpy.data.objects['10 Dial cuerpo'].select_set(True);bpy.data.objects['Asiento interior del dial'].select_set(True)
bpy.context.view_layer.objects.active=bpy.data.objects['10 Dial cuerpo'];bpy.ops.object.join()
crown=bpy.data.objects['01 Copa hueca']
# Ajuste exclusivo de visera, bordado y laureles sobre la misma superficie.
import ajuste_visera
import numpy as np
for obj in model.objects:
    if obj.type=='MESH' and group_of(obj.name)=='visera':
        coords=np.empty(len(obj.data.vertices)*3,dtype=np.float64)
        obj.data.vertices.foreach_get('co',coords)
        transformed,_=ajuste_visera.ajustar(coords.reshape(-1,3)*100,obj.name)
        obj.data.vertices.foreach_set('co',(transformed*.01).reshape(-1))
        obj.data.update()
textile_materials=textil.materials()
geometry_objects=list(model.objects)
for obj in geometry_objects:
    key=group_of(obj.name);role=textil.role_for(obj,key)
    obj['material_role']=role
    obj.data.materials.clear();obj.data.materials.append(textile_materials[role])
    textil.uv_for_mesh(obj.data,obj.matrix_world,key)
parents={}
for key,(label,delta) in group_specs.items():
    obj=bpy.data.objects.new('CONJUNTO | '+label,None);model.objects.link(obj)
    obj.empty_display_type='PLAIN_AXES';obj.empty_display_size=.025
    obj['pieza']=label;obj['uso']='Desplaza la línea de tiempo: 1 armada; 60 separada; 120 armada.'
    for frame,amount in [(1,0),(60,1),(120,0)]:
        obj.location=[v*S*amount for v in delta];obj.keyframe_insert(data_path='location',frame=frame)
    if obj.animation_data and obj.animation_data.action:
        obj.animation_data.action.name='Despiece | '+label
        for fc in obj.animation_data.action.fcurves:
            for k in fc.keyframe_points:k.interpolation='LINEAR'
    parents[key]=obj
for obj in geometry_objects:
    key=group_of(obj.name);obj.parent=parents[key];obj['conjunto']=key
scene.frame_start=1;scene.frame_end=120;scene.render.fps=30
scene.timeline_markers.new('ARMADA',frame=1)
scene.timeline_markers.new('SEPARADA',frame=60)
scene.timeline_markers.new('ARMADA',frame=120)
scene.frame_set(1);bpy.context.view_layer.update()

# Acabado definitivo: borde uniforme y escudo DIPRO desde la referencia original.
import acabados_dipro
acabados_dipro.aplicar()
import acabados_cervical
acabados_cervical.aplicar()
import paneles_copa
paneles_copa.aplicar()
import cables_laterales
cables_laterales.aplicar()
import proporcion_copa
proporcion_copa.aplicar()
import remates_superiores,estudio_realista
remates_superiores.aplicar()
estudio_realista.iluminar()
textil.set_palette('negro')
crown=bpy.data.objects['Panel Delantero']

# Inicio en vista de material sólido; todas las piezas del modelo quedan seleccionadas.
bpy.ops.object.select_all(action='DESELECT')
for o in model.objects:o.select_set(True)
bpy.context.view_layer.objects.active=crown
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.clip_start=.001
            area.spaces.active.region_3d.view_distance=.49
            area.spaces.active.region_3d.view_location=(0,-.02,.02)
            area.spaces.active.region_3d.view_rotation=cam.rotation_euler.to_quaternion()
            area.spaces.active.shading.type='MATERIAL'
            area.spaces.active.overlay.show_floor=False

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'gorra_tactica.blend'),compress=True)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT,'gorra_tactica.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_materials='EXPORT',export_cameras=False,export_lights=False,export_animations=True,export_animation_mode='SCENE',export_force_sampling=True)
unificar_animacion_glb(os.path.join(OUT,'gorra_tactica.glb'))
scene.frame_set(1);bpy.context.view_layer.update()

# Datos compactos para la misma geometría en el visor de conversación.
# Cada pieza conserva sus posiciones, normales e índices de triángulos.
import exportar_visor
parts=exportar_visor.partes(model)
with open(os.path.join(OUT,'visor-data.json'),'w') as f:json.dump(parts,f,separators=(',',':'))

if os.environ.get('GORRA_RENDER', '1') != '0':
    scene.render.filepath=os.path.join(OUT,'revision_frontal.png');bpy.ops.render.render(write_still=True)
    scene.camera=rear;scene.render.filepath=os.path.join(OUT,'revision_posterior.png');bpy.ops.render.render(write_still=True)
    scene.frame_set(60);scene.camera=cam;cam.data.ortho_scale=.67
    plane.hide_render=True;scene.render.filepath=os.path.join(OUT,'revision_desarmada.png');bpy.ops.render.render(write_still=True)
print('MODEL_READY',len(model.objects),'objects',flush=True)
