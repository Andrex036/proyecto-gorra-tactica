"""Borde uniforme de visera y escudo DIPRO de bajorrelieve, para Blender 4.3+."""
from pathlib import Path
import math
import bpy
import numpy as np
import ajuste_visera as ajuste
import textil

ROOT=Path(__file__).resolve().parent

def replace_mesh(obj,vertices,faces):
    old=obj.data;mat=list(old.materials)
    data=bpy.data.meshes.new(obj.name+' | geometría regular')
    data.from_pydata((np.asarray(vertices)*.01).tolist(),[],np.asarray(faces,dtype=int).tolist());data.update()
    obj.data=data
    for material in mat:data.materials.append(material)
    for p in data.polygons:p.use_smooth=True
    textil.uv_for_mesh(data,obj.matrix_world,'visera')
    if old.users==0:bpy.data.meshes.remove(old)
    return data


def visor_grid():
    # Muestreo por longitud: no se comprimen las caras ni los remates del borde.
    grid=np.linspace(-math.pi/2,math.pi/2,10001)
    edge=ajuste.borde_exterior(grid)
    length=np.r_[0,np.cumsum(np.linalg.norm(np.diff(edge,axis=0),axis=1))]
    theta=np.interp(np.linspace(0,1,257),length/length[-1],grid)
    vv=np.linspace(0,1,25)
    t=np.repeat(theta[1:-1],len(vv));v=np.tile(vv,len(theta)-2)
    top=ajuste.deformar_superficie(ajuste.visor_base(t,v=v,off=0))
    eps=1.e-5
    dt=ajuste.deformar_superficie(ajuste.visor_base(t+eps,v=v,off=0))-ajuste.deformar_superficie(ajuste.visor_base(t-eps,v=v,off=0))
    dv=ajuste.deformar_superficie(ajuste.visor_base(t,v=v+eps,off=0))-ajuste.deformar_superficie(ajuste.visor_base(t,v=v-eps,off=0))
    normal=np.cross(dv,dt);normal/=np.linalg.norm(normal,axis=1)[:,None]
    # Transición suave del espesor antes del encuentro con la copa.
    tip=np.minimum(np.repeat(length[-1]*np.linspace(0,1,257)[1:-1],len(vv)),np.repeat(length[-1]*(1-np.linspace(0,1,257)[1:-1]),len(vv)))
    fade=np.clip(tip/.9,0,1);fade=fade*fade*(3-2*fade)
    normal=normal*fade[:,None]+np.array([0,0,1])*(1-fade[:,None]);normal/=np.linalg.norm(normal,axis=1)[:,None]
    ends=ajuste.borde_exterior(np.array([-math.pi/2,math.pi/2]))
    top=np.vstack((ends[0],top,ends[1]));normal=np.vstack(([0,0,1],normal,[0,0,1]))
    bottom=top-.25*normal;n=len(top);faces=[];B=len(vv);rows=len(theta)-2
    for j in range(B-1):faces.append((0,1+j+1,1+j))
    for i in range(rows-1):
        for j in range(B-1):
            a=1+i*B+j;b=a+1;c=a+B;d=c+1
            faces.extend(((a,b,c),(b,d,c)))
    for j in range(B-1):faces.append((n-1,1+(rows-1)*B+j,1+(rows-1)*B+j+1))
    faces=np.asarray(faces,dtype=int)
    # Orientación de la tapa superior hacia arriba.
    tri=top[faces];norm=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
    if norm[:,2].mean()<0:faces=faces[:,::-1]
    edges=np.concatenate((faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]));keys=np.sort(edges,axis=1)
    _,first,count=np.unique(keys,axis=0,return_index=True,return_counts=True);bd=edges[first[count==1]]
    side=np.concatenate((np.c_[bd[:,1],bd[:,0],bd[:,0]+n],np.c_[bd[:,1],bd[:,0]+n,bd[:,1]+n]))
    return np.vstack((top,bottom)),np.vstack((faces,faces[:,::-1]+n,side))


