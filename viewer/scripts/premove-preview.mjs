import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
const require = createRequire(import.meta.url);
const engine = require('../../engine/dist/index.js');
const wrapper = require('../../engine/dist/wrapper.js');
const { powerPlants } = require('../../engine/dist/src/powerPlants.js');
const getPowerPlant = (number) => JSON.parse(JSON.stringify(powerPlants.find((p) => p.number === number)));
const { automation } = require('../../engine/dist/src/premoves.js');
const files = {
    '/bundle.js': fileURLToPath(new URL('../dist/powergrid-viewer.umd.min.js', import.meta.url)),
    '/bundle.css': fileURLToPath(new URL('../dist/powergrid-viewer.css', import.meta.url)),
    '/vue.js': require.resolve('vue/dist/vue.min.js'),
};
function position(scenario) {
    const G = engine.setup(3, { map: 'Germany', variant: 'original', showMoney: false }, 'premoves');
    G.round = 3;
    G.phase = engine.Phase.Resources;
    G.playerOrder = [2, 1, 0];
    G.currentPlayers = [1];
    G.players.forEach((p, i) => {
        p.name = ['You', 'Ada', 'Leo'][i];
        p.money = 70;
        p.powerPlants = (
            i === 0 && scenario === 'mobile-resources'
                ? [21, 24, 23]
                : [
                      [4, 13],
                      [8, 18],
                      [20, 22],
                  ][i]
        ).map(getPowerPlant);
        p.coalCapacity = i === 0 ? 4 : 6;
        p.coalLeft = i === 0 ? 2 : 3;
        p.powerPlantsNotUsed = p.powerPlants.map((plant) => plant.number);
        p.passed = i === 0;
        p.skipAuction = false;
        p.availableMoves = null;
        if (i === 0 && scenario === 'mobile-resources') {
            p.coalCapacity = 0;
            p.hybridCapacity = 4;
            p.garbageCapacity = 4;
            p.uraniumCapacity = 2;
        }
    });
    G.actualMarket = [3, 5, 6, 7].map(getPowerPlant);
    G.futureMarket = [9, 10, 11, 12].map(getPowerPlant);
    const visible = new Set(
        [...G.actualMarket, ...G.futureMarket, ...G.players.flatMap((p) => p.powerPlants)].map((p) => p.number)
    );
    G.powerPlantsDeck = G.powerPlantsDeck.filter((p) => !visible.has(p.number));
    G.cardsLeft = G.powerPlantsDeck.length;
    if (scenario === 'auction') {
        G.phase = engine.Phase.Auction;
        G.players[0].skipAuction = false;
        G.players[0].passed = false;
        G.currentPlayers = [0];
    }
    if (scenario === 'resources' || scenario === 'mobile-resources') {
        G.players[0].passed = false;
        G.currentPlayers = [0];
        G.players[0].coalLeft = 0;
    }
    if (scenario === 'powering') {
        G.phase = engine.Phase.Building;
        G.players[0].cities = G.map.cities.slice(0, 2).map((c) => ({ name: c.name, position: 0 }));
        G.players[0].money = 42;
    }
    G.currentPlayers.forEach((i) => (G.players[i].availableMoves = engine.availableMoves(G, G.players[i])));
    G.log.push({
        type: 'event',
        event: `Round 3: ${
            scenario === 'auction'
                ? 'consider your next plant'
                : scenario === 'powering'
                ? 'the remaining players are building'
                : 'resource buying is in progress'
        }.`,
    });
    automation(G);
    G.newTurn = true;
    return G;
}
const states = new Map();
let revision = 0;
const html = `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Powergrid · Round planning</title><link rel="stylesheet" href="/bundle.css"><style>body{margin:0;background:#fafbf6;font-family:system-ui}.preview{display:flex;gap:16px;align-items:center;flex-wrap:wrap;background:#174132;color:#fff;padding:12px 18px;font-size:13px}.preview a{color:#d7edc5}.preview button,.preview select{font:inherit;padding:6px;border-radius:4px}#error:empty{display:none}#error{background:#fee;padding:12px;color:#900}</style></head><body><header class="preview"><strong>Powergrid · Local preview</strong><label>Position <select id="scenario"><option value="after-resources">After buying resources</option><option value="powering">After building cities</option><option value="auction">Consider a plant</option><option value="resources">Buy resources</option></select></label><button id="opponent">Finish next opponent phase</button><button id="reset">Reset position</button><a id="other">Other player’s view</a></header><div id="error" role="status"></div><div id="app"></div><script src="/vue.js"></script><script src="/bundle.js"></script><script>
const params=new URLSearchParams(location.search),scenario=params.get('scenario')||'after-resources',seat=Number(params.get('seat')||0);
if(params.has('device')) document.querySelector('header.preview').style.display='none';
const host=window.powergrid.launch('#app');let revision=-1;
document.querySelector('#scenario').value=scenario;document.querySelector('#scenario').onchange=e=>location.search='?scenario='+e.target.value;
document.querySelector('#other').href='?scenario='+scenario+'&seat='+((seat+1)%3);
async function send(path,body){const res=await fetch(path+'?scenario='+scenario+'&seat='+seat,{method:body?'POST':'GET',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});const data=await res.json();if(data.error){document.querySelector('#error').textContent=data.error;return;}document.querySelector('#error').textContent='';revision=data.revision;host.emit('state',data.state);}
host.on('fetchState',()=>send('/state'));host.on('move',move=>send('/move',{move}));host.emit('player',{index:seat});host.emit('preferences',{sound:false,disableHelp:false,fitToScreen:false});host.emit('chat:state',{canSend:false,mentions:[]});
document.querySelector('#opponent').onclick=()=>send('/opponent',{});document.querySelector('#reset').onclick=()=>send('/reset',{});
setInterval(async()=>{const r=await fetch('/state?scenario='+scenario+'&seat='+seat);const data=await r.json();if(data.revision!==revision){revision=data.revision;host.emit('state',data.state);}},1000);send('/state');
</script></body></html>`;
export function premovePreviewServer() {
    return createServer(async (req, res) => {
        const url = new URL(req.url, 'http://localhost'),
            scenario = url.searchParams.get('scenario') || 'after-resources',
            seat = Number(url.searchParams.get('seat') || 0);
        try {
            res.setHeader('Cache-Control', 'no-store');
            if (url.pathname === '/mobile') {
                res.setHeader('Content-Type', 'text/html');
                return res.end(
                    `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Powergrid · Try resource buying</title><style>*{box-sizing:border-box}body{margin:0;background:#202620;color:#e8eddf;font:14px system-ui;display:flex;flex-direction:column;align-items:center}header{display:flex;align-items:center;gap:16px;padding:14px}button{font:inherit;background:#394637;color:#e8eddf;border:1px solid #71826a;border-radius:6px;padding:8px 12px;cursor:pointer}iframe{width:390px;max-width:100%;height:min(844px,calc(100dvh - 76px));min-height:420px;border:1px solid #51604b;border-radius:8px}</style></head><body><header>Try resource buying <button id="restart">Reset</button></header><iframe title="Interactive mobile resource buying" src="/?scenario=mobile-resources&device=phone"></iframe><script>const frame=document.querySelector('iframe');document.querySelector('#restart').onclick=()=>frame.contentDocument.querySelector('#reset').click();frame.addEventListener('load',()=>{let tries=40;const timer=setInterval(()=>{const el=frame.contentDocument.querySelector('[data-tutorial="resources"]');if(el&&el.getBoundingClientRect().height>0){frame.contentWindow.scrollTo(0,frame.contentWindow.scrollY+el.getBoundingClientRect().top-130);clearInterval(timer);}else if(!--tries)clearInterval(timer);},150);});</script></body></html>`
                );
            }
            if (/^\/powergrid-viewer\.umd\.min\.geography-[a-z-]+\.js$/.test(url.pathname)) {
                res.setHeader('Content-Type', 'text/javascript');
                return res.end(await readFile(new URL('../dist' + url.pathname, import.meta.url)));
            }
            if (url.pathname === '/' || files[url.pathname]) {
                res.setHeader(
                    'Content-Type',
                    url.pathname.endsWith('.js')
                        ? 'text/javascript'
                        : url.pathname.endsWith('.css')
                        ? 'text/css'
                        : 'text/html'
                );
                res.end(files[url.pathname] ? await readFile(files[url.pathname]) : html);
                return;
            }
            res.setHeader('Content-Type', 'application/json');
            if (!states.has(scenario)) states.set(scenario, position(scenario));
            let state = states.get(scenario);
            if (req.method === 'POST') {
                if (url.pathname === '/reset') {
                    state = position(scenario);
                    states.set(scenario, state);
                    revision++;
                } else if (url.pathname === '/move') {
                    let raw = '';
                    for await (const part of req) raw += part;
                    const { move } = JSON.parse(raw);
                    if (!state.currentPlayers.includes(seat) && !wrapper.canMoveOutOfTurn(state, move, seat))
                        throw Error('Not your turn');
                    const result = await wrapper.move(JSON.parse(JSON.stringify(state)), move, seat);
                    if (wrapper.toSave(result)) {
                        state = result;
                        states.set(scenario, state);
                        revision++;
                    } else {
                        res.end(JSON.stringify({ revision, state: wrapper.stripSecret(result, seat) }));
                        return;
                    }
                } else if (url.pathname === '/opponent') {
                    const opponent = state.currentPlayers.find((i) => i !== seat);
                    if (opponent === undefined) throw Error('It is your turn.');
                    state = await wrapper.move(
                        JSON.parse(JSON.stringify(state)),
                        { name: 'Pass', data: true },
                        opponent
                    );
                    states.set(scenario, state);
                    revision++;
                }
            }
            res.end(JSON.stringify({ revision, state: wrapper.stripSecret(state, seat) }));
        } catch (error) {
            res.writeHead(422, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: error.message }));
        }
    });
}
if (process.argv[1] === fileURLToPath(import.meta.url))
    premovePreviewServer().listen(Number(process.env.PORT || 5204), '127.0.0.1', () =>
        console.log('Powergrid planning: http://127.0.0.1:' + (process.env.PORT || 5204))
    );
