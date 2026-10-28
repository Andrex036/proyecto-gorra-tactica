/* Trama textil periódica, 1024 px, compartida con source/textil.py. */
window.GORRA_TEXTILE = (() => {
  'use strict';
  const palettes = {
    negro: {label:'Negro',contrast:'dorado',fabric:'#171b20',trim:'#0c1014',thread:'#343a40',inset:'#11161b',accent:'#c6a85d',badge_base:'#11161b',hardware:'#20262c'},
    gris: {label:'Gris',contrast:'plata',fabric:'#626b70',trim:'#414b52',thread:'#899399',inset:'#364148',accent:'#d0d6db',badge_base:'#354149',hardware:'#333b43'},
    beige: {label:'Beige',contrast:'dorado',fabric:'#c4b18d',trim:'#9c8969',thread:'#d6c5a5',inset:'#aa9673',accent:'#b7954f',badge_base:'#a5906b',hardware:'#3c3a33'}
  };
  for (const palette of Object.values(palettes)) palette.lining = palette.fabric;
  function createNormalMap() {
    const size=1024, height=new Float32Array(size*size), pixels=new Uint8Array(size*size*4);
    for(let y=0;y<size;y++) for(let x=0;x<size;x++) {
      const p=8*x/size,q=8*y/size;
      const px=Math.pow(Math.max(0,Math.sin(Math.PI*(p%1))),.55);
      const py=Math.pow(Math.max(0,Math.sin(Math.PI*(q%1))),.55);
      const warp=px*(.62+.38*Math.cos(Math.PI*(Math.floor(p)+q-.5)));
      const weft=py*(.62-.38*Math.cos(Math.PI*(Math.floor(q)+p-.5)));
      height[y*size+x]=Math.max(warp,weft)+.015*Math.sin(2*Math.PI*(warp>weft?p:q)*7);
    }
    for(let y=0;y<size;y++) for(let x=0;x<size;x++) {
      const nx=-(height[y*size+(x+1)%size]-height[y*size+(x+size-1)%size])*16;
      const ny=-(height[((y+1)%size)*size+x]-height[((y+size-1)%size)*size+x])*16;
      const length=Math.hypot(nx,ny,1),i=(y*size+x)*4;
      pixels[i]=Math.round((nx/length*.5+.5)*255);
      pixels[i+1]=Math.round((ny/length*.5+.5)*255);
      pixels[i+2]=Math.round((1/length*.5+.5)*255);pixels[i+3]=255;
    }
    const map=new THREE.DataTexture(pixels,size,size,THREE.RGBAFormat);
    map.name='Tela tejida 1024';map.wrapS=map.wrapT=THREE.RepeatWrapping;
    map.magFilter=THREE.LinearFilter;map.minFilter=THREE.LinearMipmapLinearFilter;
    map.generateMipmaps=true;map.needsUpdate=true;
    return map;
  }
  return {palettes,createNormalMap};
})();
