'use strict';

// adds the up and down buttons to the number boxes
document.querySelectorAll('input[type=number]').forEach(inp=>{
  const w=document.createElement('span');w.className='stepper';
  inp.parentNode.insertBefore(w,inp);w.appendChild(inp);
  const st=document.createElement('span');st.className='st';
  [['\u25B2','stepUp'],['\u25BC','stepDown']].forEach(([t,fn])=>{
    const b=document.createElement('button');b.type='button';b.tabIndex=-1;b.textContent=t;
    b.onclick=()=>{inp[fn]();inp.dispatchEvent(new Event('input',{bubbles:true}));inp.dispatchEvent(new Event('change',{bubbles:true}))};
    st.appendChild(b)});
  w.appendChild(st);
});

// reads the numbers from the config boxes
function readCfg(){
  return {
    seed:               +document.getElementById('cfg-seed').value,
    clusterScale:       +document.getElementById('cfg-clusterScale').value,
    elementOctaves:     Math.max(1, +document.getElementById('cfg-octaves').value|0),
    latticeResolution:  Math.max(5, Math.min(80, +document.getElementById('cfg-latticeRes').value|0)),
    densityThreshold:   +document.getElementById('cfg-densityThresh').value,
    HThreshold:         +document.getElementById('cfg-HThresh').value,
    HeThreshold:        +document.getElementById('cfg-HeThresh').value,
    maxStarsPerSystem:  Math.max(1, +document.getElementById('cfg-maxStars').value|0),
    minOrbitalDistance: +document.getElementById('cfg-minOrbit').value,
    maxOrbitalDistance: +document.getElementById('cfg-maxOrbit').value,
  };
}

// rotation speed changes straight away
document.getElementById('cfg-rotSpeed').addEventListener('input',e=>{
  rotSpeed=parseFloat(e.target.value)||0;
});

// open and close the config box
document.getElementById('cfgToggle').addEventListener('click',()=>{
  const body=document.getElementById('cfgBody'), open=body.classList.toggle('open');
  document.getElementById('cfgToggle').textContent=open?'⚙ Generator Config ▴':'⚙ Generator Config ▾';
});

// make a new galaxy with the new numbers
document.getElementById('regenBtn').addEventListener('click',()=>{
  document.getElementById('regenBtn').disabled=true;
  setTimeout(()=>document.getElementById('regenBtn').disabled=false,2000);
  // start
  runGeneration(readCfg());
});

// makes the galaxy and starts the viewer
function runGeneration(cfg){
  const ld=document.getElementById('loading'), det=document.getElementById('loading-detail');
  ld.style.display='flex';
  det.textContent='Seed: '+cfg.seed+' · Lattice: '+cfg.latticeResolution+'³';
  // wait a frame so the loading screen shows before the heavy bit
  requestAnimationFrame(()=>requestAnimationFrame(()=>{
    try {
      const data=generateUniverse(cfg);
      initViewer(data);
      document.getElementById('info').innerHTML='Click a system to explore.';
      document.getElementById('statsLine').textContent=
        data.systems.length+' systems · '+data.stars.length+' stars · '+data.planets.length+' planets';
    } catch(err) {
      document.getElementById('info').innerHTML='<span style="color:#ff7043">Generation error: '+err.message+'</span>';
      console.error(err);
    }
    ld.style.display='none';
  }));
}

runGeneration(readCfg());
