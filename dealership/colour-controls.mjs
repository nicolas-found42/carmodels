import {createPaintSession} from './game-paint.mjs';

export function createColourControls({root=document,scope='dealership',onChange=()=>{},storage,presetSelect}={}) {
  const container=root.querySelector('#game-paint-controls'),doc=container.ownerDocument??root;
  const make=(tag,text)=>{const node=doc.createElement(tag);if(text!==undefined)node.textContent=text;return node;};
  const channel=make('select');channel.setAttribute('aria-label','Paint channel');
  const search=make('input');search.type='search';search.placeholder='Find a game colour';search.setAttribute('aria-label','Find a game colour');
  const choices=make('div');choices.className='paint-swatches';choices.setAttribute('role','group');choices.setAttribute('aria-label','Recovered game colours');
  const reset=make('button','Reset colour');reset.type='button';
  const more=make('button','Show more colours');more.type='button';
  const status=make('p');status.setAttribute('role','status');status.setAttribute('aria-live','polite');
  const limitDetails=make('details');limitDetails.className='paint-limits';
  const limits=make('p');limitDetails.append(make('summary','Paint recovery limits'),limits);
  container.replaceChildren(channel,search,reset,choices,more,status,limitDetails);
  let enabled=false,session=null,key=null,shown=60,storageFailed=false,paletteError='';
  function localStore(){return storage??globalThis.localStorage;}
  function save(remove=false) {
    try {if(remove)localStore()?.removeItem(key);else localStore()?.setItem(key,JSON.stringify(session.state));}
    catch {storageFailed=true;}
  }
  function changed(remove=false) {save(remove);onChange(session);render();}
  function render() {
    const mode=channel.value,paintChannel=session?.channels.find(value=>value.id===mode);
    channel.disabled=!enabled;search.disabled=!enabled;reset.disabled=!enabled;
    choices.replaceChildren();more.hidden=true;
    if(!enabled || !session) {status.textContent='Load a 3D model to choose recovered game colours.';return;}
    const query=search.value.trim().toLowerCase();
    const entries=(paintChannel?session.colors:session.presets).filter(value=>
      [value.name,value.source??''].join(' ').toLowerCase().includes(query));
    const selection=paintChannel?session.state.channels[mode]?.color:session.state.preset;
    for(const entry of entries.slice(0,shown)) {
      const button=make('button');button.type='button';button.className='paint-choice';
      button.setAttribute('aria-pressed',String(selection===(paintChannel?entry.key:entry.index)));
      const swatch=make('span');swatch.className='paint-chip';swatch.setAttribute('aria-hidden','true');
      if(entry.rgb || entry.swatch) {
        const sRGB=value=>value<=.0031308?12.92*value:1.055*value**(1/2.4)-.055;
        swatch.style.backgroundColor=`rgb(${(entry.rgb??entry.swatch).map(value=>Math.round((entry.rgb?sRGB(value):value)*255)).join(',')})`;
        if(entry.swatch)button.title='Native menu swatch; original colour-space response is unresolved.';
      }else {swatch.className+=' paint-chip-unavailable';button.title='Native texture preset; an independent colour swatch has not been recovered.';}
      button.append(swatch);
      button.append(make('span',entry.name));
      if(entry.source) {
        button.title=entry.source;
        if(entries.some(other=>other!==entry&&other.name===entry.name))button.append(make('small',entry.source.replace(/ \(sha256 [a-f0-9]+\)$/,'')));
      }
      button.addEventListener('click',()=>{
        if(!enabled)return;
        if(paintChannel)session.setChannel(mode,entry.key);else {session.setPreset(entry.index);if(presetSelect)presetSelect.value=String(entry.index);}
        changed();
      });choices.append(button);
    }
    if(paintChannel) {
      const original=make('button','Use preset colour');original.type='button';original.addEventListener('click',()=>{if(enabled){session.setChannel(mode,null);changed();}});choices.prepend(original);
      if(paintChannel.finishes.length) {
        const finish=make('select');finish.setAttribute('aria-label',`${paintChannel.name} finish`);
        const base=make('option','Preset finish');base.value='';finish.append(base);
        for(const value of paintChannel.finishes){const option=make('option',value.name);option.value=value.id;finish.append(option);}
        finish.value=session.state.channels[mode]?.finish??'';
        finish.addEventListener('change',()=>{if(enabled){session.setFinish(mode,finish.value||null);changed();}});choices.append(finish);
      }
    }
    more.hidden=entries.length<=shown;
    status.textContent=`${Math.min(entries.length,shown)} of ${entries.length} ${paintChannel?'game colours':'native presets'}.`+
      (!session.channels.length?' Transferable paint channels are unavailable until recovered.':'')+
      (paletteError?` ${paletteError}`:'')+(storageFailed?' Browser storage is unavailable; this selection will not be remembered.':'');
  }
  channel.addEventListener('change',()=>{shown=60;render();});
  search.addEventListener('input',()=>{shown=60;render();});
  more.addEventListener('click',()=>{shown+=60;render();});
  reset.addEventListener('click',()=>{if(enabled&&session){session.reset();if(presetSelect)presetSelect.value='';changed(true);}});
  const controls={
    get session(){return session;},
    bind({model,game,carId,colors=[],error=''}) {
      session=createPaintSession(model,{game,colors});key=`carmodels:paint:v1:${scope}:${game}:${carId}`;
      storageFailed=false;paletteError=error;shown=60;search.value='';
      try {const saved=localStore()?.getItem(key);if(saved)session.restore(JSON.parse(saved));}catch {storageFailed=true;}
      channel.replaceChildren();
      const preset=make('option','Original presets · this car');preset.value='';channel.append(preset);
      for(const value of session.channels){const option=make('option',`${value.name} · game palette`);option.value=value.id;channel.append(option);}
      channel.value=session.presets.length?'':session.channels[0]?.id??'';if(presetSelect)presetSelect.value=session.state.preset===null?'':String(session.state.preset);
      limits.textContent=['Native colours under viewer lighting; original shader appearance may differ.',...session.limits].join(' ');
      onChange(session);render();return session;
    },
    setPreset(index){if(enabled&&session){session.setPreset(index);changed();}},
    setEnabled(value){enabled=!!value;if(!enabled){session=null;limits.textContent='';}render();}
  };
  controls.setEnabled(false);return controls;
}
