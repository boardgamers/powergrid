// Local-only interactive preview. No BGS credentials, accounts or game writes.
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
const require = createRequire(import.meta.url);
const engine = require('../../engine/dist/index.js');
const wrapper = require('../../engine/dist/wrapper.js');
const { powerPlants } = require('../../engine/dist/src/powerPlants.js');
const copy = (value) => JSON.parse(JSON.stringify(value));
function position(mode) {
    const fastBid = mode.includes('sealed');
    const G = engine.setup(
        3,
        { map: 'Germany', variant: 'original', showMoney: !mode.includes('hidden'), fastBid },
        'auction-preview'
    );
    G.round = 2;
    const yourTurn = ['your-turn', 'only-pass', 'resources', 'building', 'powering'].includes(mode);
    if (mode === 'resources') G.phase = engine.Phase.Resources;
    if (mode === 'building') G.phase = engine.Phase.Building;
    if (mode === 'powering') G.phase = engine.Phase.Bureaucracy;
    G.playerOrder = yourTurn ? [0, 1, 2] : [2, 0, 1];
    G.currentPlayers = [yourTurn ? 0 : 2];
    const plant = (n) => copy(powerPlants.find((p) => p.number === n));
    G.actualMarket = (fastBid ? [17, 19, 20, 21] : [8, 10, 13, 15]).map(plant);
    G.futureMarket = [22, 23, 24, 25].map(plant);
    G.players.forEach((p, i) => {
        p.name = ['You', 'Leo', 'Ada'][i];
        p.money = [mode === 'only-pass' ? 1 : 10, 40, 50][i];
        p.powerPlants = [plant([3, 4, 5][i])];
        if (mode === 'resources' && i === 0) p.oilCapacity = 4;
        if (mode === 'building' && i === 0) p.money = 30;
        if (mode === 'powering') {
            p.powerPlantsNotUsed = p.powerPlants.map((plant) => plant.number);
            if (i === 0) {
                p.oilCapacity = 4;
                p.oilLeft = 2;
                p.cities = [{ name: G.map.cities[0].name, position: 0 }];
            }
        }
        p.availableMoves = null;
    });
    const visible = new Set(
        [...G.actualMarket, ...G.futureMarket, ...G.players.flatMap((p) => p.powerPlants)].map((p) => p.number)
    );
    G.powerPlantsDeck = G.powerPlantsDeck.filter((p) => !visible.has(p.number));
    G.cardsLeft = G.powerPlantsDeck.length;
    if (mode.startsWith('fuel-') || mode.startsWith('city-')) {
        G.phase = mode.startsWith('fuel-') ? engine.Phase.Resources : engine.Phase.Building;
        G.playerOrder = [1, 0, 2]; // Reverse-order phases: Ada, you, Leo.
        G.currentPlayers = [2];
        if (G.phase === engine.Phase.Resources) {
            G.players[0].money = 1;
            G.players[0].oilCapacity = 4;
            G.oilMarket = mode.includes('impossible') ? 0 : 22; // One $1 oil, then $2.
            G.players[2].oilCapacity = 4;
        } else {
            // Find a starting network with one uniquely cheapest expansion.
            for (const city of G.map.cities) {
                G.players[0].cities = [{ name: city.name, position: 0 }];
                G.players[0].money = 1000;
                const choices = (engine.availableMoves(G, G.players[0]).Build || []).sort((a, b) => a.price - b.price);
                if (choices.length > 1 && choices[0].price < choices[1].price) {
                    G.players[0].money = choices[0].price;
                    break;
                }
            }
            if (engine.availableMoves(G, G.players[0]).Build?.length !== 1)
                throw Error('Preview needs a unique affordable city.');
        }
    }
    const activePlayer = G.players[G.currentPlayers[0]];
    activePlayer.availableMoves = engine.availableMoves(G, activePlayer);
    G.log.push({
        type: 'event',
        event: mode.startsWith('fuel-')
            ? 'Waiting for Ada to finish buying resources.'
            : mode.startsWith('city-')
            ? 'Waiting for Ada to finish building.'
            : yourTurn
            ? 'Your turn to start an auction.'
            : 'Waiting for Ada to start an auction.',
    });
    G.newTurn = true;
    return G;
}
const states = new Map();
const html = `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Power Grid · Auction auto-pass preview</title><link rel="stylesheet" href="/bundle.css"><style>body{margin:0;background:#e8ebdf;font-family:system-ui}.preview{display:flex;gap:12px;align-items:center;flex-wrap:wrap;background:#173b32;color:#fff;padding:10px 16px;font-size:13px}.preview button,.preview select{font:inherit;padding:7px}.preview a{color:white}.hint{font-size:13px;padding:8px 16px;margin:0;background:#edf1e8;color:#253b2c}#error{color:#9e1515}#error:empty{display:none}</style></head><body><header class="preview"><strong>Local preview</strong><select id="mode" aria-label="Auction scenario"><option value="fuel-hidden">Hidden money · last affordable fuel</option><option value="fuel-public">Public money · last affordable fuel</option><option value="fuel-hidden-impossible">Hidden money · empty oil market</option><option value="fuel-public-impossible">Public money · empty oil market</option><option value="city-hidden">Hidden money · last affordable city</option><option value="city-public">Public money · last affordable city</option><option value="your-turn">Your turn · start an auction</option><option value="only-pass">Your turn · only passing is possible</option><option value="resources">Your turn · buy resources</option><option value="building">Your turn · build cities</option><option value="powering">Your turn · activate plants</option><option value="public">Public money · open auction</option><option value="hidden">Hidden money · open auction</option><option value="public-sealed">Public money · sealed auction</option><option value="hidden-sealed">Hidden money · sealed auction</option></select><button id="opponent">Ada bids 10</button><button id="reset">Reset</button><a href="/mobile">Mobile preview</a></header><p class="hint">You have 10. With hidden money, try the auto-pass checkbox in your player card before Ada bids.</p><p id="error" role="alert"></p><div id="app"></div><script src="/vue.js"></script><script src="/bundle.js"></script><script>
const query=new URLSearchParams(location.search),mode=query.get('mode')||'public';
const host=window.host=powergrid.launch('#app');
document.querySelector('#mode').value=mode;
document.querySelector('a[href="/mobile"]').href='/mobile?mode='+encodeURIComponent(mode);
if(mode==='only-pass')document.querySelector('.hint').textContent='You have 1. No plant is affordable, so passing is the only legal action.';
if(mode==='building')document.querySelector('.hint').textContent='Build a city to change skip to confirm. Undo all builds to restore skip.';
if(mode==='powering')document.querySelector('.hint').textContent='Activate your oil plant to change skip to confirm. Hover its border to see the white highlight.';
if(mode.startsWith('fuel-')||mode.startsWith('city-'))document.querySelector('.hint').textContent=mode.includes('impossible')?'No oil is left: you are skipped even with hidden money and auto-pass off. Click Ada passes.':'Ada will take your last affordable '+(mode.startsWith('fuel-')?'oil cube':'city')+'. Toggle auto-pass in your card first. Hidden money keeps your turn unless you opt in; public money always skips. Reset to compare.';
document.querySelector('#mode').onchange=e=>{query.set('mode',e.target.value);location.search='?'+query;};
async function send(path,body){const response=await fetch(path+'?mode='+mode,{method:body?'POST':'GET',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});const data=await response.json();document.querySelector('#error').textContent=data.error||'';if(data.error)return;host.emit('settings',data.settings);host.emit('state',data.state);const button=document.querySelector('#opponent');button.textContent=data.next;button.disabled=!data.opponent;}
host.on('fetchState',()=>send('/state'));host.on('move',move=>send('/move',{move}));host.on('update:setting',setting=>send('/setting',setting));
host.on('update:preference',({name,value})=>{if(name==='textActions'){query.set('text',value?'1':'0');history.replaceState(null,'','?'+query);}});
host.emit('player',{index:0});host.emit('preferences',{sound:false,textActions:query.get('text')==='1',locale:query.get('locale')||'en'});host.emit('chat:state',{canSend:false,mentions:[]});
document.querySelector('#opponent').onclick=()=>send('/opponent',{});document.querySelector('#reset').onclick=()=>send('/reset',{});send('/state');
</script></body></html>`;
export function auctionPreviewServer() {
    // Optional public CDN assets; all state/settings/moves still stay local.
    const viewerUrl = process.env.POWERGRID_VIEWER_URL;
    const page = viewerUrl
        ? html
              .replace('src="/bundle.js"', `src="${new URL(viewerUrl).href}"`)
              .replace('href="/bundle.css"', `href="${new URL('powergrid-viewer.css', viewerUrl).href}"`)
        : html;
    return createServer(async (req, res) => {
        const url = new URL(req.url, 'http://localhost');
        const mode = url.searchParams.get('mode') || 'public';
        res.setHeader('Cache-Control', 'no-store');
        try {
            if (url.pathname === '/mobile') {
                res.setHeader('Content-Type', 'text/html');
                return res.end(
                    '<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><title>Power Grid · Mobile auction preview</title><style>body{margin:0;background:#202b24;display:grid;justify-content:center}iframe{width:390px;max-width:100vw;height:100dvh;border:0}</style><iframe title="Mobile auction preview" src="/?mode=' +
                        encodeURIComponent(mode) +
                        '"></iframe>'
                );
            }
            const files = {
                '/bundle.js': new URL('../dist/powergrid-viewer.umd.min.js', import.meta.url),
                '/bundle.css': new URL('../dist/powergrid-viewer.css', import.meta.url),
                '/vue.js': require.resolve('vue/dist/vue.min.js'),
            };
            if (/^\/powergrid-viewer\.umd\.min\.(?:locale-[a-zA-Z-]+|geography-[a-z-]+)\.js$/.test(url.pathname))
                files[url.pathname] = new URL('../dist' + url.pathname, import.meta.url);
            if (url.pathname === '/' || files[url.pathname]) {
                res.setHeader(
                    'Content-Type',
                    url.pathname.endsWith('.js')
                        ? 'text/javascript'
                        : url.pathname.endsWith('.css')
                        ? 'text/css'
                        : 'text/html'
                );
                return res.end(files[url.pathname] ? await readFile(files[url.pathname]) : page);
            }
            if (!states.has(mode)) states.set(mode, position(mode));
            let state = states.get(mode);
            if (req.method === 'POST') {
                let raw = '';
                for await (const part of req) raw += part;
                const body = JSON.parse(raw || '{}');
                if (url.pathname === '/reset') state = position(mode);
                else if (url.pathname === '/setting')
                    state = wrapper.setPlayerSettings(copy(state), 0, {
                        ...wrapper.playerSettings(state, 0),
                        [body.name]: body.value,
                    });
                else if (url.pathname === '/move') {
                    if (!state.currentPlayers.includes(0) && !wrapper.canMoveOutOfTurn(state, body.move, 0))
                        throw Error('Not your turn.');
                    const result = await wrapper.move(copy(state), body.move, 0);
                    if (!wrapper.toSave(result)) {
                        res.setHeader('Content-Type', 'application/json');
                        return res.end(
                            JSON.stringify({
                                state: wrapper.stripSecret(result, 0),
                                settings: wrapper.playerSettings(state, 0),
                                next: 'Your turn',
                                opponent: false,
                            })
                        );
                    }
                    state = result;
                } else if (url.pathname === '/opponent') {
                    const seat = state.currentPlayers.find((p) => p !== 0);
                    if (seat === undefined) throw Error('It is your turn.');
                    if (seat === 2 && mode.startsWith('fuel-') && !mode.includes('impossible')) {
                        const buy = engine
                            .availableMoves(state, state.players[seat])
                            .BuyResource.find((r) => r.resource === 'oil');
                        state = await wrapper.move(
                            copy(state),
                            [
                                { name: 'BuyResource', data: buy },
                                { name: 'Pass', data: true },
                            ],
                            seat
                        );
                    } else if (seat === 2 && mode.startsWith('city-')) {
                        const target = engine.availableMoves(state, state.players[0]).Build[0];
                        const build = engine
                            .availableMoves(state, state.players[seat])
                            .Build.find((c) => c.name === target.name);
                        state = await wrapper.move(
                            copy(state),
                            [
                                { name: 'Build', data: build },
                                { name: 'Pass', data: true },
                            ],
                            seat
                        );
                    } else if (state.phase === engine.Phase.Auction && !state.chosenPowerPlant && seat === 2) {
                        state = await wrapper.move(
                            copy(state),
                            [
                                { name: 'ChoosePowerPlant', data: state.actualMarket[0].number },
                                { name: 'Bid', data: state.options.fastBid ? 17 : 10 },
                            ],
                            seat
                        );
                    } else state = await wrapper.move(copy(state), { name: 'Pass', data: true }, seat);
                }
                states.set(mode, state);
            }
            const opponent = state.currentPlayers.find((p) => p !== 0);
            res.setHeader('Content-Type', 'application/json');
            res.end(
                JSON.stringify({
                    state: wrapper.stripSecret(state, 0),
                    settings: wrapper.playerSettings(state, 0),
                    opponent: opponent !== undefined,
                    next:
                        opponent === undefined
                            ? 'Your turn'
                            : opponent === 2 && mode.startsWith('fuel-') && !mode.includes('impossible')
                            ? 'Ada buys the last $1 oil and finishes'
                            : opponent === 2 && mode.startsWith('city-')
                            ? 'Ada builds your last affordable city and finishes'
                            : state.chosenPowerPlant || state.phase !== engine.Phase.Auction
                            ? state.players[opponent].name + ' passes'
                            : 'Ada bids ' + (state.options.fastBid ? 17 : 10),
                })
            );
        } catch (error) {
            res.writeHead(422, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: error.message }));
        }
    });
}
if (process.argv[1] === fileURLToPath(import.meta.url))
    auctionPreviewServer().listen(Number(process.env.PORT || 5216), '127.0.0.1', () =>
        console.log('Auction preview: http://127.0.0.1:' + (process.env.PORT || 5216))
    );
