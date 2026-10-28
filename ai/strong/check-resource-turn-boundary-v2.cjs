// Pure input/engine-transition checks. No inference or search continuations.
const assert = require('node:assert/strict');
const path = require('node:path');
const {isDeepStrictEqual} = require('node:util');
const runtime = path.resolve(process.argv[2]);
const c = require(path.join(runtime, 'ai/core.cjs'));
const {publicRoot} = require(path.join(runtime, 'ai/strong/resource-turn-search-v1.cjs'));
const {preparePolicy} = require(path.join(runtime, 'ai/strong/population-hybrid-policy.cjs'));
const anchor = require('./resource-turn-anchor-v2.cjs').createResourceTurnAnchor(runtime);
const old = require('./resource-turn-anchor-v1.cjs').createResourceTurnAnchor(runtime);

function handle(q) {
    const request = {...q.request, featureRevision: '4.3-strategic-correction'};
    if (q.op === 'prepare') return preparePolicy(request);
    if (q.op === 'anchor') return anchor.prepare(request);
    if (q.op === 'old') {
        try {return {result: old.prepare(request)};}
        catch (error) {return {error: error.message};}
    }
    if (q.op === 'advance') {
        const state = publicRoot(request), seat = request.player;
        assert.equal(q.move.name, 'BuyResource');
        assert(c.allLegal(state, seat).some(move => isDeepStrictEqual(move, q.move)));
        const metadata = {cardsLeft: state.cardsLeft, nextCardWeak: state.nextCardWeak};
        c.E.move(state, structuredClone(q.move), seat); Object.assign(state, metadata);
        return {...request, state: publicRoot({...request, state})};
    }
    throw new Error('Unknown boundary check operation');
}
(async () => {
    for await (const line of require('node:readline').createInterface({input: process.stdin})) {
        try {console.log(JSON.stringify({ok: true, result: handle(JSON.parse(line))}));}
        catch (error) {console.log(JSON.stringify({ok: false, rejection: error.message}));}
    }
})().catch(error => {console.error(error.stack); process.exit(1);});
