export const stages=['interpret request','pick neighbour cars','sample shape','rebuild mesh','place wheels','fit template','bake texture','validate','ready'];

export function generatorController({transport,render,preview=()=>{},saved=()=>{}}) {
  let state={status:'idle',events:stages.map(stage=>({stage,state:'waiting',elapsed_seconds:0,decisions:{}}))};
  let revision=0, shown=null;
  const display=()=>render({...state});
  async function action(fn) {
    try {await fn();}catch(error){state={...state,status:state.id?state.status:'failed',message:error.message};display();}
  }
  return {
    get state(){return state;},
    resume:snapshot=>action(async()=>{
      if(state.status!=='idle')return;state={...state,...snapshot};display();
      if(state.status==='ready' && state.preview){shown=state.id;await preview(state.preview);}
    }),
    start:options=>action(async()=>{
      const version=++revision;shown=null;state={status:'starting',events:stages.map(stage=>({stage,state:'waiting',elapsed_seconds:0,decisions:{}}))};display();
      const job=await transport('/api/generator/start',options);
      if(version===revision){state={...state,...job};display();}
    }),
    poll:()=>action(async()=>{
      if(!state.id || !['running','confirmation_required'].includes(state.status))return;
      const version=revision, result=await transport('/api/generator/'+state.id);
      if(version!==revision)return;
      state={...state,...result};display();
      if(state.status==='ready' && shown!==state.id){shown=state.id;await preview(state.preview);}
    }),
    cancel:()=>action(async()=>{
      ++revision;const result=await transport('/api/generator/'+state.id+'/cancel',{});state={...state,...result};display();
    }),
    confirm:accept=>action(async()=>{
      const result=await transport('/api/generator/'+state.id+'/confirm',{accept});state={...state,...result};display();
    }),
    save:name=>action(async()=>{
      const result=await transport('/api/generator/'+state.id+'/save',{name});state={...state,status:'saved'};display();await saved(result);
    })
  };
}

async function transport(path,body) {
  const response=await fetch(path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  let data;try{data=await response.json();}catch{throw Error('The generator needs the local library server.');}
  if(!response.ok)throw Error(data.message||'Generator request failed.');
  return data;
}

export function decisionsText(decisions) {
  const lines=[];
  for(const field of ['bodyStyle','era'])if(decisions[field]) {
    const reading=decisions[field];lines.push(`${field==='era'?'Era':'Body style'}: ${reading.value}, probability ${reading.probability.toFixed(2)}${reading.applied===false?' · set aside':''}`);
  }
  for(const reading of decisions.proportions||[])lines.push(`${reading.dimension}: level ${reading.score?.toFixed(2)??reading.value}, probability ${reading.probability.toFixed(2)}${reading.applied===false?' · set aside':''}`);
  for(const reading of decisions.unsupported_readings||[])lines.push(`${reading.part}: probability ${reading.probability.toFixed(2)}${reading.applied===false?' · set aside':''}`);
  for(const neighbour of decisions.neighbours||[])lines.push(`${neighbour.name}: distance ${neighbour.distance.toFixed(4)}`);
  if(decisions.unsupported)lines.push(`Unsupported: ${decisions.unsupported.join(', ')}. Generate without these parts?`);
  for(const [key,label] of Object.entries({novelty_score:'Novelty score',nearest_real_distance:'Nearest real car distance',template_fit_error:'Template fit error',body_vertices:'Body vertices',surface_vertices:'Rebuilt surface vertices',wheel_source:'Wheels copied from',texture:'Texture',reason:'Reason',honesty_label:'Model label'}))
    if(decisions[key]!==undefined)lines.push(`${label}: ${typeof decisions[key]==='number'?decisions[key].toFixed(4):decisions[key]}`);
  if(decisions.symmetry_error!==undefined)lines.push(`Symmetry error: ${decisions.symmetry_error.toFixed(4)}; wheel contact: ${decisions.wheel_contact_errors.map(v=>v.toFixed(4)).join(', ')}; static profile: ${decisions.static_profile?'pass':'fail'}`);
  return lines.join('\n');
}

export function mountGenerator(host,{preview,saved}) {
  host.innerHTML=`<details><summary>Generate a new car</summary><p>Learned shape · four real wheels · editable GLB</p>
    <label>Request <input data-control="request" maxlength="500" placeholder="a low, long 70s coupe"></label>
    <label>Body style <select data-control="bodyStyle"><option value="">Any</option>${['coupe','sedan','hatchback','convertible','wagon','SUV','pickup'].map(s=>`<option>${s}</option>`).join('')}</select></label>
    <label>Era <select data-control="era"><option value="">Any</option>${Array.from({length:10},(_,i)=>`<option>${1930+i*10}s</option>`).join('')}</select></label>
    <label>Method <select data-control="method"><option>shape space</option><option>network</option></select></label>
    <label>Novelty <input data-control="novelty" type="range" min="0" max="1" step="0.05" value="0.35"><span>close to real cars ↔ novel</span></label>
    <button data-control="generate" type="button">Generate</button> <button data-control="cancel" type="button" disabled>Cancel</button>
    <p data-control="status" role="status"></p><ol data-control="stages"></ol>
    <div data-control="confirm" hidden><button data-control="yes" type="button">Generate without unsupported parts</button><button data-control="no" type="button">Decline</button></div>
    <label>Name <input data-control="name" maxlength="120" placeholder="Use the generated name"></label>
    <button data-control="save" type="button" disabled>Save to dealership</button></details>`;
  const control=name=>host.querySelector(`[data-control="${name}"]`);
  let noveltyTouched=false;control('novelty').oninput=()=>{noveltyTouched=true;};
  transport('/api/generator/config').then(config=>{if(!noveltyTouched)control('novelty').value=config.novelty_default;}).catch(()=>{});
  const panel=generatorController({transport,preview,saved,render:state=>{
    control('status').textContent=state.message||state.status;
    control('generate').disabled=['starting','running','confirmation_required'].includes(state.status);
    control('cancel').disabled=!['running','confirmation_required'].includes(state.status);
    control('save').disabled=state.status!=='ready';
    control('confirm').hidden=state.status!=='confirmation_required';
    control('stages').replaceChildren(...state.events.map(event=>{
      const row=document.createElement('li');row.textContent=`${event.stage} · ${event.state} · ${event.elapsed_seconds.toFixed(1)}s`;
      const detail=document.createElement('div');detail.className='generator-decisions';detail.textContent=decisionsText(event.decisions);row.append(detail);return row;
    }));
  }});
  transport('/api/generator/current').then(snapshot=>panel.resume(snapshot)).catch(()=>{});
  control('generate').onclick=()=>{
    const constraints={};for(const field of ['bodyStyle','era'])if(control(field).value)constraints[field]={value:control(field).value,probability:1};
    return panel.start({method:control('method').value,seed:crypto.getRandomValues(new Uint32Array(1))[0],novelty:Number(control('novelty').value),constraints,request:control('request').value});
  };
  control('cancel').onclick=()=>panel.cancel();control('yes').onclick=()=>panel.confirm(true);control('no').onclick=()=>panel.confirm(false);
  control('save').onclick=()=>panel.save(control('name').value);
  let polling=false;
  const timer=setInterval(async()=>{if(polling)return;polling=true;try{await panel.poll();}finally{polling=false;}},500);
  addEventListener('pagehide',()=>clearInterval(timer),{once:true});
  return panel;
}
