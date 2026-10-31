/* Visor técnico: ocho fichas, geometría original y render bajo demanda. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const shell=$('explorador'),stage=$('model-stage'),workspace=$('viewer-workspace');
  const loading=$('model-loading'),status=$('model-status'),pieceInput=$('piece');
  const viewInput=$('view'),wireInput=$('wireframe'),separationInput=$('separation');
  const technical=window.GORRA_TECHNICAL;
  const reducedMotion=window.matchMedia('(prefers-reduced-motion: reduce)');
  let engine=null,currentColor='negro',fallback=false;
  const presets={tres:[.66,.32],frente:[0,.15],lado:[Math.PI/2,.12],izquierda:[-Math.PI/2,.12],atras:[Math.PI,.18],superior:[.35,1.35],abajo:[.5,-.9]};
  const renderControls=['view','wireframe','separation','lighting','zoom-in','zoom-out','mode-assembled','mode-exploded','hero-explode','reset-model'];
  renderControls.forEach(id=>$(id).disabled=true);

  function updateTechnical(key) {
    const data=technical[key];
    $('technical-panel').hidden=!data;
    workspace.classList.toggle('has-detail',!!data);
    $('show-all').hidden=!data;
    $('viewer-current').textContent=data?data.name:'Modelo completo';
    $('stage-state').textContent=data?'COMPONENTE AISLADO':'GORRA ARMADA';
    $('piece-view-option').hidden=!data;
    document.querySelectorAll('.component-row').forEach(button=>{
      const active=button.dataset.piece===key;
      button.classList.toggle('selected',active);button.setAttribute('aria-pressed',String(active));
    });
    if(data){
      $('technical-title').textContent=data.name;$('technical-summary').textContent=data.summary;
      $('technical-measure').textContent=data.measure;$('technical-measure-label').textContent=data.measureLabel;
      $('technical-quantity').textContent=data.quantity;$('technical-note').textContent=data.note;
      const items=data.details.map(([label,value])=>{const div=document.createElement('div'),dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=label;dd.textContent=value;div.append(dt,dd);return div;});
      $('technical-specs').replaceChildren(...items);$('technical-panel').scrollTop=0;
    }
    if(fallback)updateFallback();
  }
  function updateFallback(){
    const key=pieceInput.value,img=$('model-fallback');
    img.src=key==='todas'?`assets/partes/modelo-${currentColor}.png?v=gorra-v2-20261030`:`assets/partes/${key}.png?v=gorra-v2-20261030`;
    img.alt=key==='todas'?`Vista de la gorra en ${currentColor}`:`Vista de referencia de ${technical[key].name} en negro`;
    if(key!=='todas')$('finish-color').textContent='REFERENCIA EN NEGRO';
    else $('finish-color').textContent=`${currentColor} / ${window.GORRA_TEXTILE.palettes[currentColor].contrast}`.toUpperCase();
  }
  function selectPiece(key,scroll=false){
    if(key!=='todas'&&!technical[key])return;
    pieceInput.value=key;updateTechnical(key);engine?.selectPiece(key);
    status.textContent=key==='todas'?'Modelo completo.':`${technical[key].name}. Ficha técnica disponible junto al modelo.`;
    if(scroll){shell.scrollIntoView({behavior:reducedMotion.matches?'auto':'smooth',block:'start'});}
  }
  function selectColor(key){
    const palette=window.GORRA_TEXTILE.palettes[key];if(!palette)return;currentColor=key;
    document.querySelectorAll('.color-button').forEach(button=>{const on=button.dataset.color===key;button.classList.toggle('active',on);button.setAttribute('aria-pressed',String(on));});
    shell.dataset.color=key;$('accent-label').textContent=`Bordado en ${palette.contrast}`;
    $('finish-color').textContent=`${palette.label} / ${palette.contrast}`.toUpperCase();
    engine?.selectColor(key);if(fallback)updateFallback();
    status.textContent=`Acabado ${palette.label.toLowerCase()}, bordado en ${palette.contrast}.`;
  }
  function mode(amount){
    if(!engine)return;pieceInput.value='todas';updateTechnical('todas');engine.animateSeparation(amount);
  }
  document.querySelectorAll('.component-row').forEach(button=>button.addEventListener('click',()=>selectPiece(button.dataset.piece,true)));
  document.querySelectorAll('.color-button').forEach(button=>button.addEventListener('click',()=>selectColor(button.dataset.color)));
  $('show-all').addEventListener('click',()=>selectPiece('todas'));
  $('close-technical').addEventListener('click',()=>selectPiece('todas'));
  pieceInput.addEventListener('change',()=>selectPiece(pieceInput.value));
  $('mode-assembled').addEventListener('click',()=>mode(0));$('mode-exploded').addEventListener('click',()=>mode(1));
  $('hero-explode').addEventListener('click',()=>{mode(1);shell.scrollIntoView({behavior:reducedMotion.matches?'auto':'smooth'});});
  $('reset-model').addEventListener('click',()=>{selectPiece('todas');engine?.reset();});
  viewInput.addEventListener('change',()=>engine?.setView(viewInput.value));
  wireInput.addEventListener('change',()=>engine?.setWire(wireInput.checked));
  $('lighting').addEventListener('change',()=>engine?.setLighting($('lighting').value));
  separationInput.addEventListener('input',()=>{if(pieceInput.value!=='todas'){pieceInput.value='todas';updateTechnical('todas');}engine?.setSeparation(Number(separationInput.value)/100);});
  separationInput.addEventListener('change',()=>engine?.announce());
  $('zoom-in').addEventListener('click',()=>engine?.changeZoom(.15));$('zoom-out').addEventListener('click',()=>engine?.changeZoom(-.15));
  $('fullscreen').addEventListener('click',async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await shell.requestFullscreen();}catch{status.textContent='La pantalla completa no está disponible en este navegador.';}});
  document.addEventListener('fullscreenchange',()=>{$('fullscreen').setAttribute('aria-label',document.fullscreenElement?'Salir de pantalla completa':'Abrir en pantalla completa');});
  if(!shell.requestFullscreen)$('fullscreen').hidden=true;
  selectColor(currentColor);updateTechnical('todas');

  async function init(){
    if (!window.THREE || !window.GORRA_MODEL_DATA || !window.GORRA_TEXTILE || !window.GORRA_DIPRO_TEXTURE || !window.DecompressionStream) {
      throw new Error('Falta una función necesaria para el visor.');
    }

    // El modelo va incluido en JavaScript: funciona también al abrir index.html.
    const raw = Uint8Array.from(atob(window.GORRA_MODEL_DATA), (c) => c.charCodeAt(0));
    const stream = new Blob([raw]).stream().pipeThrough(new DecompressionStream('deflate'));
    const buffer = await new Response(stream).arrayBuffer();
    const data = new DataView(buffer);
    const headerLength = data.getUint32(0, true);
    const parts = JSON.parse(new TextDecoder().decode(new Uint8Array(buffer, 4, headerLength)));
    const start = 4 + headerLength;
    const scene = new THREE.Scene();
    const group = new THREE.Group();
    const meshes = [];
    const textile = window.GORRA_TEXTILE;
    const normalMap = textile.createNormalMap();
    const materials = {};
    for (const role of ['fabric','trim','thread','inset','accent','badge_base','hardware','lining']) {
      const isFabric = role !== 'accent' && role !== 'hardware';
      materials[role] = new THREE.MeshPhysicalMaterial({
        color: textile.palettes[currentColor][role],
        roughness: role === 'accent' ? .46 : (role === 'hardware' ? .57 : (role === 'lining' ? .94 : .86)),
        metalness: role === 'accent' ? .45 : (role === 'hardware' ? .05 : 0),
        sheen: isFabric ? (role === 'lining' ? .08 : .12) : 0,
        sheenRoughness: .78,
        sheenColor: new THREE.Color(.08,.09,.10),
        specularIntensity: isFabric ? .6 : 1,
        envMapIntensity: .35,
        side: THREE.DoubleSide,
        normalMap: isFabric ? normalMap : null,
        normalScale: new THREE.Vector2(role === 'lining' ? .22 : .42, role === 'lining' ? .22 : .42)
      });
    }
    const diproMap = await new THREE.TextureLoader().loadAsync(window.GORRA_DIPRO_TEXTURE);
    diproMap.colorSpace = THREE.SRGBColorSpace;
    materials.dipro = new THREE.MeshStandardMaterial({ color: 0xffffff, map: diproMap, roughness: .40, metalness: .28, side: THREE.DoubleSide });
    materials.dipro_gold = new THREE.MeshStandardMaterial({ color: 0xc6a052, roughness: .32, metalness: .65, side: THREE.DoubleSide });
    materials.boa = new THREE.MeshStandardMaterial({ color: 0x080b0d, roughness: .64, metalness: .05, side: THREE.DoubleSide });
    scene.add(group);
    let triangles = 0;

    for (const [name, count, indexCount, offset, rgb, key, delta, hasUV, role, normalBits = 8] of parts) {
      let cursor = start + offset;
      const positions = new Float32Array(count * 3);
      const normals = new Float32Array(count * 3);
      const indices = new Uint32Array(indexCount);
      for (let i = 0; i < positions.length; i++, cursor += 2) positions[i] = data.getInt16(cursor, true) / 1000;
      for (let i = 0; i < normals.length; i++) {
        normals[i] = normalBits === 16 ? data.getInt16(cursor, true) / 32767 : data.getInt8(cursor) / 127;
        cursor += normalBits === 16 ? 2 : 1;
      }
      for (let i = 0; i < indices.length; i++, cursor += 4) indices[i] = data.getUint32(cursor, true);
      const uv = new Float32Array(count * 2);
      if (hasUV) for (let i = 0; i < uv.length; i++, cursor += 4) uv[i] = data.getFloat32(cursor, true);
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
      geometry.setAttribute('normal', new THREE.BufferAttribute(normals, 3));
      geometry.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
      geometry.setIndex(new THREE.BufferAttribute(indices, 1));
      const material = materials[role] || materials.fabric;
      const mesh = new THREE.Mesh(geometry, material);
      mesh.castShadow=true;mesh.receiveShadow=true;
      mesh.name = name;
      mesh.userData.piece = key;
      mesh.userData.materialRole = role;
      mesh.userData.delta = new THREE.Vector3(...delta);
      group.add(mesh);
      meshes.push(mesh);
      triangles += indexCount / 3;
    }

    const initialBounds=new THREE.Box3().setFromObject(group);
    group.position.copy(initialBounds.getCenter(new THREE.Vector3())).multiplyScalar(-1);
    const renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});
    normalMap.anisotropy=Math.min(8,renderer.capabilities.getMaxAnisotropy());diproMap.anisotropy=normalMap.anisotropy;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,2));renderer.setClearColor(0,0);
    renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.04;
    renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
    // Cajas de luz para reflejos amplios en el hilo y las superficies del ajuste.
    const studio=new THREE.Scene();studio.background=new THREE.Color(0x42464d);
    for(const [pos,size,power] of [[[-35,45,25],[45,65],2.4],[[30,20,-35],[30,55],1.8]]){
      const panel=new THREE.Mesh(new THREE.PlaneGeometry(...size),new THREE.MeshBasicMaterial({color:new THREE.Color(power,power*.98,power*.94),side:THREE.DoubleSide}));
      panel.position.set(...pos);panel.lookAt(0,0,0);studio.add(panel);
    }
    const pmrem=new THREE.PMREMGenerator(renderer),environment=pmrem.fromScene(studio,.12,.1,200);
    scene.environment=environment.texture;pmrem.dispose();studio.traverse(o=>{o.geometry?.dispose();o.material?.dispose();});
    materials.dipro.envMapIntensity=.35;materials.dipro_gold.envMapIntensity=.5;materials.boa.envMapIntensity=.3;
    const camera=new THREE.PerspectiveCamera(37,1,.1,500);scene.add(camera);
    const hemi=new THREE.HemisphereLight(0xeaf0ff,0x90877c,.65);scene.add(hemi);
    function directional(color,intensity,pos){const light=new THREE.DirectionalLight(color,intensity);light.position.set(...pos);scene.add(light);return light;}
    const keyLight=directional(0xfff1dd,3.0,[-30,45,35]);
    keyLight.castShadow=true;keyLight.shadow.mapSize.set(2048,2048);keyLight.shadow.bias=-.00003;keyLight.shadow.normalBias=.014;
    keyLight.shadow.camera.near=.5;keyLight.shadow.camera.far=180;scene.add(keyLight.target);
    const fillLight=directional(0xe4edff,.9,[35,18,10]);
    const rimLight=directional(0xfffaf1,2.2,[-10,28,-35]);
    const lowerLight=directional(0xeaf0ff,.25,[0,-30,12]);
    const cameraFill=new THREE.DirectionalLight(0xffffff,.25);cameraFill.position.set(0,0,1);
    cameraFill.target.position.set(0,0,-1);camera.add(cameraFill);camera.add(cameraFill.target);
    const lightPresets={estudio:[.65,3,.9,2.2,.25,.25,1.04],suave:[.9,2.2,1.35,1.6,.4,.4,1.04],interior:[1.1,1.9,1.3,1.4,1.8,1.1,1.06]};
    function setLighting(name){const values=lightPresets[name]||lightPresets.estudio;[hemi,keyLight,fillLight,rimLight,lowerLight,cameraFill].forEach((light,i)=>light.intensity=values[i]);renderer.toneMappingExposure=values[6];shell.dataset.lighting=name;requestRender();}
    const canvas=renderer.domElement;canvas.tabIndex=0;canvas.setAttribute('role','img');
    canvas.setAttribute('aria-label','Gorra en 3D. Arrastra para girar; rueda o pellizco para acercar. Usa las flechas, más, menos e Inicio con el teclado.');stage.append(canvas);
    let theta=.66,phi=.32,zoom=1,separation=0,fitPoints=[],animation=0,frame=0,contextLost=false;
    const focus=new THREE.Vector3(),direction=new THREE.Vector3(),right=new THREE.Vector3(),up=new THREE.Vector3(),worldUp=new THREE.Vector3(0,1,0);
    function render(){
      frame=0;if(contextLost)return;
      direction.set(Math.cos(phi)*Math.sin(theta),Math.sin(phi),Math.cos(phi)*Math.cos(theta));right.crossVectors(worldUp,direction).normalize();up.crossVectors(direction,right);
      const tangent=Math.tan(camera.fov*Math.PI/360);let fit=1;
      for(let i=0;i<fitPoints.length;i+=3){const x=fitPoints[i]-focus.x,y=fitPoints[i+1]-focus.y,z=fitPoints[i+2]-focus.z,depth=x*direction.x+y*direction.y+z*direction.z;
        fit=Math.max(fit,depth+Math.abs(x*up.x+y*up.y+z*up.z)/tangent,depth+Math.abs(x*right.x+y*right.y+z*right.z)/(tangent*camera.aspect));}
      camera.position.copy(direction).multiplyScalar(fit*1.12/zoom).add(focus);camera.lookAt(focus);renderer.render(scene,camera);
    }
    function requestRender(){if(!frame)frame=requestAnimationFrame(render);}
    function applyColor(key){const palette=textile.palettes[key];for(const [role,material]of Object.entries(materials)){if(palette[role]!==undefined)material.color.set(palette[role]);}requestRender();}
    function announce(){status.textContent=pieceInput.value==='todas'?(separation===0?'Gorra armada.':`Despiece al ${Math.round(separation*100)} por ciento.`):`${technical[pieceInput.value].name}. Vista individual y ficha técnica.`;}
    function updateParts(speak=true){
      const selected=pieceInput.value,bounds=new THREE.Box3();fitPoints=[];
      for(const mesh of meshes){mesh.position.copy(mesh.userData.delta).multiplyScalar(separation);mesh.visible=selected==='todas'||mesh.userData.piece===selected||(selected==='panel_delantero'&&mesh.userData.piece==='escudo');}
      group.updateMatrixWorld(true);
      for(const mesh of meshes){if(!mesh.visible)continue;bounds.expandByObject(mesh);const points=mesh.geometry.attributes.position.array,dx=mesh.position.x+group.position.x,dy=mesh.position.y+group.position.y,dz=mesh.position.z+group.position.z;for(let i=0;i<points.length;i+=3)fitPoints.push(points[i]+dx,points[i+1]+dy,points[i+2]+dz);}
      bounds.getCenter(focus);const percent=Math.round(separation*100);separationInput.value=percent;$('separation-value').textContent=`${percent} %`;
      const radius=Math.max(4,bounds.getSize(new THREE.Vector3()).length()*.55);
      keyLight.target.position.copy(focus);keyLight.position.copy(focus).add(new THREE.Vector3(-30,45,35));
      Object.assign(keyLight.shadow.camera,{left:-radius,right:radius,top:radius,bottom:-radius});keyLight.shadow.camera.updateProjectionMatrix();
      $('stage-state').textContent=selected!=='todas'?'COMPONENTE AISLADO':(separation===0?'GORRA ARMADA':`DESPIECE / ${percent} %`);
      for(const [id,on]of[['mode-assembled',separation===0],['mode-exploded',separation===1]]){$(id).classList.toggle('active',on);$(id).setAttribute('aria-pressed',String(on));}
      shell.dataset.separation=String(separation);shell.dataset.visibleGroups=String(new Set(meshes.filter(m=>m.visible).map(m=>m.userData.piece)).size);
      if(speak)announce();requestRender();
    }
    function cancelAnimation(){if(animation)cancelAnimationFrame(animation);animation=0;}
    function syncZoom(){$('zoom-value').textContent=`${Math.round(zoom*100)} %`;$('zoom-out').disabled=zoom<=.65;$('zoom-in').disabled=zoom>=2.5;}
    function setZoom(value){zoom=Math.max(.65,Math.min(2.5,value));syncZoom();requestRender();}
    function animateSeparation(target){cancelAnimation();zoom=1;syncZoom();const from=separation;if(reducedMotion.matches||from===target){separation=target;updateParts();return;}const start=performance.now();function tick(now){const progress=Math.min((now-start)/650,1),smooth=progress*progress*(3-2*progress);separation=from+(target-from)*smooth;updateParts(false);if(progress<1)animation=requestAnimationFrame(tick);else{animation=0;announce();}}animation=requestAnimationFrame(tick);}
    function setView(key){const value=key==='pieza'?(technical[pieceInput.value]?.view||presets.tres):presets[key];if(value)[theta,phi]=value;requestRender();}
    function selectEnginePiece(key){cancelAnimation();separation=0;zoom=1;syncZoom();viewInput.value=key==='todas'?'tres':'pieza';setView(viewInput.value);updateParts();}
    function reset(){cancelAnimation();separation=0;zoom=1;[theta,phi]=presets.tres;viewInput.value='tres';wireInput.checked=false;for(const mesh of meshes)mesh.material.wireframe=false;stage.classList.remove('interacted');syncZoom();updateParts();}
    const pointers=new Map();let oldDistance=0;
    canvas.addEventListener('pointerdown',event=>{if(event.button!==0)return;canvas.setPointerCapture(event.pointerId);pointers.set(event.pointerId,{x:event.clientX,y:event.clientY});oldDistance=0;stage.classList.add('interacted');});
    canvas.addEventListener('pointermove',event=>{if(!pointers.has(event.pointerId))return;const previous=pointers.get(event.pointerId);pointers.set(event.pointerId,{x:event.clientX,y:event.clientY});if(pointers.size===1){theta-=(event.clientX-previous.x)*.009;phi=Math.max(-1.45,Math.min(1.45,phi+(event.clientY-previous.y)*.009));}else{const[a,b]=[...pointers.values()],distance=Math.hypot(a.x-b.x,a.y-b.y);if(oldDistance)setZoom(zoom*distance/oldDistance);oldDistance=distance;}requestRender();});
    for(const name of['pointerup','pointercancel','lostpointercapture'])canvas.addEventListener(name,event=>{pointers.delete(event.pointerId);oldDistance=0;});
    canvas.addEventListener('wheel',event=>{event.preventDefault();const scale=event.deltaMode===1?16:event.deltaMode===2?stage.clientHeight:1;setZoom(zoom*Math.exp(-event.deltaY*scale*.001));},{passive:false});
    canvas.addEventListener('keydown',event=>{if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','+','=','-','Home'].includes(event.key))return;event.preventDefault();if(event.key==='ArrowLeft')theta-=.12;if(event.key==='ArrowRight')theta+=.12;if(event.key==='ArrowUp')phi=Math.min(1.45,phi+.12);if(event.key==='ArrowDown')phi=Math.max(-1.45,phi-.12);if(event.key==='+'||event.key==='=')setZoom(zoom+.15);if(event.key==='-')setZoom(zoom-.15);if(event.key==='Home'){selectPiece('todas');reset();}requestRender();});
    canvas.addEventListener('webglcontextlost',event=>{event.preventDefault();contextLost=true;cancelAnimation();loading.classList.remove('hidden');$('loading-text').textContent='Recuperando el visor 3D…';});
    canvas.addEventListener('webglcontextrestored',()=>{contextLost=false;loading.classList.add('hidden');requestRender();});
    function resize(){const width=Math.max(stage.clientWidth,1),height=Math.max(stage.clientHeight,1);renderer.setSize(width,height);camera.aspect=width/height;camera.updateProjectionMatrix();requestRender();}
    new ResizeObserver(resize).observe(stage);resize();
    engine={selectPiece:selectEnginePiece,selectColor:applyColor,setView,setWire:enabled=>{for(const m of meshes)m.material.wireframe=enabled;requestRender();},setLighting,animateSeparation,setSeparation:value=>{cancelAnimation();separation=value;updateParts(false);},changeZoom:value=>setZoom(zoom+value),reset,announce};
    renderControls.forEach(id=>$(id).disabled=false);applyColor(currentColor);setLighting('estudio');selectEnginePiece(pieceInput.value);syncZoom();loading.classList.add('hidden');shell.dataset.ready='true';shell.dataset.triangles=String(triangles);
    if(window.matchMedia('(pointer: coarse)').matches)$('viewer-hint').textContent='Arrastra para girar · Pellizca para acercar';
  }
  init().catch(error=>{console.warn('Visor 3D no disponible:',error);fallback=true;loading.classList.add('hidden');$('model-fallback').hidden=false;$('fallback-notice').hidden=false;$('viewer-hint').hidden=true;updateFallback();shell.dataset.ready='fallback';status.textContent='El 3D no está disponible. Puedes consultar las vistas de referencia y las fichas técnicas.';});
})();
