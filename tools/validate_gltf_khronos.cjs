const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const validator = require('./validation-runtime/node_modules/gltf-validator');
const root = path.resolve(__dirname, '..');
const folder = process.argv[2] ? path.resolve(process.argv[2]) : path.join(root, 'viewer/public/recovered');
const out = path.join(root, 'research/evidence/continuation/khronos-validation.json');
(async () => {
  const files = fs.readdirSync(folder).filter(f => f.endsWith('.glb')).sort();
  const cars = [];
  for (const file of files) {
    const bytes = fs.readFileSync(path.join(folder, file));
    const report = await validator.validateBytes(new Uint8Array(bytes), {uri:file, maxIssues:10000});
    cars.push({file, sha256:crypto.createHash('sha256').update(bytes).digest('hex'), report});
    console.log(JSON.stringify({file, errors:report.issues.numErrors, warnings:report.issues.numWarnings}));
  }
  // A malformed input must fail; record the validator's independent negative control.
  let negative;
  try {
    const report = await validator.validateBytes(new Uint8Array(Buffer.from('invalid glb')));
    negative = {rejected: report.issues.numErrors > 0, report};
  } catch (e) { negative = {rejected:true, message:String(e)}; }
  const result = {validator:validator.version(), folder, cars, negative,
    summary:{cars:cars.length, errors:cars.reduce((n,c)=>n+c.report.issues.numErrors,0),
      warnings:cars.reduce((n,c)=>n+c.report.issues.numWarnings,0)},
    limits:'Format validation does not validate original game fidelity.'};
  fs.writeFileSync(out, JSON.stringify(result,null,2)+'\n');
  if (result.summary.errors || !negative.rejected) process.exitCode = 1;
})().catch(e => { console.error(e); process.exitCode=1; });