def rim_mesh():
    # Sección circular constante y transporte suave, con remates dentro de la unión.
    th=np.linspace(-math.pi/2,math.pi/2,10001);edge=ajuste.borde_exterior(th)
    arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(edge,axis=0),axis=1))]
    t=np.interp(np.linspace(0,1,361),arc/arc[-1],th)
    p=ajuste.borde_exterior(t)
    dt=np.gradient(p,axis=0);dt/=np.linalg.norm(dt,axis=1)[:,None]
    # El perfil se mantiene circular sin aplastarse en la punta.
    reference=np.tile([0.,0.,1.],(len(p),1));normal=reference-dt*np.sum(reference*dt,axis=1)[:,None]
    normal/=np.linalg.norm(normal,axis=1)[:,None]
    centers=p-.12*normal
    centers=np.vstack((centers[0]-.14*dt[0],centers,centers[-1]+.14*dt[-1]))
    tangent=np.gradient(centers,axis=0);tangent/=np.linalg.norm(tangent,axis=1)[:,None]
    normal=np.tile([0.,0.,1.],(len(centers),1));normal-=tangent*np.sum(normal*tangent,axis=1)[:,None];normal/=np.linalg.norm(normal,axis=1)[:,None]
    lateral=np.cross(tangent,normal);q=np.linspace(0,2*math.pi,13)[:-1]
    vertices=centers[:,None,:]+.13*(normal[:,None,:]*np.cos(q)[None,:,None]+lateral[:,None,:]*np.sin(q)[None,:,None])
    vertices=vertices.reshape(-1,3);faces=[];K=len(q)
    for i in range(len(centers)-1):
        for j in range(K):
            a=i*K+j;b=i*K+(j+1)%K;c=a+K;d=b+K;faces.extend(((a,c,b),(b,c,d)))
    left=len(vertices);right=left+1;vertices=np.vstack((vertices,centers[0],centers[-1]))
    for j in range(K):faces.extend(((left,(j+1)%K,j),(right,(len(centers)-1)*K+j,(len(centers)-1)*K+(j+1)%K)))
    return vertices,np.array(faces,dtype=int)


def material_dipro():
    im=bpy.data.images.load(str(ROOT/'assets/DIPRO.png'),check_existing=True);im.name='DIPRO | imagen original';im.pack()
    m=bpy.data.materials.new('DIPRO | colores originales');m.use_nodes=True;m['role']='dipro';m.diffuse_color=(1,1,1,1)
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Roughness'].default_value=.40;p.inputs['Metallic'].default_value=.28
    tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=im;tex.interpolation='Linear';tex.extension='EXTEND'
    m.node_tree.links.new(tex.outputs['Color'],p.inputs['Base Color'])
    gold=bpy.data.materials.new('DIPRO | reverso y canto dorado');gold.use_nodes=True;gold['role']='dipro_gold'
    rgb=textil.linear_hex('c6a052');gold.diffuse_color=(*rgb,1);p=gold.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*rgb,1);p.inputs['Metallic'].default_value=.65;p.inputs['Roughness'].default_value=.32
    return m,gold


def aplicar():
    scene=bpy.context.scene;scene.frame_set(1)
    model=bpy.data.collections['GORRA | piezas editables']
    parents={o.get('pieza'):o for o in model.objects if o.type=='EMPTY'}
    brim=bpy.data.objects['04 Visera redondeada con caída'];rim=bpy.data.objects['Ribete exterior visera']
    replace_mesh(brim,*visor_grid());replace_mesh(rim,*rim_mesh())
    brim['acabado']='Cuerpo cerrado y simétrico, espesor 2,5 mm; remates regulares.'
    rim['acabado']='Sección circular constante de 2,6 mm y uniones continuas.'
    for obj in list(model.objects):
        if obj.type=='MESH' and obj.get('conjunto')=='escudo':bpy.data.objects.remove(obj,do_unlink=True)
    data=np.load(ROOT/'assets/dipro-relieve.npz')
    mesh=bpy.data.meshes.new('DIPRO | bajorrelieve cerrado')
    mesh.from_pydata((data['positions']*.01).tolist(),[],data['faces'].tolist());mesh.update()
    obj=bpy.data.objects.new('05 Escudo DIPRO | bajorrelieve',mesh);model.objects.link(obj);obj.parent=parents['Escudo frontal']
    obj['conjunto']='escudo';obj['material_role']='dipro';obj['detalle_fino']=True;obj['fuente']='DIPRO.png: contorno, proporciones, textos y colores originales.'
    for m in material_dipro():mesh.materials.append(m)
    mesh.polygons.foreach_set('material_index',data['material'])
    for poly in mesh.polygons:poly.use_smooth=True
    uv=mesh.uv_layers.new(name='DIPRO original')
    loops=np.empty(len(mesh.loops),dtype=np.int32);mesh.loops.foreach_get('vertex_index',loops)
    uv.data.foreach_set('uv',data['uv'][loops].astype(np.float32).reshape(-1))
    # Simplificar las zonas casi planas manteniendo el contorno y las UV originales.
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    modifier=obj.modifiers.new('Relieve optimizado','DECIMATE');modifier.ratio=.50
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.context.view_layer.update()
    return obj
