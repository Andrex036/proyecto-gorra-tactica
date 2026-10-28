"""Luz de producto y acabados textiles compartidos por el archivo y los renders."""
import bpy
from mathutils import Vector

def materiales():
    for m in bpy.data.materials:
        if not m.use_nodes:continue
        p=m.node_tree.nodes.get('Principled BSDF');role=m.get('role')
        if p is None:continue
        if role in {'fabric','trim','thread','inset','badge_base','lining'}:
            p.inputs['Roughness'].default_value=.94 if role=='lining' else .86
            p.inputs['Sheen Weight'].default_value=.08 if role=='lining' else .12
            p.inputs['Sheen Roughness'].default_value=.78
            p.inputs['Sheen Tint'].default_value=(.08,.09,.10,1)
            p.inputs['Specular IOR Level'].default_value=.30
            for node in m.node_tree.nodes:
                if node.type=='NORMAL_MAP':node.inputs['Strength'].default_value=.22 if role=='lining' else .42
        elif role=='accent':
            p.inputs['Roughness'].default_value=.46;p.inputs['Metallic'].default_value=.45

def iluminar(samples=64):
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=samples;scene.cycles.use_denoising=True
    scene.cycles.use_adaptive_sampling=True;scene.cycles.adaptive_threshold=.015
    scene.render.threads_mode='FIXED';scene.render.threads=8
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=-.15
    scene.world.use_nodes=True
    bg=scene.world.node_tree.nodes.get('Background');bg.inputs['Color'].default_value=(.65,.69,.76,1);bg.inputs['Strength'].default_value=.20
    for o in list(bpy.data.objects):
        if o.name.startswith('Estudio realista |'):bpy.data.objects.remove(o,do_unlink=True)
        elif o.type=='LIGHT':o.hide_render=True
        elif o.name=='Suelo estudio':o.hide_render=True
    # Una caja principal amplia, relleno moderado y recorte posterior.
    for name,pos,power,width,height,color in [
        ('Principal',(-.28,-.32,.45),7.0,.32,.42,(1,.95,.88)),
        ('Relleno',(.32,-.18,.22),1.7,.40,.50,(.88,.94,1)),
        ('Recorte',(.08,.24,.35),5.5,.20,.42,(1,.98,.94)),
        ('Interior',(0,-.10,-.28),.45,.32,.32,(.95,.97,1)),
    ]:
        d=bpy.data.lights.new('Estudio realista | '+name,'AREA');d.energy=power;d.shape='RECTANGLE';d.size=width;d.size_y=height;d.color=color
        o=bpy.data.objects.new(d.name,d);scene.collection.objects.link(o);o.location=pos
        o.rotation_euler=(Vector((0,-.025,.025))-o.location).to_track_quat('-Z','Y').to_euler()
    materiales()
