// Export production predictions only. The independent official GS receives its
// own original GIF/texture inputs, never these predicted pixels.
import {readFileSync,writeFileSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {captureNativeGarage,decodeEnvironmentImage,addNativePanorama} from '../dealership/mc3-environment.mjs';
import {copyNativeEnvironmentRGBA} from '../dealership/mc3-specular.mjs';

if(process.argv.length!==4)throw Error('Usage: node tools/mc3_raster_reference.mjs <native-pack.json> <existing-output-directory>');
const pack=JSON.parse(readFileSync(resolve(process.argv[2]),'utf8'));
if(pack.native_gs?.schema!==1)throw Error('Executed native GS packets are required.');
const decoded={...pack,images:Object.fromEntries(Object.entries(pack.images).map(([key,image])=>[key,decodeEnvironmentImage(image)])),
 sky:{...pack.sky,images:Object.fromEntries(Object.entries(pack.sky.images).map(([key,image])=>[key,decodeEnvironmentImage(image)]))}};
const base=captureNativeGarage(decoded,{viewportYSign:-1});
const panorama0=addNativePanorama(base.rgba,decoded.images.panorama,0);
const files={capture:base.rgba,panorama0,specular0:copyNativeEnvironmentRGBA(panorama0),
 specular7:copyNativeEnvironmentRGBA(addNativePanorama(base.rgba,decoded.images.panorama,7))};
for(const [name,data] of Object.entries(files))writeFileSync(join(process.argv[3],name+'.rgba'),data);
writeFileSync(join(process.argv[3],'prediction.json'),JSON.stringify({coverage:base.coverage,contributing:base.contributing},null,2)+'\n');
