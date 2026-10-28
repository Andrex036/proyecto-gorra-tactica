"""Copa de cuatro paneles y sistema de ajuste único con cableado interior.

Conserva la envolvente original. Los cortes son geometría real y el mecanismo
permanece en su posición de montaje. Unidades internas de Blender: metros.
"""
import bpy,bmesh,math
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
import textil

S=.01
SPECS={
 'panel_delantero':('Panel Delantero',(0,-5,11),-150,-30),
 'panel_trasero':('Panel Trasero',(0,8,16),30,150),
 'panel_izquierdo':('Panel Lateral Izquierdo',(-14,0,8),150,210),
 'panel_derecho':('Panel Lateral Derecho',(14,0,8),-30,30),
 'ajuste':('Sistema de ajuste',(0,18,0),None,None),
}
DELTAS={k:v[1] for k,v in SPECS.items()}
DELTAS.update(visera=(0,-11,-3),cervical=(0,10,-5),escudo=(0,-10,8),banda=(0,0,-10))


def panel_key(p):
 a=math.degrees(math.atan2(p.y/10.4,p.x/9.4))
 if -150<a<-30:return 'panel_delantero'
 if 30<a<150:return 'panel_trasero'
 return 'panel_derecho' if p.x>=0 else 'panel_izquierdo'


def remove(o):
 data=o.data;bpy.data.objects.remove(o,do_unlink=True)
 if data and data.users==0 and isinstance(data,bpy.types.Mesh):bpy.data.meshes.remove(data)


def finish(o,key,preserve=True):
 o['conjunto']=key;o['normal_bits']=16;o['uv_preservar']=preserve
 for f in o.data.polygons:f.use_smooth=True
 textil.uv_for_mesh(o.data,o.matrix_world,'copa' if key.startswith('panel_') else key)
 return o


def cut_sector(source,key):
 """Recorta el sólido sin cambiar ninguno de sus vértices interiores."""
 _,_,a0,a1=SPECS[key]
 bm=bmesh.new();bm.from_mesh(source.data);bm.transform(source.matrix_world)
 for angle,end in [(a0,False),(a1,True)]:
  a=math.radians(angle);n=Vector((math.sin(a)/9.4,-math.cos(a)/10.4,0))
  if end:n=-n
  bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-9,plane_co=(0,0,0),plane_no=n,clear_outer=True,clear_inner=False)
  boundary=[e for e in bm.edges if e.is_boundary]
  if boundary:bmesh.ops.holes_fill(bm,edges=boundary,sides=0)
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-8)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 me=bpy.data.meshes.new(SPECS[key][0]);bm.to_mesh(me);bm.free();me.update()
 o=bpy.data.objects.new(SPECS[key][0],me);source.users_collection[0].objects.link(o)
 for mat in source.data.materials:me.materials.append(mat)
 finish(o,key);o['material_role']=source.get('material_role','fabric')
 return o


