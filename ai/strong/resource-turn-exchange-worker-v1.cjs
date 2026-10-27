// Private research transport helper; runtime comes from the verified caller.
const assert = require('node:assert/strict');
const {createResourceTurnExchange} = require('./resource-turn-exchange-v1.cjs');
let runtime,exchange;
(async () => {
    for await (const line of require('node:readline').createInterface({input:process.stdin})) {
        try {
            const q=JSON.parse(line);assert.equal(q.op,'respond');
            assert.equal(typeof q.runtime,'string');
            if (!exchange) {runtime=q.runtime;exchange=createResourceTurnExchange(runtime);}
            assert.equal(q.runtime,runtime,'Runtime may not change within a worker');
            console.log(JSON.stringify(exchange.respond(q.request,q.actions,q.identity)));
        } catch(error) {
            console.log(JSON.stringify({error:error.name+': '+error.message}));
        }
    }
})();
