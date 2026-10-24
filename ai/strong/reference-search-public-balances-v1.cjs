// Scope the sampler repair to the reference opponent's nested search only.
// Neither require.cache nor any historical module export is changed.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const Module=require('node:module');
const runtime=process.env.PG_REFERENCE_RUNTIME;
assert(runtime && path.isAbsolute(runtime));
const filename=path.join(runtime,'ai/strong/search.cjs');
const source=fs.readFileSync(filename,'utf8');
const originalRequire=Module.createRequire(filename);
const repaired=require('./analysis-public-balances-v1.cjs');
const isolated=new Module(filename,module);
isolated.filename=filename;
isolated.paths=Module._nodeModulePaths(path.dirname(filename));
let replacements=0;
isolated.require=request=>{
    if (request==='../../engine/dist/src/analysis.js') {replacements++;return repaired;}
    return originalRequire(request);
};
isolated._compile(source,filename);
assert.equal(replacements,1,'Unexpected frozen search dependency');
module.exports=isolated.exports;
