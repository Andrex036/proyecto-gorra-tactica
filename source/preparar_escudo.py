"""Prepara una malla de bajorrelieve cerrada desde la referencia DIPRO.

Se conserva el PNG original como textura; el contorno y las alturas tienen
geometría real. Requiere numpy, Pillow y scipy. La malla precalculada se incluye.
"""
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import gaussian_filter,label,binary_fill_holes,distance_transform_edt

ROOT=Path(__file__).resolve().parent
image=Image.open(ROOT/'assets/DIPRO.png').convert('RGBA')
width=420;height=round(width*image.height/image.width)
rgba=np.asarray(image.resize((width,height),Image.Resampling.LANCZOS)).astype(float)/255
rgb=rgba[:,:,:3];mask=rgba[:,:,3]>.5
labels,_=label(mask);sizes=np.bincount(labels.ravel());sizes[0]=0;mask=binary_fill_holes(labels==sizes.argmax())
# Regiones del escudo y la cinta, trazadas sobre los límites de la referencia.
def poly_mask(points):
 im=Image.new('L',(width,height));d=ImageDraw.Draw(im)
 d.polygon([(x/image.width*(width-1),y/image.height*(height-1)) for x,y in points],fill=255)
 return np.asarray(im,dtype=float)/255
shield=poly_mask([(205,331),(1055,331),(1064,500),(1036,678),(973,861),(875,1000),(754,1100),(631,1164),(507,1100),(385,1000),(286,861),(225,678),(198,500)])
banner=poly_mask([(209,204),(357,161),(630,202),(904,162),(1050,206),(1005,260),(1029,329),(906,304),(630,332),(355,302),(233,329),(260,261)])
yy,xx=np.mgrid[0:height,0:width];rr,gg,bb=rgb.transpose(2,0,1)
luma=.2126*rr+.7152*gg+.0722*bb
gold=np.clip((rr-bb-.16)*4,0,1)*np.clip((gg-bb-.08)*5,0,1)*np.clip((rr-.42)*4,0,1)
color=np.max(rgb,axis=2)-np.min(rgb,axis=2)
# Los rayos, el marco, las letras y las figuras tienen distintos niveles.
outer=(1-np.maximum(shield,banner))*mask
height_cm=.07+.17*outer*np.clip((luma-.18)/.7,0,1)
height_cm+=.13*shield+.16*banner
height_cm+=.080*gold*np.maximum(shield,banner)
# Relieve fino de las figuras y texto, conservando el dibujo original.
interior=poly_mask([(344,433),(918,433),(914,601),(874,769),(787,911),(631,1026),(476,912),(390,770),(348,602)])
subject=(color>.30)&(gg>bb*.72)&(rr<.86)
height_cm+=interior*(.032*subject+.014*(1-luma))
# La estrella central se eleva sobre los cuatro cuarteles.
star=poly_mask([(630,602),(653,655),(710,655),(664,688),(682,751),(630,713),(579,751),(596,691),(549,658),(607,657)])
height_cm+=.11*star
height_cm=gaussian_filter(height_cm,.55)
# Bisel pequeño junto al contorno sin perder las puntas de la silueta.
edge=np.clip(distance_transform_edt(mask)/2.0,0,1)
height_cm=.035+height_cm*edge
badge_width=5.65;badge_height=badge_width*image.height/image.width;center_z=4.6
x=(xx/(width-1)-.5)*badge_width;z=center_z+(.5-yy/(height-1))*badge_height

def front_y(x,z,offset):
 r=np.maximum(.001,1-(z/11.6)**2)**.425
 return -10.4*r*np.sqrt(np.maximum(.001,1-(x/(9.4*r))**2))-offset

indices=np.full((height,width),-1,dtype=np.int32);indices[mask]=np.arange(mask.sum())
front=np.column_stack((x[mask],front_y(x[mask],z[mask],.12+height_cm[mask]),z[mask])).astype('f4')
back=np.column_stack((x[mask],front_y(x[mask],z[mask],.095),z[mask])).astype('f4')
uv=np.column_stack((xx[mask]/(width-1),1-yy[mask]/(height-1))).astype('f4')
a=indices[:-1,:-1].ravel();b=indices[:-1,1:].ravel();c=indices[1:,:-1].ravel();d=indices[1:,1:].ravel()
tri=np.concatenate((np.column_stack((a,c,b)),np.column_stack((b,c,d))))
tri=tri[np.all(tri>=0,axis=1)].astype('i4')
# Eliminar vértices aislados y crear tapa posterior y paredes laterales.
used=np.unique(tri);remap=np.full(len(front),-1,dtype=np.int32);remap[used]=np.arange(len(used));tri=remap[tri]
front=front[used];back=back[used];uv=uv[used];n=len(front)
edges=np.concatenate((tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]));keys=np.sort(edges,axis=1)
_,first,counts=np.unique(keys,axis=0,return_index=True,return_counts=True);boundary=edges[first[counts==1]]
side=np.concatenate((np.column_stack((boundary[:,1],boundary[:,0],boundary[:,0]+n)),np.column_stack((boundary[:,1],boundary[:,0]+n,boundary[:,1]+n))))
faces=np.concatenate((tri,tri[:,::-1]+n,side)).astype('i4')
material=np.concatenate((np.zeros(len(tri),dtype='i4'),np.ones(len(tri)+len(side),dtype='i4')))
np.savez_compressed(ROOT/'assets/dipro-relieve.npz',positions=np.concatenate((front,back)),faces=faces,uv=np.concatenate((uv,uv)),material=material)
print({'vertices':len(front)*2,'triangles':len(faces),'height_cm':badge_height,'maximum_relief_cm':float(height_cm[mask].max())})
