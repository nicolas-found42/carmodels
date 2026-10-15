import {normaliseColourTint} from './materials.mjs';

// Preview state only: no catalog, GLB or browser-storage writes.
export function createColourControls({root=document,onTint,onReset}) {
  const picker=root.querySelector('#custom-colour'),hex=root.querySelector('#custom-colour-hex');
  const reset=root.querySelector('#reset-colour'),status=root.querySelector('#custom-colour-status');
  let enabled=false,tint=null;
  function clearFields() {
    tint=null;picker.value=hex.value='#ffffff';hex.removeAttribute('aria-invalid');
    status.textContent=enabled?'Stored colours · no custom tint':'Load a 3D model to change its colour.';
  }
  function apply(value) {
    if(!enabled)return;
    tint=normaliseColourTint(value);picker.value=hex.value=tint;
    hex.removeAttribute('aria-invalid');status.textContent=`Custom preview tint ${tint.toUpperCase()}`;
    onTint(tint);
  }
  picker.addEventListener('input',()=>apply(picker.value));
  picker.addEventListener('change',()=>apply(picker.value));
  hex.addEventListener('input',()=>{
    if(!enabled)return;
    if(!/^#[0-9a-f]{6}$/i.test(hex.value)) {
      hex.setAttribute('aria-invalid','true');status.textContent='Enter a colour as #RRGGBB. The last valid colour stays applied.';
      return;
    }
    apply(hex.value);
  });
  reset.addEventListener('click',()=>{if(!enabled)return;clearFields();onTint(null);onReset();});
  const controls={
    get tint(){return tint;},
    clear(){clearFields();if(enabled)onTint(null);},
    setEnabled(value){enabled=!!value;picker.disabled=hex.disabled=reset.disabled=!enabled;clearFields();}
  };
  controls.setEnabled(false);
  return controls;
}
