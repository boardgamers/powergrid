// Research-only public whole-turn response and independent private-state execution.
// The caller must verify the supplied engine runtime and policy identity first.
const assert = require('node:assert/strict');
const path = require('node:path');
const {isDeepStrictEqual} = require('node:util');
const {createResourceTurnTransaction} = require('./resource-turn-transaction-v1.cjs');
const REVISION = 'resource-turn-exchange-v1';
const clone = value => structuredClone(value);

function checkIdentity(identity) {
    assert(identity && typeof identity === 'object' && !Array.isArray(identity));
    assert.deepEqual(Object.keys(identity).sort(), ['modelSha256','policySha256','runtimeManifestSha256']);
    for (const value of Object.values(identity)) {
        assert.equal(typeof value,'string');
        assert(/^[a-f0-9]{64}$/.test(value));
    }
}

function createResourceTurnExchange(runtimeDirectory) {
    const runtime = path.resolve(runtimeDirectory);
    const c = require(path.join(runtime,'ai/core.cjs'));
    const {publicState} = require(path.join(runtime,'ai/strong/sealed-policy-beliefs.cjs'));
    const transaction = createResourceTurnTransaction(runtime);

    function respond(request, actions, identity) {
        checkIdentity(identity);
        assert.equal(typeof request.requestId,'string');
        assert(request.requestId.length > 0);
        assert(Number.isSafeInteger(request.revision) && request.revision >= 0);
        const envelope = transaction.build(request,actions);
        return {contract:REVISION,requestId:request.requestId,revision:request.revision,
            identity:clone(identity),transaction:envelope,qualification_eligible:false};
    }

    function verify(request, response, identity) {
        assert(response && typeof response === 'object' && !Array.isArray(response));
        const expected = respond(request,response.transaction?.actions,identity);
        assert.deepEqual(response,expected,'Stale or changed resource-turn response');
        return expected;
    }

    function execute(state, request, response, identity) {
        // Both the public response and the arena's current private root must agree.
        // Validate before touching any live state, then execute on a private clone.
        verify(request,response,identity);
        const seat = request.player;
        verify({...request,state:publicState(state,seat)},response,identity);
        const g = clone(state), envelope = response.transaction, money = g.players[seat].money;
        const counts = [0,0,0,0], actions = envelope.actions;
        for (let i=0;i<actions.length;i++) {
            const move = actions[i];
            assert.deepEqual(g.currentPlayers,[seat]);
            const matches = c.allLegal(g,seat).filter(candidate => isDeepStrictEqual(candidate,move));
            assert.equal(matches.length,1,'Move is not uniquely legal in the private arena');
            if (i < actions.length-1) {
                assert.equal(move.name,'BuyResource');
                counts[c.RES.indexOf(move.data.resource)]++;
            } else {
                assert.deepEqual(move,{name:'Pass',data:true});
                assert.deepEqual({money:g.players[seat].money,
                    stock:c.RES.map(r=>g.players[seat][r+'Left']),
                    market:c.RES.map(r=>g[r+'Market'])},envelope.afterPurchases);
                assert.equal(money-g.players[seat].money,envelope.cost);
            }
            c.E.move(g,clone(move),seat);
            assert.equal(g.newTurn,i===actions.length-1,'Unexpected private turn boundary');
            if (i < actions.length-1) {
                assert.equal(g.phase,c.E.Phase.Resources);
                assert.deepEqual(g.currentPlayers,[seat]);
            }
        }
        assert.deepEqual(counts,envelope.counts);
        assert.deepEqual({phase:g.phase,round:g.round,currentPlayers:g.currentPlayers},envelope.committed);
        return {state:g,atomicMoves:actions.length};
    }

    return {respond,verify,execute};
}

module.exports = {REVISION,checkIdentity,createResourceTurnExchange};
