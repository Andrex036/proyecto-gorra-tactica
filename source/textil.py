"""Material textil compartido por Blender, GLB y el visor Three.js.

La trama normal es periódica de 1024 px: ocho hilos por baldosa de 4,8 mm.
Las UV se expresan en esa escala física, no dependen del tamaño de cada pieza.
"""
import bpy, math, numpy as np

TILE_CM = .48
PALETTES = {
    'negro': {'fabric':'171b20','trim':'0c1014','thread':'343a40','inset':'11161b','accent':'c6a85d','badge_base':'11161b','hardware':'20262c'},
    'gris': {'fabric':'626b70','trim':'414b52','thread':'899399','inset':'364148','accent':'d0d6db','badge_base':'354149','hardware':'333b43'},
    'beige': {'fabric':'c4b18d','trim':'9c8969','thread':'d6c5a5','inset':'aa9673','accent':'b7954f','badge_base':'a5906b','hardware':'3c3a33'},
}
# El forro conserva el color de la tela y suaviza la trama interior.
for palette in PALETTES.values():palette['lining']=palette['fabric']

def linear_hex(value):
    rgb=[int(value[i:i+2],16)/255 for i in (0,2,4)]
    return tuple(c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in rgb)

def make_normal():
    size=1024
    yy,xx=np.mgrid[0:size,0:size].astype(np.float32)
    p=8*xx/size;q=8*yy/size
    px=np.maximum(0,np.sin(np.pi*(p%1)))**.55
    py=np.maximum(0,np.sin(np.pi*(q%1)))**.55
    warp=px*(.62+.38*np.cos(np.pi*(np.floor(p)+q-.5)))
    weft=py*(.62-.38*np.cos(np.pi*(np.floor(q)+p-.5)))
    fibers=np.where(warp>weft,.015*np.sin(2*np.pi*p*7),.015*np.sin(2*np.pi*q*7))
    h=np.maximum(warp,weft)+fibers
    nx=-(np.roll(h,-1,axis=1)-np.roll(h,1,axis=1))*16
    ny=-(np.roll(h,-1,axis=0)-np.roll(h,1,axis=0))*16
    length=np.sqrt(nx*nx+ny*ny+1)
    rgba=np.stack((nx/length*.5+.5,ny/length*.5+.5,1/length*.5+.5,np.ones_like(h)),axis=-1)
    im=bpy.data.images.new('Tela | trama tejida 1024',width=size,height=size,alpha=True)
    im.colorspace_settings.name='Non-Color';im.pixels.foreach_set(rgba.reshape(-1));im.pack()
    return im

def materials():
    image=make_normal();result={}
    for role,color in PALETTES['gris'].items():
        m=bpy.data.materials.new('Textil | '+role);m.use_nodes=True;m['role']=role
        rgb=linear_hex(color);m.diffuse_color=(*rgb,1)
        nodes=m.node_tree.nodes;links=m.node_tree.links;p=nodes.get('Principled BSDF')
        p.inputs['Base Color'].default_value=(*rgb,1)
        p.inputs['Roughness'].default_value=.40 if role=='accent' else (.57 if role=='hardware' else (.96 if role=='lining' else .90))
        p.inputs['Metallic'].default_value=.38 if role=='accent' else .05 if role=='hardware' else 0
        if role not in {'accent','hardware'}:
            tex=nodes.new('ShaderNodeTexImage');tex.image=image;tex.extension='REPEAT';tex.interpolation='Linear'
            normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.25 if role=='lining' else .65
            links.new(tex.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],p.inputs['Normal'])
        result[role]=m
    return result

def role_for(obj,group):
    n=obj.name.lower()
    if group=='escudo':return 'badge_base' if 'base escudo' in n else 'accent'
    if group=='visera' and any(x in n for x in ['laurel','nervadura','trenza perimetral']):return 'accent'
    original=obj.data.materials[0].name if obj.data.materials else ''
    if any(x in n for x in ['cable','guía cable','dial cuerpo','dial cara','dial centro','estrías','aro frontal']):return 'hardware'
    if 'costuras' in original or 'puntadas' in n:return 'thread'
    if 'fuelles' in original:return 'inset'
    if 'bordes' in original or 'trenza' in n:return 'trim'
    if 'mecanismo' in original:return 'hardware'
    return 'fabric'

def uv_for_mesh(me,matrix,group):
    uv=me.uv_layers.active or me.uv_layers.new(name='Trama a escala')
    period=2*math.pi*9.5/TILE_CM
    cylindrical=group in {'cervical','banda','ajuste'}
    coords=[]
    for v in me.vertices:
        p=matrix@v.co;x,y,z=(p.x*100,p.y*100,p.z*100)
        if group=='copa' or group.startswith('panel_'):
            # Proyección desde la cima: evita comprimir los hilos en anillos
            # alrededor del botón, como ocurriría con una UV cilíndrica.
            radius=math.hypot(x,y)
            scale=11*math.atan2(radius,max(.01,z))/max(.00001,radius)/TILE_CM
            u=x*scale;v=y*scale
        elif cylindrical:u=math.atan2(x,y)*9.5/TILE_CM;v=z/TILE_CM
        elif group=='visera':u=x/TILE_CM;v=-y/TILE_CM
        elif group in {'izquierdo','derecho'}:u=y/TILE_CM;v=z/TILE_CM
        else:u=x/TILE_CM;v=z/TILE_CM
        coords.append((u,v))
    for face in me.polygons:
        points=[coords[me.loops[i].vertex_index] for i in face.loop_indices]
        crosses=cylindrical and max(p[0] for p in points)-min(p[0] for p in points)>period/2
        for i,(u,v) in zip(face.loop_indices,points):uv.data[i].uv=(u+period if crosses and u<0 else u,v)
    return uv

def set_palette(name):
    for m in bpy.data.materials:
        role=m.get('role')
        if role in PALETTES[name]:
            rgb=linear_hex(PALETTES[name][role]);m.diffuse_color=(*rgb,1)
            m.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(*rgb,1)
