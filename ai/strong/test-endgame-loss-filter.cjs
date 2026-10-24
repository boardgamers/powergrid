const test = require('node:test'), assert = require('node:assert/strict');
const {strictLossBound, createFilter} = require('./endgame-loss-filter.cjs');

test('strict output loss includes every supported player count and seat', () => {
    for (let n=2; n<=6; n++) for (let seat=0; seat<n; seat++) {
        const counts = Array(n).fill(10); counts[seat]=14;
        assert(strictLossBound({phase:'Building',threshold:15,currentPlayer:seat,
            cityCounts:counts,fuelUpperBound:8,opponentLowerBound:11}));
    }
});
test('ties, possible further powering, an already-triggered end and other phases are not certified', () => {
    const base={phase:'Building',threshold:15,currentPlayer:0,cityCounts:[14,11],fuelUpperBound:10,opponentLowerBound:11};
    for (const changed of [{fuelUpperBound:11},{fuelUpperBound:12},{cityCounts:[14,15]},
        {cityCounts:[13,11]},{phase:'Resources'},{currentPlayer:2},{fuelUpperBound:NaN}]) {
        assert.equal(strictLossBound({...base,...changed}),false);
    }
});
test('adapter requires a legal build and pass, is read-only, and ignores private deck/RNG fields', () => {
    const build={name:'Build',data:{name:'Berlin',price:20}}, pass={name:'Pass',data:true};
    const core={allLegal:g=>g.legal,capacity:p=>p.capacity};
    const calculate=(_,p)=>Math.min(p.cities.length,p.fueled);
    const check=createFilter(core,calculate);
    const g={map:{name:'Germany'},options:{variant:'recharged'},phase:'Building',citiesToEndGame:15,
        currentPlayers:[0],players:[{cities:Array(14).fill(0),capacity:18,fueled:10},
                                  {cities:Array(12).fill(0),capacity:12,fueled:11}],legal:[build,pass]};
    const before=structuredClone(g), certificate=check(g,0,build);
    assert.equal(certificate.fuelUpperBound,10); assert.equal(certificate.opponentLowerBound,11);
    assert.deepEqual(certificate.replacement,pass);assert.deepEqual(g,before);
    assert.deepEqual(check({...g,seed:'different',powerPlantsDeck:[{secret:true}],hiddenLog:[1]},0,build),certificate);
    assert.equal(check({...g,legal:[build]},0,build),null);
    assert.equal(check(g,0,{name:'Build',data:{name:'Berlin',price:19}}),null);
    assert.equal(check({...g,map:{name:'Australia'}},0,build),null);
    assert.equal(check({...g,options:{variant:'recharged',randomizeMap:true}},0,build),null);
    assert.equal(check(g,0,pass),null);
});
