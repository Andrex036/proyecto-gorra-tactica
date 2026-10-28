"""Exportación de mallas para el visor, incluyendo el material original del DIPRO."""
import bpy
import textil

DELTAS={'copa':(0,0,7),'visera':(0,-11,-3),'cervical':(0,10,-5),'dial':(0,17,5),'izquierdo':(-11,0,2),'derecho':(11,0,2),'escudo':(0,-10,8),'banda':(0,0,-10)}

from paneles_copa import DELTAS as PANELES_DELTAS
DELTAS.update(PANELES_DELTAS)

def partes(model,only_names=None):
    scene=bpy.context.scene;scene.frame_set(1);bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get();parts=[]
    for o in list(model.objects):
        if o.type!='MESH' or (only_names is not None and o.name not in only_names):continue
        eo=o.evaluated_get(deps);preview_mesh=bpy.data.meshes.new_from_object(eo)
        preview=bpy.data.objects.new('_export_preview',preview_mesh);scene.collection.objects.link(preview);preview.matrix_world=eo.matrix_world
        is_dipro=o.get('material_role')=='dipro'
        preserve_uv=bool(o.get('uv_preservar'))
        is_edge=preserve_uv or o.name in {'04 Visera redondeada con caída','Ribete exterior visera'}
        if len(preview_mesh.vertices)>250 and not is_edge and o.get('material_role')!='boa':
            dec=preview.modifiers.new('Vista ligera','DECIMATE');dec.ratio=.80 if is_dipro else (.72 if o.get('detalle_fino') else (.55 if 'hoja' in o.name.lower() or 'cervical' in o.name.lower() else .38))
        bpy.context.view_layer.update();pe=preview.evaluated_get(bpy.context.evaluated_depsgraph_get());me=pe.to_mesh();me.calc_loop_triangles()
        key=o.get('conjunto','copa');uv=me.uv_layers.active if (is_dipro or preserve_uv) else textil.uv_for_mesh(me,eo.matrix_world,key)
        normal_matrix=eo.matrix_world.to_3x3().inverted().transposed()
        for material_index in sorted(set(t.material_index for t in me.loop_triangles)):
            mat=o.data.materials[material_index];role=mat.get('role',o.get('material_role','fabric'))
            vs=[];ns=[];ind=[];uvs=[];lookup={}
            for t in me.loop_triangles:
                if t.material_index!=material_index:continue
                for li in t.loops:
                    vi=me.loops[li].vertex_index;tex=uv.data[li].uv;cn=me.corner_normals[li].vector;ident=(vi,round(tex.x,5),round(tex.y,5),*(round(v,5) for v in cn))
                    if ident not in lookup:
                        lookup[ident]=len(vs)//3;vert=me.vertices[vi];p=eo.matrix_world@vert.co;n=(normal_matrix@cn).normalized()
                        vs.extend([p.x*100,p.z*100,-p.y*100]);ns.extend([n.x,n.z,-n.y]);uvs.extend(tex)
                    ind.append(lookup[ident])
            delta=DELTAS[key];name=o.name+(' | anverso' if material_index==0 else ' | reverso y canto') if is_dipro else o.name
            if o.get('exportar_por_material'):name=o.name+' | '+role
            elif preserve_uv and len(o.data.materials)>1:name=o.name+(' | exterior' if material_index==0 else ' | interior y remates')
            parts.append({'normal_bits':int(o.get('normal_bits',8)),'n':name,'p':vs,'v':ns,'i':ind,'uv':uvs,'role':role,'c':list(mat.diffuse_color[:3]),'g':key,'d':[delta[0],delta[2],-delta[1]]})
        pe.to_mesh_clear();bpy.data.objects.remove(preview,do_unlink=True);bpy.data.meshes.remove(preview_mesh)
    return parts
