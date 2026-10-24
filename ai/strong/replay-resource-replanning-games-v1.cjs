// Independently replay saved atomic choices through the engine and retain slow public roots.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const base=path.resolve(process.argv[2]),runtime=path.join(base,'runtime');
const c=require(path.join(runtime,'ai/core.cjs')),eco=require(path.join(runtime,'ai/strong/economics.cjs'));
const beliefs=require(path.join(runtime,'ai/strong/sealed-policy-beliefs.cjs'));
const read=p=>JSON.parse(fs.readFileSync(p));
const selection=read(path.join(base,'selection.json'));
const cases=selection.game_smokes;
assert.equal(cases.length,4);
for(const x of cases)assert(fs.existsSync(path.join(base,'games',x.label,`game-${x.episode}.json`)));
const out=path.join(base,'replays');fs.mkdirSync(out,{recursive:false});
const write=(name,d)=>fs.writeFileSync(path.join(out,name),JSON.stringify(d,null,2)+'\n',{flag:'wx'});
const report={passed:false,games:0,learner_moves:0,opponent_moves:0,resource_moves:0,qualification_eligible:false};
try {
    for(const entry of cases) {
        const folder=path.join(base,'games',entry.label),config=read(path.join(folder,'config.json'));
        const reference=read(path.join(folder,`game-${entry.episode}.json`));
        const rows=fs.readFileSync(path.join(folder,`decisions-${entry.episode}.jsonl`),'utf8').trim().split('\n').map(JSON.parse);
        assert.equal(config.opponent,'economic');assert.equal(reference.terminal.seat,0);
        const gameSeed=config.seed+'-'+Math.floor(entry.episode/(4*entry.players));
        const g=c.E.setup(entry.players,{map:'Germany',variant:entry.episode%2?'recharged':'original',
            fastBid:entry.episode%4<2,showMoney:true},gameSeed),rng=c.seedrandom(gameSeed+'-bot');
        let steps=0,worst=null;const moves={};
        function advance() {
            while(!c.E.ended(g)&&g.currentPlayers[0]!==0) {
                const seat=g.currentPlayers[0];c.E.move(g,eco.choose(g,seat,rng,'economic').action,seat);
                steps++;report.opponent_moves++;
            }
        }
        advance();
        for(const row of rows) {
            assert(!c.E.ended(g));assert.equal(g.currentPlayers[0],0);assert.equal(g.round,row.round);
            const legal=c.candidates(g,0);assert.deepEqual(legal[row.index],row.move);
            if(row.resourcePlan) {
                assert.equal(g.phase,c.E.Phase.Resources);assert.deepEqual(row.resourcePlan.firstMove,row.move);
                if(!worst||row.elapsedMs>worst.reference.elapsedMs)worst={
                    case:entry.label,decision:row.decision,request:{state:beliefs.publicState(g,0),player:0},reference:row};
                report.resource_moves++;
            }
            c.E.move(g,structuredClone(legal[row.index]),0);steps++;report.learner_moves++;
            moves[row.move.name]=(moves[row.move.name]||0)+1;advance();
        }
        assert(c.E.ended(g));assert.equal(steps,reference.terminal.steps);
        assert.deepEqual(moves,reference.terminal.policyMoves);
        assert.deepEqual(c.outcome(g),reference.terminal.value);
        assert.deepEqual({round:g.round,players:g.players.map(p=>({cities:p.cities.length,
            powered:p.citiesPowered,money:p.money,capacity:c.capacity(p),plants:p.powerPlants.map(x=>x.number)}))},reference.terminal.final);
        assert(worst);write(entry.label+'-slow-root.json',worst);report.games++;
    }
    report.passed=true;write('assessment.json',report);console.log(JSON.stringify(report));
} catch(error) {
    write('failure.json',{error:error.stack,report});console.error(error.stack);process.exitCode=1;
}
