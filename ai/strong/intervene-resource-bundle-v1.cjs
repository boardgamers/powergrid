// One frozen diagnostic resource bundle. Not a serving rule or training label.
const assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path');
const root = process.env.PG_DIAGNOSTIC_RUNTIME;
assert(root && path.isAbsolute(root));
const c = require(path.join(root,'ai/core.cjs'));
const {calculateMaxCitiesPowered} = require(path.join(root,'engine/dist/src/engine.js'));
const target = JSON.parse(process.env.PG_RESOURCE_BRANCH), roots = new WeakSet();
assert(['original','buy_coal_3'].includes(target.branch));
const setup = c.E.setup, move = c.E.move;
let applied = 0;
Object.defineProperty(c.E,'setup',{configurable:true,enumerable:true,value:function (...args) {
    const state = setup(...args); roots.add(state); return state;
}});
Object.defineProperty(c.E,'move',{configurable:true,enumerable:true,value:function (state,action,seat) {
    if (roots.has(state) && state.round === target.round && state.phase === 'Resources' &&
            seat === target.seat && action.name === 'Pass') {
        assert.equal(++applied,1,'Must intervene exactly once');
        const p = state.players[seat];
        const before = {round:state.round,phase:state.phase,seat,money:p.money,cities:p.cities.length,
            resources:Object.fromEntries(c.RES.map(r=>[r,p[r+'Left']])),
            plants:p.powerPlants.map(pp=>pp.number),market:Object.fromEntries(c.RES.map(r=>[r,state[r+'Market']])),
            threshold:state.citiesToEndGame};
        assert.deepEqual(before,target.before,'Public decision prefix changed');
        const power = () => calculateMaxCitiesPowered(state,{...p,cities:Array(c.capacity(p))});
        const receipt = {applied,branch:target.branch,before,fuelBefore:power(),purchases:[]};
        if (target.branch === 'buy_coal_3') {
            for (let i = 0; i < 3; i++) {
                const buy = {name:'BuyResource',data:{resource:'coal'}};
                assert(c.allLegal(state,seat).some(m=>JSON.stringify(m)===JSON.stringify(buy)),'Illegal purchase');
                const cash = p.money;
                move(state,buy,seat);
                receipt.purchases.push({action:buy,paid:cash-p.money});
                assert.equal(state.phase,'Resources'); assert(state.currentPlayers.includes(seat));
            }
            assert(power() >= target.before.threshold,'Bundle must reach the public end threshold');
        }
        receipt.fuelAfter = power(); receipt.moneyAfter = p.money;
        fs.writeFileSync(process.env.PG_TRACE_PATH+'.intervention.json',JSON.stringify(receipt)+'\n',{flag:'wx'});
    }
    return move(state,action,seat);
}});
