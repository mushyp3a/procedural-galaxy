'use strict';
// viewer, draws everything with three.js
let _renderer=null, _animId=null, _camera=null;
let _exitSystemFn=null, _centerFn=null;
let rotSpeed=0.5;

// frees the memory of one object
function _disposeObj(obj) {
  if (obj.geometry) obj.geometry.dispose();
  if (obj.material) {
    const mats=Array.isArray(obj.material)?obj.material:[obj.material];
    mats.forEach(m=>{ if(m.map)m.map.dispose(); m.dispose(); });
  }
}
// frees a whole group of objects
function _disposeGroup(g) { if(g) g.traverse(_disposeObj); }

// removes the old viewer before making a new one
function destroyViewer() {
  if (_animId!=null){cancelAnimationFrame(_animId);_animId=null;}
  if (_renderer){
    _renderer.dispose();
    if(_renderer.domElement.parentNode) _renderer.domElement.parentNode.removeChild(_renderer.domElement);
    _renderer=null;
  }
  _camera=null; _exitSystemFn=null;
}

// sets up the scene, camera and all the click stuff
function initViewer(DATA) {
  destroyViewer();

  const AU=6.0, MOON=150.0, GAP=0.45;
  const starVR  = r=>Math.max(0.30,Math.min(0.80,0.35*r));
  const planetVR= r=>Math.max(0.12,Math.min(0.60,0.22*Math.sqrt(Math.max(0.01,r))));

  let mode='universe', currentSys=null;
  let systemPoints=null, systemOrder=[];
  const bodyMeshMap={};
  const _bodyTime={value:0.0};

  const systems=DATA.systems;
  const starsBySys={}, planetsBySys={}, moonsByPlanet={}, sysById={}, planetCount={};
  systems.forEach(s=>{sysById[s.id]=s; planetCount[s.id]=0;});
  DATA.stars.forEach(st=>{
    if(!starsBySys[st.system_id]) starsBySys[st.system_id]=[];
    starsBySys[st.system_id].push(st);
  });
  DATA.planets.forEach(p=>{
    if(!planetsBySys[p.system_id]) planetsBySys[p.system_id]=[];
    planetsBySys[p.system_id].push(p);
    planetCount[p.system_id]=(planetCount[p.system_id]||0)+1;
  });
  DATA.moons.forEach(m=>{
    if(!moonsByPlanet[m.planet_id]) moonsByPlanet[m.planet_id]=[];
    moonsByPlanet[m.planet_id].push(m);
  });

  const container=document.getElementById('container');
  const scene=new THREE.Scene();
  scene.background=new THREE.Color(0x020203);
  const camera=new THREE.PerspectiveCamera(60,innerWidth/innerHeight,0.1,500000);
  _camera=camera;

  const renderer=new THREE.WebGLRenderer({antialias:true});
  renderer.setPixelRatio(devicePixelRatio);
  renderer.setSize(innerWidth,innerHeight);
  container.appendChild(renderer.domElement);
  _renderer=renderer;

  const controls=new THREE.OrbitControls(camera,renderer.domElement);
  controls.enableDamping=true; controls.dampingFactor=0.08; controls.screenSpacePanning=true;

  const uHalf = systems.length>0
    ? systems.reduce((m,s)=>Math.max(m,s.x,s.y,s.z),0)*0.5
    : 500;
  const starDist = Math.max(6000, uHalf * 20);
  controls.minDistance = 0.5;
  controls.maxDistance = starDist * 0.7;

  const desiredTarget=new THREE.Vector3(uHalf,uHalf,uHalf);
  const desiredCam   =new THREE.Vector3(uHalf,uHalf*0.6,uHalf*3);
  camera.position.copy(desiredCam); controls.target.copy(desiredTarget);

  let flying=false;
  // starts the camera flying to a place
  function startFlight(camPos,target){desiredCam.copy(camPos);desiredTarget.copy(target);flying=true;controls.enabled=false;}
  // stops the flight if the user grabs the controls
  function cancelFlight(){if(flying){flying=false;controls.enabled=true;}}
  renderer.domElement.addEventListener('pointerdown',cancelFlight);
  renderer.domElement.addEventListener('wheel',cancelFlight,{passive:true});

  const clock=new THREE.Clock();

  // background stars, own seed so they dont change when regenerating
  (function(){
    const srng=makePRNG(DATA.seed+99);
    const cx=uHalf, cy=uHalf, cz=uHalf;
    const mkLayer=(n, rLo, rHi, col, sz, op)=>{
      const pos=new Float32Array(n*3);
      for(let i=0;i<n;i++){
        const r=starDist*(rLo+srng.next()*(rHi-rLo));
        const t=srng.next()*Math.PI*2, ph=Math.acos(2*srng.next()-1);
        pos[i*3]=cx+r*Math.sin(ph)*Math.cos(t); pos[i*3+1]=cy+r*Math.cos(ph); pos[i*3+2]=cz+r*Math.sin(ph)*Math.sin(t);
      }
      const g=new THREE.BufferGeometry(); g.setAttribute('position',new THREE.BufferAttribute(pos,3));
      scene.add(new THREE.Points(g,new THREE.PointsMaterial({color:col,size:sz,sizeAttenuation:false,transparent:true,opacity:op})));
    };
    mkLayer(3500, 0.75, 1.0, 0x8899bb, 1.0, 0.55);
    mkLayer( 700, 0.60, 0.8, 0xddeeff, 1.8, 0.85);
  })();

  // round soft dot for the stars
  function discTexture(){
    const c=document.createElement('canvas'); c.width=c.height=64;
    const x=c.getContext('2d'), g=x.createRadialGradient(32,32,0,32,32,32);
    g.addColorStop(0,'rgba(255,255,255,1)'); g.addColorStop(0.4,'rgba(255,255,255,0.6)'); g.addColorStop(1,'rgba(255,255,255,0)');
    x.fillStyle=g; x.fillRect(0,0,64,64); return new THREE.CanvasTexture(c);
  }
  const disc=discTexture();

  const tooltip=document.getElementById('tooltip');
  // blue for low metallicity, orange for high
  function metColor(m){return new THREE.Color(0x3a6bff).lerp(new THREE.Color(0xff9b3a),Math.max(0,Math.min(1,m)));}
  const SPEC_COL={O:'#9bb0ff',B:'#aabfff',A:'#cad7ff',F:'#f8f7ff',G:'#fff4e8',K:'#ffd2a1',M:'#ffcc6f'};
  const PL_COL={terrestrial:0x4caf50,ice_giant:0x64b5f6,gas_giant:0xff7043};

  // draws a dot for every system
  function buildSystems(list){
    systemOrder=list.map(s=>s.id);
    const pos=new Float32Array(list.length*3), col=new Float32Array(list.length*3);
    list.forEach((s,i)=>{
      pos[i*3]=s.x; pos[i*3+1]=s.y; pos[i*3+2]=s.z;
      const c=metColor(s.metallicity);
      col[i*3]=c.r; col[i*3+1]=c.g; col[i*3+2]=c.b;
    });
    const g=new THREE.BufferGeometry();
    g.setAttribute('position',new THREE.BufferAttribute(pos,3));
    g.setAttribute('color',new THREE.BufferAttribute(col,3));
    if(systemPoints){scene.remove(systemPoints);_disposeGroup(systemPoints);}
    const mat=new THREE.ShaderMaterial({
      uniforms:{uRef:{value:1500},uMin:{value:3},uMax:{value:16},uOpacity:{value:1}},
      vertexShader:[
        'attribute vec3 color;','varying vec3 vColor;','uniform float uRef,uMin,uMax;',
        'void main(){','  vColor=color;','  vec4 mv=modelViewMatrix*vec4(position,1.0);',
        '  float d=max(1.0,-mv.z);','  gl_PointSize=clamp(6.0*(uRef/d),uMin,uMax);',
        '  gl_Position=projectionMatrix*mv;','}'
      ].join('\n'),
      fragmentShader:[
        'varying vec3 vColor;','uniform float uOpacity;',
        'void main(){',
        '  vec2 c=gl_PointCoord-0.5;',
        '  float d=dot(c,c)*4.0;',
        '  if(d>1.0)discard;',
        '  float a=pow(1.0-d,1.5)*uOpacity;',
        '  vec3 col=vColor+vec3(0.25)*(1.0-d)*(1.0-d);',
        '  gl_FragColor=vec4(col,a);','}'
      ].join('\n'),
      transparent:true,depthWrite:false
    });
    systemPoints=new THREE.Points(g,mat);
    systemPoints.frustumCulled=false;
    scene.add(systemPoints);
  }

  let detailGroup=null;
  // removes the system we are looking at
  function clearDetail(){if(detailGroup){scene.remove(detailGroup);_disposeGroup(detailGroup);detailGroup=null;}}

  // random numbers for each planet so the orbits stay the same
  function rngFor(seed){let s=(seed>>>0)||1; return()=>{s^=s<<13;s^=s>>>17;s^=s<<5;return(s>>>0)/4294967296;};}

  // works out where a body is on its orbit
  function orbitPoint(a,phase,incl){
    return new THREE.Vector3(a*Math.cos(phase),a*Math.sin(phase)*Math.cos(incl),a*Math.sin(phase)*Math.sin(incl));
  }
  // draws the circle of an orbit
  function orbitRing(center,a,incl,n){
    const pts=[];
    for(let i=0;i<=n;i++){const th=i/n*Math.PI*2; pts.push(new THREE.Vector3(center.x+a*Math.cos(th),center.y+a*Math.sin(th)*Math.cos(incl),center.z+a*Math.sin(th)*Math.sin(incl)));}
    return new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts),new THREE.LineBasicMaterial({color:0x4466aa,transparent:true,opacity:0.3}));
  }
  // draws a line between two points
  function edge(a,b,color){return new THREE.Line(new THREE.BufferGeometry().setFromPoints([a,b]),new THREE.LineBasicMaterial({color,transparent:true,opacity:0.35}));}
  // glow around a star
  function glowSprite(color,scale){
    const m=new THREE.SpriteMaterial({map:disc,color,transparent:true,opacity:0.26,depthWrite:false,blending:THREE.AdditiveBlending});
    const sp=new THREE.Sprite(m); sp.scale.set(scale,scale,scale); return sp;
  }

  const _VERT=`
    varying vec3 vW,vN,vL;
    void main(){
      vec4 w=modelMatrix*vec4(position,1.0);
      vW=w.xyz; vN=normalize(mat3(modelMatrix)*normal); vL=normalize(position);
      gl_Position=projectionMatrix*viewMatrix*w;
    }`;
  const _NOISE=`
    float _h(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
    float _n(vec2 p){
      vec2 i=floor(p),f=fract(p); f=f*f*(3.0-2.0*f);
      return mix(mix(_h(i),_h(i+vec2(1,0)),f.x),
                 mix(_h(i+vec2(0,1)),_h(i+vec2(1,1)),f.x),f.y);}
    float fbm(vec2 p,int o){float v=0.,a=.5;
      for(int i=0;i<8;i++){if(i>=o)break;v+=a*_n(p);p*=2.;a*=.5;}return v;}
    float _n3(vec3 p){
      vec3 i=floor(p),f=fract(p); f=f*f*(3.0-2.0*f);
      float n=i.x+i.y*57.+i.z*113.;
      return mix(
        mix(mix(_h(vec2(n,0.)),_h(vec2(n+1.,0.)),f.x),
            mix(_h(vec2(n+57.,0.)),_h(vec2(n+58.,0.)),f.x),f.y),
        mix(mix(_h(vec2(n+113.,0.)),_h(vec2(n+114.,0.)),f.x),
            mix(_h(vec2(n+170.,0.)),_h(vec2(n+171.,0.)),f.x),f.y),f.z);}
    float fbm3(vec3 p,int o){float v=0.,a=.5;
      for(int i=0;i<8;i++){if(i>=o)break;v+=a*_n3(p);p*=2.;a*=.5;}return v;}`;

  // material for a star
  function starMat(hexCol){
    const c=new THREE.Color(hexCol);
    return new THREE.ShaderMaterial({
      uniforms:{uColor:{value:new THREE.Vector3(c.r,c.g,c.b)},
                uSeed:{value:Math.random()},uTime:_bodyTime},
      vertexShader:_VERT,
      fragmentShader:`
        ${_NOISE}
        varying vec3 vL;
        uniform vec3 uColor;
        uniform float uSeed,uTime;
        void main(){
          float ang=uTime*1.571+uSeed*6.283;
          float ca=cos(ang),sa=sin(ang);
          vec3 sp=vec3(vL.x*ca-vL.z*sa,vL.y,vL.x*sa+vL.z*ca)+uSeed*0.17;
          float surf=fbm3(sp*7.,4);
          float fine=fbm3(sp*18.+1.1,3);
          vec3 col=uColor*(0.80+0.20*surf)*(0.90+0.10*fine);
          gl_FragColor=vec4(col,1.0);
        }`
    });
  }

  // material for a planet
  function planetMat(type,hexCol,lightPos,seed){
    const c=new THREE.Color(hexCol);
    const lp=lightPos instanceof THREE.Vector3?lightPos:new THREE.Vector3();
    const s=(seed%99991)/99991.0;
    const frag={
      terrestrial:`
        ${_NOISE}
        varying vec3 vW,vN,vL;
        uniform vec3 uColor,uLight; uniform float uSeed,uTime;
        void main(){
          vec3 L=normalize(uLight-vW);
          float diff=max(0.,dot(vN,L));
          float light=0.45+0.55*diff;
          float ang=uTime*0.942+uSeed*6.283;
          float ca=cos(ang),sa=sin(ang);
          vec3 sp=vec3(vL.x*ca-vL.z*sa,vL.y,vL.x*sa+vL.z*ca)+uSeed*0.17;
          float land=fbm3(sp*3.2,4)*1.7-(0.60+uSeed*0.50);
          float detail=fbm3(sp*8.5+1.3,3);
          vec3 ocean=mix(vec3(0.04,0.14,0.56),vec3(0.10,0.38,0.54),uSeed*0.6);
          vec3 sand=mix(vec3(0.30,0.21,0.09),vec3(0.52,0.38,0.18),uSeed);
          vec3 vege=mix(vec3(0.09,0.38,0.07),vec3(0.22,0.44,0.10),uSeed);
          vec3 landC=mix(sand,vege,clamp(detail*(1.2-uSeed*0.9),0.,1.));
          vec3 col=mix(ocean,landC,smoothstep(-0.06,0.14,land));
          col=mix(col,uColor*0.4,0.10);
          gl_FragColor=vec4(col*light,1.0);
        }`,
      gas_giant:`
        ${_NOISE}
        varying vec3 vW,vN,vL;
        uniform vec3 uColor,uLight; uniform float uSeed,uTime;
        void main(){
          vec3 L=normalize(uLight-vW);
          float diff=max(0.,dot(vN,L));
          float light=0.45+0.55*diff;
          float ang=uTime*0.753+uSeed*6.283;
          float ca=cos(ang),sa=sin(ang);
          vec3 sp=vec3(vL.x*ca-vL.z*sa,vL.y,vL.x*sa+vL.z*ca);
          float bandFreq=18.+uSeed*9.;
          float warpStr=0.30+uSeed*0.25;
          float warp=fbm3(sp*4.,4)*warpStr;
          float band=sin((vL.y+warp)*bandFreq+fbm3(sp*2.,3)*1.5)*0.5+0.5;
          float detail=fbm3(sp*13.+uSeed,3);
          vec3 c1=uColor*0.72, c2=uColor*1.22, c3=vec3(0.94,0.90,0.80);
          vec3 col=mix(c1,c2,smoothstep(0.28,0.72,band));
          col=mix(col,c3,smoothstep(0.72,1.,band)*(0.4+uSeed*0.3));
          col*=0.84+0.16*detail;
          gl_FragColor=vec4(col*light,1.0);
        }`,
      ice_giant:`
        ${_NOISE}
        varying vec3 vW,vN,vL;
        uniform vec3 uColor,uLight; uniform float uSeed,uTime;
        void main(){
          vec3 L=normalize(uLight-vW);
          float diff=max(0.,dot(vN,L));
          float light=0.45+0.55*diff;
          float ang=uTime*0.628+uSeed*6.283;
          float ca=cos(ang),sa=sin(ang);
          vec3 sp=vec3(vL.x*ca-vL.z*sa,vL.y,vL.x*sa+vL.z*ca);
          float warpStr=0.40+uSeed*0.25;
          float warp=fbm3(sp*3.,3)*warpStr;
          float swirl=fbm3(sp*5.5+uSeed,4);
          float bandFreq=11.+uSeed*5.;
          float band=sin((vL.y+warp*0.5)*bandFreq)*0.5+0.5;
          vec3 c3=vec3(0.80+uSeed*0.12,0.89,0.97);
          vec3 c1=uColor*0.62, c2=uColor*1.28;
          vec3 col=mix(c1,c2,swirl);
          col=mix(col,c3,band*0.22);
          col*=0.87+0.13*fbm3(sp*19.,3);
          gl_FragColor=vec4(col*light,1.0);
        }`
    };
    return new THREE.ShaderMaterial({
      uniforms:{uColor:{value:new THREE.Vector3(c.r,c.g,c.b)},
                uLight:{value:lp.clone()},uSeed:{value:s},uTime:_bodyTime},
      vertexShader:_VERT,
      fragmentShader:frag[type]||frag.terrestrial
    });
  }

  // material for a moon
  function moonMat(isIcy,lightPos,seed){
    const lp=lightPos instanceof THREE.Vector3?lightPos:new THREE.Vector3();
    const s=(seed%99991)/99991.0;
    return new THREE.ShaderMaterial({
      uniforms:{uLight:{value:lp.clone()},uSeed:{value:s},
                uIcy:{value:isIcy?1.0:0.0},uTime:_bodyTime},
      vertexShader:_VERT,
      fragmentShader:`
        ${_NOISE}
        varying vec3 vW,vN,vL;
        uniform vec3 uLight; uniform float uSeed,uIcy,uTime;
        void main(){
          vec3 L=normalize(uLight-vW);
          float diff=max(0.,dot(vN,L));
          float light=0.40+0.60*diff;
          float ang=uTime*0.08+uSeed*6.283;
          float ca=cos(ang),sa=sin(ang);
          vec3 sp=vec3(vL.x*ca-vL.z*sa,vL.y,vL.x*sa+vL.z*ca)+uSeed*0.17;
          float surf=fbm3(sp*9.,4);
          float fine=fbm3(sp*22.+1.3,3);
          vec3 rocky=vec3(0.30,0.26,0.22)*(0.7+0.3*surf)*(0.88+0.12*fine);
          vec3 icy=vec3(0.70,0.78,0.88)*(0.8+0.2*surf)*(0.90+0.10*fine);
          vec3 col=mix(rocky,icy,uIcy);
          gl_FragColor=vec4(col*light,1.0);
        }`
    });
  }

  // material for the clouds on a planet
  function cloudMat(type,lightPos,seed){
    const lp=lightPos instanceof THREE.Vector3?lightPos:new THREE.Vector3();
    const s=(seed%99991)/99991.0;
    // cloud colours for each planet type
    const cfg={
      terrestrial:{col:[0.95,0.96,0.98],thresh:0.57,alpha:0.58},
      gas_giant:  {col:[0.91,0.88,0.78],thresh:0.54,alpha:0.46},
      ice_giant:  {col:[0.82,0.88,0.94],thresh:0.64,alpha:0.30},
    }[type]||{col:[0.95,0.96,0.98],thresh:0.57,alpha:0.58};
    const [cr,cg,cb]=cfg.col;
    return new THREE.ShaderMaterial({
      uniforms:{uLight:{value:lp.clone()},uSeed:{value:s},uTime:_bodyTime,
                uCol:{value:new THREE.Vector3(cr,cg,cb)},
                uThresh:{value:cfg.thresh},uMaxAlpha:{value:cfg.alpha}},
      vertexShader:_VERT,
      fragmentShader:`
        ${_NOISE}
        varying vec3 vW,vN,vL;
        uniform vec3 uLight,uCol; uniform float uSeed,uTime,uThresh,uMaxAlpha;
        void main(){
          vec3 L=normalize(uLight-vW);
          float diff=max(0.,dot(vN,L));
          float light=0.50+0.50*diff;
          float ang=uTime*1.15+uSeed*6.283;
          float ca=cos(ang),sa=sin(ang);
          vec3 sp=vec3(vL.x*ca-vL.z*sa,vL.y,vL.x*sa+vL.z*ca)+uSeed*0.23;
          float c1=fbm3(sp*3.5,4);
          float c2=fbm3(sp*7.+0.8,3);
          float alpha=smoothstep(uThresh,uThresh+0.16,c1+c2*0.3)*uMaxAlpha*light;
          gl_FragColor=vec4(uCol,alpha);
        }`,
      transparent:true,
      depthWrite:false
    });
  }

  // zooms into a system and draws its stars, planets and moons
  function enterSystem(sysId){
    const sys=sysById[sysId]; if(!sys)return;
    mode='system'; currentSys=sysId; clearDetail();
    Object.keys(bodyMeshMap).forEach(k=>delete bodyMeshMap[k]);
    const center=new THREE.Vector3(sys.x,sys.y,sys.z);
    detailGroup=new THREE.Group(); scene.add(detailGroup);

    const stars=starsBySys[sysId]||[];
    const starPos={}, starRadius={};
    let maxStarR=0.3;
    stars.forEach(st=>{ maxStarR=Math.max(maxStarR,starVR(st.radius)); });
    const starGlow=1.25*maxStarR;
    // space the stars out around a ring so they dont overlap
    const starGap = 2*starGlow + GAP;
    const sep = stars.length > 1
      ? starGap / (2 * Math.sin(Math.PI / stars.length))
      : 0;

    stars.forEach((st,i)=>{
      const ang=stars.length>1 ? i/stars.length*Math.PI*2 : 0;
      const pos=center.clone().add(new THREE.Vector3(Math.cos(ang)*sep,0,Math.sin(ang)*sep));
      starPos[st.id]=pos;
      const r=starVR(st.radius); starRadius[st.id]=r;
      const col=SPEC_COL[st.spectral_type]||'#ffffff';
      const mesh=new THREE.Mesh(new THREE.SphereGeometry(r,32,32),starMat(col));
      mesh.position.copy(pos); mesh.userData={type:'star',data:st,radius:r,bodyKey:'star-'+st.id};
      bodyMeshMap['star-'+st.id]=mesh;
      detailGroup.add(mesh);
      const gl=glowSprite(new THREE.Color(col),r*3.8); gl.position.copy(pos); detailGroup.add(gl);
    });

    const pl=(planetsBySys[sysId]||[]).slice().sort((a,b)=>a.orbital_distance-b.orbital_distance);
    const moonPad={};
    pl.forEach(p=>{
      moonPad[p.id]=(moonsByPlanet[p.id]||[]).reduce((m,mn)=>Math.max(m,mn.orbital_distance*MOON),0);
    });
    const orbits=[]; let prevA=null, prevR=0;
    pl.forEach(p=>{
      const rp=planetVR(p.radius), sr=starRadius[p.star_id]||maxStarR, mp=moonPad[p.id]||0;
      let a=Math.max(p.orbital_distance*AU, 1.25*sr+rp+mp+GAP);
      if(stars.length>1) a=Math.max(a, sep+sr+rp+mp+GAP);
      if(prevA!==null) a=Math.max(a, prevA+prevR+rp+mp+GAP);
      orbits.push(a); prevA=a; prevR=rp+mp;
    });

    let maxOrbit=1;
    // spreads the planets out evenly around the star
    const goldenAngle = Math.PI * (3 - Math.sqrt(5));
    const n = pl.length;

    const placed = stars.map(st => ({pos: starPos[st.id].clone(), r: starRadius[st.id]}));

    pl.forEach((p,i)=>{
      const a=orbits[i];
      const starC = starPos[p.star_id] || center;
      const rand=rngFor((p.id*2654435761)>>>0); // keep for moons
      const r=planetVR(p.radius);

      const cosPhase = n > 1 ? 1 - 2*(i+0.5)/n : 0;
      const basePhase = Math.acos(Math.max(-1, Math.min(1, cosPhase)));
      let incl = i * goldenAngle;

      const rEff = r + (moonPad[p.id]||0);
      let pos = center.clone().add(orbitPoint(a, basePhase, incl));
      for (let k = 1; k < 32; k++) {
        if (placed.every(o => pos.distanceTo(o.pos) >= o.r + rEff + GAP)) break;
        incl = i * goldenAngle + k * goldenAngle;
        pos = center.clone().add(orbitPoint(a, basePhase, incl));
      }
      placed.push({pos, r: rEff});

      maxOrbit=Math.max(maxOrbit,a);
      const mesh=new THREE.Mesh(new THREE.SphereGeometry(r,24,24),planetMat(p.planet_type,PL_COL[p.planet_type]||0xffffff,starPos[p.star_id]||center,p.id));
      mesh.position.copy(pos); mesh.userData={type:'planet',data:p,radius:r,bodyKey:'planet-'+p.id};
      bodyMeshMap['planet-'+p.id]=mesh;
      detailGroup.add(mesh);
      const cm=new THREE.Mesh(new THREE.SphereGeometry(r*1.05,24,24),cloudMat(p.planet_type,starPos[p.star_id]||center,p.id));
      cm.position.copy(pos); detailGroup.add(cm);
      detailGroup.add(orbitRing(center,a,incl,80));
      detailGroup.add(edge(starC,pos,0x335588));
      (moonsByPlanet[p.id]||[]).forEach(mn=>{
        const mr=Math.max(0.001,mn.orbital_distance)*MOON;
        const ph2=rand()*Math.PI*2, ic2=rand()*Math.PI;
        const mp=pos.clone().add(orbitPoint(mr,ph2,ic2));
        const mr2=Math.max(0.06,planetVR(mn.radius)*0.6);
        const mmesh=new THREE.Mesh(new THREE.SphereGeometry(mr2,16,16),moonMat(mn.moon_type==='icy',starPos[p.star_id]||center,mn.id));
        mmesh.position.copy(mp); mmesh.userData={type:'moon',data:mn,radius:mr2,bodyKey:'moon-'+mn.id};
        bodyMeshMap['moon-'+mn.id]=mmesh;
        detailGroup.add(mmesh);
        detailGroup.add(orbitRing(pos,mr,ic2,40));
        detailGroup.add(edge(pos,mp,0x555555));
      });
    });

    const dist=Math.max(60,(maxOrbit+1.25*maxStarR)*1.5);
    const sysCamPos = center.clone().add(new THREE.Vector3(0,dist*0.3,dist));
    _centerFn = () => startFlight(sysCamPos.clone(), center.clone());
    startFlight(sysCamPos, center);
    controls.minDistance = maxStarR * 2;
    if(systemPoints){
      const K=120;
      systemPoints.scale.setScalar(K);
      systemPoints.position.copy(center.clone().multiplyScalar(1-K));
      systemPoints.material.uniforms.uOpacity.value=0;
    }
    showSystemInfo(sys);
    document.getElementById('backBtn').style.display='inline-block';
    document.getElementById('crumb').textContent='System #'+sysId;
  }

  // goes back out to the whole galaxy
  function exitSystem(){
    controls.minDistance=0.5;
    mode='universe'; currentSys=null; clearDetail();
    if(systemPoints){
      systemPoints.scale.setScalar(1); systemPoints.position.set(0,0,0);
      systemPoints.material.uniforms.uOpacity.value=1;
    }
    startFlight(new THREE.Vector3(uHalf,uHalf*0.6,uHalf*3),new THREE.Vector3(uHalf,uHalf,uHalf));
    _centerFn = () => startFlight(new THREE.Vector3(uHalf,uHalf*0.6,uHalf*3), new THREE.Vector3(uHalf,uHalf,uHalf));
    document.getElementById('info').innerHTML='Click a system to explore.';
    document.getElementById('backBtn').style.display='none';
    document.getElementById('crumb').textContent='Universe';
  }
  _exitSystemFn=exitSystem;
  _centerFn = () => startFlight(new THREE.Vector3(uHalf,uHalf*0.6,uHalf*3), new THREE.Vector3(uHalf,uHalf,uHalf));

  const ray=new THREE.Raycaster();
  const mouse=new THREE.Vector2();
  let downXY=null;

  // finds the system closest to the mouse
  function nearestSystem(mx,my){
    const v=new THREE.Vector3(); let best=null, bestD=18;
    for(const id of systemOrder){
      const s=sysById[id]; v.set(s.x,s.y,s.z).project(camera);
      if(v.z>1)continue;
      const sx=(v.x*0.5+0.5)*innerWidth, sy=(-v.y*0.5+0.5)*innerHeight;
      const d=Math.hypot(sx-mx,sy-my);
      if(d<bestD){bestD=d;best=id;}
    }
    return best;
  }

  renderer.domElement.addEventListener('pointerdown',e=>{downXY=[e.clientX,e.clientY];});
  // click on a system to go into it
  renderer.domElement.addEventListener('pointerup',e=>{
    if(!downXY)return;
    const dx=e.clientX-downXY[0], dy=e.clientY-downXY[1]; downXY=null;
    if(dx*dx+dy*dy>25)return;
    if(mode==='universe'&&systemPoints){
      const id=nearestSystem(e.clientX,e.clientY); if(id!=null)enterSystem(id);
    } else if(mode==='system'&&detailGroup){
      mouse.x=(e.clientX/innerWidth)*2-1; mouse.y=-(e.clientY/innerHeight)*2+1;
      ray.setFromCamera(mouse,camera);
      const hits=ray.intersectObjects(detailGroup.children,false).filter(h=>h.object.userData&&h.object.userData.type);
      if(hits.length){const o=hits[0].object; selectBodyByKey(o.userData.bodyKey);}
    }
  });

  // show the name when hovering
  renderer.domElement.addEventListener('pointermove',e=>{
    if(flying||mode!=='universe'){tooltip.style.display='none';return;}
    const id=nearestSystem(e.clientX,e.clientY);
    if(id==null){tooltip.style.display='none';return;}
    const s=sysById[id];
    tooltip.style.display='block';
    tooltip.style.left=(e.clientX+14)+'px'; tooltip.style.top=(e.clientY+14)+'px';
    tooltip.innerHTML='System #'+id+'<br>met '+s.metallicity.toFixed(2)+'<br>planets '+(planetCount[id]||0);
  });

  // moves the camera to look at a body
  function focusBody(o){
    const p=o.position.clone(), r=o.userData.radius||1;
    const t=o.userData.type;
    const minMult = t==='star' ? 3.0 : t==='moon' ? 3.5 : 2.5;
    controls.minDistance=r*minMult;
    const dir=new THREE.Vector3().subVectors(camera.position,p).normalize();
    startFlight(p.clone().add(dir.multiplyScalar(Math.max(8,r*8+6))),p);
  }

  // one row of the info table
  function row(k,v){return'<tr><td class="k">'+k+'</td><td>'+v+'</td></tr>';}

  // fills the info panel for a system
  function showSystemInfo(s){
    const stars=(starsBySys[s.id]||[]).slice().sort((a,b)=>a.mass-b.mass);
    const planets=(planetsBySys[s.id]||[]).slice().sort((a,b)=>a.orbital_distance-b.orbital_distance);
    let h='<h3>System #'+s.id+'</h3><table>'+
      row('metallicity',s.metallicity.toFixed(3))+row('density',s.density.toFixed(3))+
      row('H',s.H.toFixed(3))+row('He',s.He.toFixed(3))+row('C',s.C.toFixed(3))+row('O',s.O.toFixed(3))+
      row('stars',stars.length)+row('planets',planets.length)+
      '</table><hr>';
    stars.forEach(st=>{
      const col=SPEC_COL[st.spectral_type]||'#ffffff';
      h+=`<div class="body-item" data-key="star-${st.id}"><span class="sw" style="background:${col}"></span><span>${st.spectral_type} star — ${st.mass.toFixed(2)} M&#9737;</span></div>`;
      planets.filter(p=>p.star_id===st.id).forEach(p=>{
        const col=PL_COL[p.planet_type]||'#ffffff';
        h+=`<div class="body-item" data-key="planet-${p.id}" style="padding-left:14px"><span class="sw" style="background:${col}"></span><span>Planet ${p.orbital_order} — ${p.planet_type} — ${p.orbital_distance.toFixed(2)} AU</span></div>`;
        (moonsByPlanet[p.id]||[]).forEach(mn=>{
          h+=`<div class="body-item" data-key="moon-${mn.id}" style="padding-left:28px"><span class="sw" style="background:#aaaaaa"></span><span>${mn.moon_type} moon — ${mn.orbital_distance.toFixed(4)} AU</span></div>`;
        });
      });
    });
    h+='<hr><div id="bodyDetail" style="color:var(--mute)">click a body above</div>';
    document.getElementById('info').innerHTML=h;
    document.querySelectorAll('#info .body-item').forEach(el=>{
      el.onclick=()=>selectBodyByKey(el.dataset.key);
    });
  }

  // selects a body from the list
  function selectBodyByKey(key){
    document.querySelectorAll('#info .body-item').forEach(el=>el.classList.toggle('sel',el.dataset.key===key));
    const mesh=bodyMeshMap[key];
    if(mesh){focusBody(mesh); showBodyInfo(mesh.userData.type,mesh.userData.data);}
  }

  // fills the info panel for a star, planet or moon
  function showBodyInfo(type,d){
    let h='<h3>'+(type==='star'?'Star #'+d.id:type==='planet'?'Planet (order '+d.orbital_order+')':'Moon #'+d.id)+'</h3><table>';
    if(type==='star')
      h+=row('system',d.system_id)+row('star #',d.star_number)+row('spectral',d.spectral_type)+
         row('mass',d.mass.toFixed(3)+' M&#9737;')+row('radius',d.radius.toFixed(3)+' R&#9737;')+
         row('temp',d.temperature.toFixed(0)+' K')+row('luminosity',d.luminosity.toFixed(3)+' L&#9737;')+
         row('metallicity',d.metallicity.toFixed(3));
    else if(type==='planet')
      h+=row('system',d.system_id)+row('star',d.star_id)+row('order',d.orbital_order)+
         row('type',d.planet_type)+row('mass',d.mass.toFixed(2)+' M&#8853;')+
         row('radius',d.radius.toFixed(2)+' R&#8853;')+row('temp',d.temperature.toFixed(0)+' K')+
         row('albedo',d.albedo.toFixed(2))+row('orbit',d.orbital_distance.toFixed(3)+' AU');
    else
      h+=row('planet',d.planet_id)+row('order',d.orbital_order)+
         row('mass',d.mass.toFixed(3))+row('radius',d.radius.toFixed(3))+
         row('orbit',d.orbital_distance.toFixed(4)+' AU');
    h+='</table>';
    const detail=document.getElementById('bodyDetail');
    if(detail) detail.innerHTML=h;
    else document.getElementById('info').innerHTML=h;
  }

  const SPECS=['O','B','A','F','G','K','M'];
  const specBox=document.getElementById('specBoxes');
  specBox.innerHTML='';
  SPECS.forEach(sp=>{
    const l=document.createElement('label'), cb=document.createElement('input');
    cb.type='checkbox'; cb.value=sp; cb.checked=true;
    l.appendChild(cb); l.appendChild(document.createTextNode(sp)); specBox.appendChild(l);
  });

  // hides the systems that dont match the search boxes
  function applyFilter(){
    const metMin=+document.getElementById('metMin').value;
    const metMax=+document.getElementById('metMax').value;
    const minP=+document.getElementById('minP').value;
    const specs=Array.from(document.querySelectorAll('#specBoxes input:checked')).map(c=>c.value);
    const visible=systems.filter(s=>{
      if(s.metallicity<metMin||s.metallicity>metMax)return false;
      if((planetCount[s.id]||0)<minP)return false;
      if(specs.length<SPECS.length){
        const sp=(starsBySys[s.id]||[]).map(st=>st.spectral_type);
        if(!sp.some(x=>specs.includes(x)))return false;
      }
      return true;
    });
    buildSystems(visible);
    document.getElementById('matchCount').textContent=visible.length+' shown';
    const ml=document.getElementById('matchList'); ml.innerHTML='';
    visible.slice(0,200).forEach(s=>{
      const d=document.createElement('div');
      d.textContent='#'+s.id+' (met '+s.metallicity.toFixed(2)+', '+(planetCount[s.id]||0)+' pl)';
      d.onclick=()=>enterSystem(s.id); ml.appendChild(d);
    });
  }

  document.getElementById('applyF').onclick=applyFilter;
  document.getElementById('backBtn').onclick=exitSystem;
  document.getElementById('goId').onclick=()=>{
    const v=parseInt(document.getElementById('sysId').value,10);
    if(sysById[v])enterSystem(v);
  };

  // get the time since last frame so flying stays smooth
  function animate(){
    _animId=requestAnimationFrame(animate);
    const dt=Math.min(clock.getDelta(),0.05);
    _bodyTime.value+=dt*rotSpeed;
    if(flying){
      controls.target.lerp(desiredTarget,0.18);
      camera.position.lerp(desiredCam,0.18);
      camera.lookAt(controls.target);
      if(camera.position.distanceTo(desiredCam)<0.06&&controls.target.distanceTo(desiredTarget)<0.06){
        flying=false;
        controls.target.copy(desiredTarget);
        camera.position.copy(desiredCam);
        controls.enabled=true;
      }
    } else {
      controls.update();
    }
    renderer.render(scene,camera);
  }

  applyFilter();
  animate();
}

(function(){
  // true if the user is typing in a box
  function typing(){return document.activeElement&&/INPUT|TEXTAREA/.test(document.activeElement.tagName);}
  // keyboard, space centers and esc goes back
  window.addEventListener('keydown',e=>{
    if(typing())return;
    if(e.code==='Space'){ e.preventDefault(); if(_centerFn)_centerFn(); return; }
    if(e.key==='Escape'&&_exitSystemFn){ _exitSystemFn(); return; }
  });
  // keep the size right when the window changes
  window.addEventListener('resize',()=>{
    if(_camera&&_renderer){
      _camera.aspect=innerWidth/innerHeight;
      _camera.updateProjectionMatrix();
      _renderer.setSize(innerWidth,innerHeight);
    }
  });
})();
