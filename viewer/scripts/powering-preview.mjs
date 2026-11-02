import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
const require = createRequire(import.meta.url);
const engine = require('../../engine/dist/index.js');
const wrapper = require('../../engine/dist/wrapper.js');
const { powerPlants } = require('../../engine/dist/src/powerPlants.js');
const clone = (value) => JSON.parse(JSON.stringify(value));
const plant = (number) => clone(powerPlants.find((p) => p.number === number));
export function poweringPosition(scenario = 'choice') {
    const G = engine.setup(
        3,
        {
            map: scenario === 'australia' ? 'Australia' : scenario === 'india' ? 'India' : 'Germany',
            variant: 'original',
            showMoney: true,
        },
        'powering-preview'
    );
    G.round = 6;
    G.step = 2;
    G.phase = engine.Phase.Bureaucracy;
    G.currentPlayers = [0, 1, 2];
    G.playerOrder = [0, 1, 2];
    G.players.forEach((p, i) => {
        p.name = ['You', 'Nora', 'Leo'][i];
        p.money = 42 + i * 11;
        p.powerPlants = [
            [27, 20, 26],
            [18, 24, 25],
            [22, 28, 30],
        ][i].map(plant);
        p.coalLeft = 3;
        p.oilLeft = 0;
        p.garbageLeft = i === 1 ? 2 : 0;
        p.uraniumLeft = 0;
        p.coalCapacity = p.oilCapacity = p.garbageCapacity = p.uraniumCapacity = 12;
        p.resourcesUsed = [];
        p.citiesPowered = 0;
        p.passed = p.skipAuction = false;
        p.cities = G.map.cities.slice(i * 8, i * 8 + 8).map((city) => ({ name: city.name, position: 0 }));
    });
    const p = G.players[0];
    if (scenario === 'discard') {
        G.phase = engine.Phase.Auction;
        G.currentPlayers = [0];
        G.auctioningPlayer = 0;
        p.powerPlants.push(plant(35));
    }
    if (scenario === 'covered') p.cities = p.cities.slice(0, 3);
    if (scenario === 'only-free') p.powerPlants = [18, 27, 33].map(plant);
    if (scenario === 'no-fuel') p.coalLeft = 0;
    if (scenario === 'empty') {
        p.powerPlants = [20, 24, 26].map(plant);
        p.coalLeft = 0;
    }
    if (scenario === 'hybrid') {
        p.powerPlants = [27, 29, 26].map(plant);
        p.coalLeft = p.oilLeft = 2;
    }
    if (scenario === 'australia') p.powerPlants = [27, 20, 11].map(plant);
    if (scenario === 'india') {
        G.citiesBuiltInCurrentRound = 0;
        p.targetCitiesPowered = 8;
    }
    for (const player of G.players) {
        player.powerPlantsNotUsed = player.powerPlants.map((plant) => plant.number);
        player.availableMoves = engine.availableMoves(G, player);
    }
    const held = new Set(G.players.flatMap((p) => p.powerPlants.map((p) => p.number)));
    G.powerPlantsDeck = G.powerPlantsDeck.filter((p) => !held.has(p.number));
    G.log.push({
        type: 'event',
        event:
            scenario === 'discard'
                ? 'Choose which Power Plant to discard.'
                : 'Round 6: power your cities and collect income.',
    });
    G.newTurn = true;
    return G;
}
const html = `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Powergrid · Plant activation preview</title><link rel="stylesheet" href="/powergrid-viewer.css"><style>.preview{display:flex;gap:12px;align-items:center;flex-wrap:wrap;background:#101d27;color:#eff5f8;padding:12px 16px;font:13px/1.4 system-ui}.preview strong{margin-right:auto}.preview small{color:#b7c8cf}.preview select,.preview button{font:inherit;padding:7px 9px;border:1px solid #6d858b;border-radius:5px;background:#253943;color:#fff}.preview label{display:flex;gap:6px;align-items:center}#error:empty{display:none}#error{background:#fee;color:#900;padding:12px}</style></head><body><header class="preview"><strong>Plant activation <small>Local preview · not published</small></strong><label>Scenario <select id="scenario"><option value="choice">Choose fuel</option><option value="discard">Discard a plant</option><option value="covered">Free plants cover every city</option><option value="only-free">Only free plants</option><option value="no-fuel">No fuel for other plants</option><option value="empty">No usable plants</option><option value="hybrid">Hybrid fuel choice</option><option value="australia">Australia + uranium mine</option><option value="india">India · must power the maximum</option></select></label><button id="reset">Reset</button><button id="theme">Light mode</button><button id="opponent">Finish next opponent</button></header><div id="error" role="alert"></div><div id="app"></div><script src="/vue.js"></script><script src="/powergrid-viewer.umd.min.js"></script><script>
const params=new URLSearchParams(location.search), scenario=params.get('scenario')||'choice', session=crypto.randomUUID();
const host=window.host=powergrid.launch('#app');let dark=true,pending=Promise.resolve();window.sentMoves=[];
const suffix='?scenario='+scenario+'&session='+session;
async function send(path,body){const response=await fetch(path+suffix,{method:body?'POST':'GET',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});const data=await response.json();if(data.error){document.querySelector('#error').textContent=data.error;throw Error(data.error);}document.querySelector('#error').textContent='';window.previewState=data.state;host.emit('state',data.state);}
host.on('fetchState',()=>{pending=pending.then(()=>send('/state'));});host.on('move',moves=>{sentMoves.push(moves);pending=pending.then(()=>send('/move',{moves}));});
host.emit('player',{index:0});host.emit('theme',{dark});host.emit('preferences',{sound:false,locale:params.get('locale')||'en',fitToScreen:false});host.emit('chat:state',{canSend:false,mentions:[]});
host.emit('avatars',Array(3).fill('data:image/svg+xml,'+encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30"><circle cx="15" cy="15" r="15" fill="#bccbc4"/></svg>')));
document.querySelector('#scenario').value=scenario;document.querySelector('#scenario').onchange=e=>location.search='?scenario='+e.target.value+'&locale='+(params.get('locale')||'en');
document.querySelector('#reset').onclick=()=>location.reload();document.querySelector('#opponent').onclick=()=>{pending=pending.then(()=>send('/opponent',{}));};document.querySelector('#theme').onclick=e=>{dark=!dark;host.emit('theme',{dark});e.target.textContent=dark?'Light mode':'Dark mode';};
pending=pending.then(()=>send('/state'));
</script></body></html>`;
export function poweringPreviewServer() {
    const states = new Map();
    return createServer(async (req, res) => {
        try {
            const url = new URL(req.url, 'http://localhost');
            res.setHeader('Cache-Control', 'no-store');
            if (url.pathname === '/') {
                res.setHeader('Content-Type', 'text/html');
                res.end(html);
                return;
            }
            if (url.pathname === '/vue.js' || /^\/powergrid-viewer[\w.-]*\.(css|js)$/.test(url.pathname)) {
                res.setHeader('Content-Type', url.pathname.endsWith('.css') ? 'text/css' : 'text/javascript');
                res.end(
                    await readFile(
                        url.pathname === '/vue.js'
                            ? require.resolve('vue/dist/vue.min.js')
                            : fileURLToPath(new URL('../dist' + url.pathname, import.meta.url))
                    )
                );
                return;
            }
            const key = url.searchParams.get('session');
            if (!key || !['/state', '/move', '/opponent'].includes(url.pathname)) {
                res.writeHead(404);
                res.end();
                return;
            }
            if (!states.has(key)) states.set(key, poweringPosition(url.searchParams.get('scenario')));
            let state = states.get(key);
            if (req.method === 'POST') {
                let raw = '';
                for await (const chunk of req) raw += chunk;
                const seat = url.pathname === '/opponent' ? state.currentPlayers.find((i) => i !== 0) : 0;
                if (seat === undefined) throw Error('No opponent is waiting.');
                const moves = url.pathname === '/opponent' ? [{ name: 'Pass', data: true }] : JSON.parse(raw).moves;
                state = await wrapper.move(clone(state), moves, seat);
                if (wrapper.toSave(state)) states.set(key, state);
            }
            res.setHeader('Content-Type', 'application/json');
            res.end(JSON.stringify({ state: wrapper.stripSecret(state, 0) }));
        } catch (error) {
            res.writeHead(422, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: error.message }));
        }
    });
}
if (process.argv[1] === fileURLToPath(import.meta.url))
    poweringPreviewServer().listen(Number(process.env.PORT || 5207), '127.0.0.1', () =>
        console.log('Powergrid activation preview: http://127.0.0.1:' + (process.env.PORT || 5207))
    );