def triangle_hole(o,sign):
 yz=[(-1.6,5.3),(1.6,5.3),(0,1.25)]
 # El recorte coincide con la línea central del ribete triangular existente.
 vs=[(sign*x*S,y*S,z*S) for x in (6,12) for y,z in yz]
 fs=[(0,2,1),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5)]
 me=bpy.data.meshes.new('Herramienta abertura triangular');me.from_pydata(vs,[],fs);me.update()
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 cutter=bpy.data.objects.new('Herramienta abertura triangular',me);o.users_collection[0].objects.link(cutter)
 bpy.context.view_layer.objects.active=o;mod=o.modifiers.new('Abertura triangular real','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
 bpy.ops.object.modifier_apply(modifier=mod.name);remove(cutter)
 finish(o,o['conjunto'])


def sharpen_walls(o):
 bm=bmesh.new();bm.from_mesh(o.data)
 for e in bm.edges:
  if len(e.link_faces)==2:e.smooth=e.calc_face_angle()<.6
 bm.to_mesh(o.data);bm.free();o.data.update()


def new_mesh(name,vs,fs,role,model):
 me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update();o=bpy.data.objects.new(name,me);model.objects.link(o)
 me.materials.append(next(m for m in bpy.data.materials if m.get('role')==role));o['material_role']=role
 finish(o,'ajuste');return o


def tube(name,points,radius,model):
 # Malla tubular con marco paralelo y tapas; no hay cabos abiertos.
 vs=[];fs=[];sides=8
 for i,p in enumerate(points):
  tangent=(points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized()
  u=tangent.cross(Vector((0,0,1))).normalized();v=tangent.cross(u).normalized()
  for j in range(sides):
   a=2*math.pi*j/sides;vs.append(p+radius*(math.cos(a)*u+math.sin(a)*v))
 for i in range(len(points)-1):
  for j in range(sides):
   a=i*sides+j;b=i*sides+(j+1)%sides;fs.append((a,b,b+sides,a+sides))
 fs.extend([tuple(range(sides-1,-1,-1)),tuple((len(points)-1)*sides+j for j in range(sides))])
 return new_mesh(name,vs,fs,'hardware',model)


def aplicar():
 model=bpy.data.collections['GORRA | piezas editables'];scene=bpy.context.scene;scene.frame_set(1);bpy.context.view_layer.update()
 crown=bpy.data.objects.get('01 Copa hueca')
 if crown is None:return
 old_tree=BVHTree.FromPolygons([crown.matrix_world@v.co for v in crown.data.vertices],[tuple(p.vertices) for p in crown.data.polygons])
 def radial(a,z,inset=.08):
  direction=Vector((math.cos(a),math.sin(a),0));origin=direction*.3;origin.z=z*S
  p,n,_,_=old_tree.ray_cast(origin,-direction,.5);assert p is not None
  # La distancia normal coloca el cable entre las dos paredes de la copa.
  return p-n*(inset*S)
 def lateral(sign,y,z):
  p,n,_,_=old_tree.ray_cast(Vector((sign*.3,y*S,z*S)),Vector((-sign,0,0)),.6);assert p is not None
  # Mantener Y/Z fija hace coincidir el fuelle y los extremos de los cables.
  return Vector((p.x-sign*(.08*S/max(.6,abs(n.x))),y*S,z*S))
 # Corte del sólido y abertura real en cada panel lateral.
 panels={k:cut_sector(crown,k) for k in SPECS if k.startswith('panel_')}
 triangle_hole(panels['panel_izquierdo'],-1);triangle_hole(panels['panel_derecho'],1)
 for o in panels.values():sharpen_walls(o)
 remove(crown)
 # Los ribetes y las puntadas periféricas acompañan a su panel.
 crown_objects=[o for o in list(model.objects) if o.type=='MESH' and o.get('conjunto')=='copa']
 for o in crown_objects:
  if o.name in {'Costura panel 00','Costura panel 03'}:remove(o);continue
  if o.name in {'Ribete inferior','Costura del borde'}:
   for key in panels:
    part=cut_sector(o,key);part.name=o.name+' | '+SPECS[key][0]
   remove(o);continue
  if o.name in {'Puntadas dobles de los paneles','Puntadas alrededor de la copa'}:
   # Las puntadas son islas cerradas: asignar cada isla completa evita cortarlas.
   bm=bmesh.new();bm.from_mesh(o.data);bm.transform(o.matrix_world);remaining=set(bm.verts);groups={k:set() for k in panels}
   while remaining:
    todo=[remaining.pop()];island=set(todo)
    while todo:
     v=todo.pop()
     for e in v.link_edges:
      q=e.other_vert(v)
      if q in remaining:remaining.remove(q);island.add(q);todo.append(q)
    center=sum((v.co for v in island),Vector())/len(island);a=math.degrees(math.atan2(center.y/10.4,center.x/9.4))
    if o.name.startswith('Puntadas dobles') and abs(abs(a)-90)<5:continue
    groups[panel_key(center)].update(v.index for v in island)
   bm.verts.ensure_lookup_table()
   for key,indices in groups.items():
    if not indices:continue
    vlist=sorted(indices);mapping={v:i for i,v in enumerate(vlist)}
    faces=[tuple(mapping[v.index] for v in f.verts) for f in bm.faces if all(v.index in indices for v in f.verts)]
    me=bpy.data.meshes.new(o.name);me.from_pydata([bm.verts[i].co for i in vlist],[],faces);me.update()
    obj=bpy.data.objects.new(o.name+' | '+SPECS[key][0],me);model.objects.link(obj)
    for mat in o.data.materials:me.materials.append(mat)
    obj['material_role']=o['material_role'];finish(obj,key)
   bm.free();remove(o);continue
  if o.name.startswith('Costura panel'):
   k=int(o.name.split()[-1]);key='panel_delantero' if k in (1,5) else 'panel_trasero'
  elif o.name=='03 Botón superior':key='panel_trasero'
  else:
   center=sum((o.matrix_world@v.co for v in o.data.vertices),Vector())/len(o.data.vertices);key=panel_key(center)
  o['conjunto']=key
 # Un único mecanismo: conservar soportes/dial/guías y sustituir solo los cables.
 hardware=[o for o in model.objects if o.type=='MESH' and o.get('conjunto') in {'dial','izquierdo','derecho'}]
 for o in list(hardware):
  if o.name.startswith('08 Cable'):hardware.remove(o);remove(o)
 for sign,side in [(-1,'izquierdo'),(1,'derecho')]:
  # Circuito continuo: dial -> guía trasera alta -> delantera baja ->
  # trasera baja -> delantera alta -> trasera alta -> retorno al dial.
  # El cruce se separa en profundidad para no interpenetrar los cables.
  anchors=[(-3,1.7),(-3,3.75),(3,1.7),(3,3.75)]
  for k,(a,b) in enumerate([(0,2),(1,3),(0,3),(1,2)]):
   p,q=anchors[a],anchors[b];points=[]
   for j in range(145):
    t=j/144;y=p[0]*(1-t)+q[0]*t;z=p[1]*(1-t)+q[1]*t
    pt=lateral(sign,y,z)
    if k>=2:pt.x+=sign*(.029 if k==2 else -.029)*S
    points.append(pt)
   hardware.append(tube('Cable interior cruzado '+side+' '+str(k+1),points,.024*S,model))
  # Cableado de ida y vuelta hasta el cuerpo del dial: dos recorridos cerrados.
  for z in (1.7,3.75):
   target=lateral(sign,3,z);a0=math.atan2(target.y,target.x)
   ae=math.pi/2-sign*.10
   points=[radial(a0+(ae-a0)*j/128,z) for j in range(129)]
   points[0]=target
   # Penetración oculta debajo de la placa, entrando en el alojamiento circular.
   endpoint=Vector((sign*.55*S,10.57*S,(2.22+(z-2.725)*.45)*S))
   start=points[-1]
   for j in range(1,33):
    t=j/32;points.append(start.lerp(endpoint,t))
   hardware.append(tube('Cable al dial '+side+(' superior' if z>2 else ' inferior'),points,.024*S,model))
  # Unir las dos alturas en las guías delanteras y traseras.
  for y in (-3,3):
   points=[lateral(sign,y,1.7+2.05*j/80) for j in range(81)]
   hardware.append(tube('Retorno de guías '+side+str(y),points,.024*S,model))
  # Forro triangular del mecanismo: oculta los cables también por el interior.
  coords=[(-1.6,5.3),(1.6,5.3),(0,1.25)];vs=[];fs=[];idx={};N=36
  for j in range(N+1):
   for i in range(N+1-j):
    a=i/N;b=j/N;y=coords[0][0]*(1-a-b)+coords[1][0]*a+coords[2][0]*b;z=coords[0][1]*(1-a-b)+coords[1][1]*a+coords[2][1]*b
    p=lateral(sign,y,z);p.x-=sign*.12*S;idx[i,j]=len(vs);vs.append(p)
  for j in range(N):
   for i in range(N-j):
    f=(idx[i,j],idx[i+1,j],idx[i,j+1]);fs.append(f if sign>0 else f[::-1])
    if i+j<N-1:
     f=(idx[i+1,j],idx[i+1,j+1],idx[i,j+1]);fs.append(f if sign>0 else f[::-1])
  back=new_mesh('Forro triangular interior '+side,vs,fs,'lining',model)
  bpy.context.view_layer.objects.active=back;mod=back.modifiers.new('Espesor del forro','SOLIDIFY');mod.thickness=.035*S;mod.offset=-1;bpy.ops.object.modifier_apply(modifier=mod.name)
  textil.uv_for_mesh(back.data,back.matrix_world,'izquierdo');hardware.append(back)
 # Convertir todo el mecanismo en una sola malla editable con sus materiales.
 bpy.ops.object.select_all(action='DESELECT')
 for o in hardware:
  vg=o.vertex_groups.new(name=o.name);vg.add(list(range(len(o.data.vertices))),1.,'REPLACE')
  world=o.matrix_world.copy();o.parent=None;o.matrix_world=world;o.select_set(True)
 bpy.context.view_layer.objects.active=hardware[0];bpy.ops.object.join();mechanism=bpy.context.object
 mechanism.name='Sistema de ajuste | dial, soporte, laterales y cables';mechanism['conjunto']='ajuste';mechanism['uv_preservar']=True;mechanism['normal_bits']=16;mechanism['exportar_por_material']=True
 mechanism['descripcion']='Dial BOA, soporte, ajustes triangulares y cableado conectado. Los cables quedan dentro de la copa al ensamblar.'
 # Unificar ranuras por material (la malla mantiene colores, BOA y UV originales).
 oldm=list(mechanism.data.materials);newm=[];mapping={}
 for i,m in enumerate(oldm):
  if m not in newm:newm.append(m)
  mapping[i]=newm.index(m)
 mi=[mapping[p.material_index] for p in mechanism.data.polygons];mechanism.data.materials.clear()
 for m in newm:mechanism.data.materials.append(m)
 for p,i in zip(mechanism.data.polygons,mi):p.material_index=i
 # Sustituir los cuatro padres antiguos por los cinco nuevos conjuntos.
 for o in model.objects:
  if o.type=='MESH' and o.get('conjunto') in SPECS:
   world=o.matrix_world.copy();o.parent=None;o.matrix_world=world
 for o in list(model.objects):
  if o.type=='EMPTY' and o.get('pieza') in {'Copa','Dial y soporte','Ajuste izquierdo','Ajuste derecho'}:remove(o)
 parents={}
 for key,(label,delta,_,_) in SPECS.items():
  p=bpy.data.objects.new('CONJUNTO | '+label,None);model.objects.link(p);p['pieza']=label;p['conjunto']=key;p.empty_display_type='PLAIN_AXES';p.empty_display_size=.025
  for frame,amount in [(1,0),(60,1),(120,0)]:
   p.location=[v*S*amount for v in delta];p.keyframe_insert(data_path='location',frame=frame)
  p.animation_data.action.name='Despiece | '+label
  for fc in p.animation_data.action.fcurves:
   for k in fc.keyframe_points:k.interpolation='LINEAR'
  parents[key]=p
 scene.frame_set(1);bpy.context.view_layer.update()
 for o in model.objects:
  if o.type=='MESH' and o.get('conjunto') in parents:o.parent=parents[o['conjunto']]
 bpy.context.view_layer.update()
 return set(o.name for o in model.objects if o.type=='MESH' and o.get('conjunto') in SPECS)
