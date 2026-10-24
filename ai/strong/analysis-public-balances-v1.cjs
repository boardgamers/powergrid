// Isolated research repair. The historical engine files are never changed.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const crypto=require('node:crypto');
const Module=require('node:module');
const runtime=process.env.PG_REFERENCE_RUNTIME;
assert(runtime && path.isAbsolute(runtime));
const filename=path.join(runtime,'engine/dist/src/analysis.js');
const source=fs.readFileSync(filename,'utf8');
const before='const publicReplay = engine_1.reconstructState(s, s.log.length, true);';
const after='const publicReplay = s.players.some(p => p.money < 0) ? engine_1.reconstructState(s, s.log.length, true) : null;';
assert.equal(source.split(before).length,2,'Unexpected frozen sampler source');
// The sole consumer of publicReplay is already guarded by p.money < 0.
assert(source.includes('if (p.money < 0)\n            p.money = publicReplay.players[i].money;'));
const isolated=new Module(filename,module);
isolated.filename=filename;
isolated.paths=Module._nodeModulePaths(path.dirname(filename));
isolated._compile(source.replace(before,after),filename);
module.exports={...isolated.exports,repair:{
    originalSourceSha256:crypto.createHash('sha256').update(source).digest('hex'),
    before,after,scope:'Skip unused balance reconstruction only when every balance is already public. Preserve replay when any balance is unknown.'}};
