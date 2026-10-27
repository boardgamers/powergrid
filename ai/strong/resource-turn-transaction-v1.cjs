// Research-only complete resource-turn boundary. No policy selection or serving integration.
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const path = require('node:path');
const {isDeepStrictEqual} = require('node:util');
const REVISION = 'resource-turn-transaction-v1';
const PASS = {name:'Pass',data:true};
const clone = value => structuredClone(value);

function canonical(value) {
    if (Array.isArray(value)) return value.map(canonical);
    if (value && typeof value === 'object') return Object.fromEntries(
        Object.keys(value).sort().map(key => [key,canonical(value[key])]));
    return value;
}

function digest(value) {
    // Bind exactly the public JSON representation, independently of object-key order.
    return crypto.createHash('sha256').update(JSON.stringify(canonical(
        JSON.parse(JSON.stringify(value))))).digest('hex');
}

function createResourceTurnTransaction(runtimeDirectory) {
    const runtime = path.resolve(runtimeDirectory);
    const c = require(path.join(runtime,'ai/core.cjs'));
    const {publicRoot} = require(path.join(runtime,'ai/strong/resource-turn-search-v1.cjs'));

    function build(request, actions) {
        const g = publicRoot({...request,featureRevision:'4.3-strategic-correction'}), seat = request.player;
        const rootSha256 = digest({player:seat,state:g});
        assert(Array.isArray(actions) && actions.length > 0,'A complete turn is required');
        const bound = 1+c.RES.reduce((sum,r) => sum+g[r+'Market'],0);
        assert(actions.length <= bound,'Resource turn exceeds the available market');
        assert(isDeepStrictEqual(actions.at(-1),PASS),'A complete turn ends with Pass');
        const moves = clone(actions), money = g.players[seat].money, counts = [0,0,0,0];
        for (const move of moves.slice(0,-1)) {
            assert.deepEqual(Object.keys(move).sort(),['data','name']);
            assert.equal(move.name,'BuyResource','Only resource purchases precede Pass');
            assert.deepEqual(Object.keys(move.data).sort(),['resource']);
            const index = c.RES.indexOf(move.data.resource);
            assert(index >= 0,'Unknown resource');
            assert(c.allLegal(g,seat).some(m => isDeepStrictEqual(m,move)),'Illegal purchase');
            c.E.move(g,clone(move),seat);counts[index]++;
            assert.equal(g.phase,c.E.Phase.Resources);
            assert.deepEqual(g.currentPlayers,[seat],'A purchase may not hand off the turn');
            assert.equal(g.newTurn,false,'A purchase must remain tentative');
        }
        const afterPurchases = {money:g.players[seat].money,
            stock:c.RES.map(r => g.players[seat][r+'Left']),
            market:c.RES.map(r => g[r+'Market'])};
        assert(c.allLegal(g,seat).some(m => isDeepStrictEqual(m,PASS)),'Illegal final Pass');
        c.E.move(g,clone(PASS),seat);
        assert.equal(g.newTurn,true,'The final Pass must commit the turn');
        assert([c.E.Phase.Resources,c.E.Phase.Building].includes(g.phase));
        return {revision:REVISION,player:seat,rootSha256,actions:moves,counts,
            cost:money-afterPurchases.money,afterPurchases,
            committed:{phase:g.phase,round:g.round,currentPlayers:clone(g.currentPlayers)},
            qualification_eligible:false};
    }

    function verify(request, envelope) {
        assert(envelope && typeof envelope === 'object' && !Array.isArray(envelope));
        const expected = build(request,envelope.actions);
        // Recheck the complete sequence on a private clone before exposing any result.
        // This also rejects stale positions, truncated buffers, extra fields and false costs.
        assert.deepEqual(envelope,expected,'Resource transaction differs from the current public root');
        return expected;
    }

    return {build,verify};
}

module.exports = {REVISION,createResourceTurnTransaction};
