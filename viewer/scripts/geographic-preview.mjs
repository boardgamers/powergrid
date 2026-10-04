// Local-only exploration. No engine/viewer source or published assets are changed.
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
const require = createRequire(import.meta.url);
const engine = require('../../engine/dist/index.js');
const wrapper = require('../../engine/dist/wrapper.js');
const maps = Object.fromEntries(['germany', 'ukireland'].map((key) => [key, require(`../../engine/dist/src/maps/${key}.js`).map]));
const geometry = JSON.parse(await readFile(new URL('./geography/outlines.json', import.meta.url)));

export function geographicPreviewState(key = 'germany', allRegions = true) {
    const authored = maps[key];
    if (!authored) throw Error('Unknown preview map');
    const state = engine.setup(3, { map: authored.name, variant: 'original', showMoney: true }, 'outline-preview');
    if (allRegions) {
        const [rx, ry] = state.map.adjustRatio;
        state.map.cities = authored.cities.map((city) => ({ ...city, x: city.x * rx, y: city.y * ry }));
        state.map.connections = JSON.parse(JSON.stringify(authored.connections));
    }
    state.players.forEach((player, i) => {
        player.name = ['You', 'Nora', 'Leo'][i];
        player.availableMoves = {};
    });
    state.currentPlayers = [];
    return wrapper.stripSecret(state, 0);
}

const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Powergrid · Geographic outlines</title><link rel="stylesheet" href="/powergrid-viewer.css"><style>
*{box-sizing:border-box}body{margin:0;background:#171717;color:#e8ece7;font:14px/1.4 system-ui}header{padding:14px 20px;border-bottom:1px solid #3e493e;display:flex;align-items:center;gap:18px;flex-wrap:wrap}header strong{margin-right:auto}header small{font-weight:400;color:#aeb9ad}label{display:flex;align-items:center;gap:7px}select,button{font:inherit;background:#263027;color:inherit;border:1px solid #63715f;border-radius:5px;padding:7px 10px}button{cursor:pointer}main{max-width:1400px;margin:auto;padding:16px}#map-only{width:100%;height:calc(100vh - 160px);min-height:380px;background:yellowgreen;border-radius:5px}#app{position:absolute;left:-20000px;width:1300px;visibility:hidden}body.full #app{position:static;left:auto;width:auto;visibility:visible}body.full #map-only{display:none}footer{padding:10px 0;color:#b7c2b2;font-size:12px}footer a{color:inherit}body.light{background:#e7ebda;color:#1d2a1d}body.light header{border-color:#a6b297}body.light select,body.light button{background:#f0f2e9;color:#1d2a1d}body.light small,body.light footer{color:#4c6043}#error{color:#ffaba0}svg .geographic-backdrop{pointer-events:none}@media(max-width:600px){header{padding:12px;gap:10px}header strong{width:100%}main{padding:10px}#map-only{height:calc(100vh - 240px)}}
</style></head><body><header><strong>Geographic outlines <small>Local preview</small></strong><label>Map <select id="map"><option value="germany">Germany</option><option value="ukireland">UK &amp; Ireland</option></select></label><label>Backdrop <select id="style"><option value="wash">Soft land + outline</option><option value="line">Outline only</option><option value="none">Off</option></select></label><label><input type="checkbox" id="regions" checked> All regions</label><button id="full">Full board</button><button id="theme">Light mode</button></header><main><svg id="map-only" role="img" aria-label="Geographic outline behind the Power Grid network"></svg><div id="app"></div><div id="error" role="alert"></div><footer>Existing cities and links, with a fitted geographic backdrop. Hover a city for its name. <a href="https://www.naturalearthdata.com/about/terms-of-use/">Natural Earth</a> · public domain. Local visual experiment; full-region view is illustrative.</footer></main><script src="/vue.js"></script><script src="/powergrid-viewer.umd.min.js"></script><script>
const params=new URLSearchParams(location.search), key=params.get('map')||'germany';let mode=params.get('style')||'wash',dark=true,full=false,current;
document.querySelector('#map').value=key;document.querySelector('#style').value=mode;document.querySelector('#regions').checked=params.get('regions')!=='selected';
const host=window.host=powergrid.launch('#app');host.emit('player',{index:0});host.emit('theme',{dark});host.emit('preferences',{sound:false,locale:'en',fitToScreen:false,stackOnPortrait:false});host.emit('chat:state',{canSend:false,mentions:[]});host.emit('avatars',Array(3).fill('data:image/svg+xml,'+encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30"><circle cx="15" cy="15" r="15" fill="#bbc9ae"/></svg>')));
const ns='http://www.w3.org/2000/svg';
function draw(){
 const slot=document.querySelector('#app [data-tutorial="map"]');if(!slot||!slot.firstElementChild||!current)return;
 const group=slot.firstElementChild,scene=slot.ownerSVGElement;scene.querySelector('.geographic-scene-backdrop')?.remove();
 const land=document.createElementNS(ns,'g');land.classList.add('geographic-backdrop');land.setAttribute('aria-hidden','true');land.setAttribute('pointer-events','none');land.setAttribute('transform','scale('+current.ratio.join(' ')+')');
 for(const d of current.outline.paths){const p=document.createElementNS(ns,'path');p.setAttribute('d',d);p.setAttribute('fill',mode==='wash'?'#dce8aa':'none');p.setAttribute('fill-opacity','.48');p.setAttribute('stroke','#526b39');p.setAttribute('stroke-opacity','.68');p.setAttribute('stroke-width','2');p.setAttribute('stroke-linejoin','round');land.append(p);}
 land.style.display=mode==='none'?'none':'';
 const boardLand=document.createElementNS(ns,'g');boardLand.classList.add('geographic-scene-backdrop');boardLand.setAttribute('pointer-events','none');boardLand.setAttribute('transform',group.getAttribute('transform')||'');boardLand.append(land.cloneNode(true));scene.insertBefore(boardLand,scene.children[1]);
 const svg=document.querySelector('#map-only');svg.replaceChildren(group.cloneNode(true));svg.firstElementChild.removeAttribute('transform');svg.firstElementChild.prepend(land);
 // Include the whole outline even when it is switched off: on/off has no zoom jump.
 const box=svg.firstElementChild.getBBox(),[rx,ry]=current.ratio,b=current.outline.bounds;
 const x=Math.min(box.x,b[0]*rx)-24,y=Math.min(box.y,b[1]*ry)-24,x2=Math.max(box.x+box.width,b[2]*rx)+24,y2=Math.max(box.y+box.height,b[3]*ry)+24;
 svg.setAttribute('viewBox',[x,y,x2-x,y2-y].join(' '));
}
async function load(){try{const r=await fetch('/state?map='+key+'&regions='+(document.querySelector('#regions').checked?'all':'selected'));current=await r.json();if(!r.ok)throw Error(current.error);host.emit('state',current.state);Vue.nextTick(()=>requestAnimationFrame(draw));}catch(e){document.querySelector('#error').textContent=e.message}}
host.on('fetchState',load);document.querySelector('#map').onchange=e=>{params.set('map',e.target.value);location.search=params;};
document.querySelector('#style').onchange=e=>{mode=e.target.value;params.set('style',mode);history.replaceState(null,'','?'+params);draw();};
document.querySelector('#regions').onchange=e=>{params.set('regions',e.target.checked?'all':'selected');history.replaceState(null,'','?'+params);load();};
document.querySelector('#full').onclick=e=>{full=!full;document.body.classList.toggle('full',full);e.target.textContent=full?'Map only':'Full board';};
document.querySelector('#theme').onclick=e=>{dark=!dark;document.body.classList.toggle('light',!dark);host.emit('theme',{dark});e.target.textContent=dark?'Light mode':'Dark mode';};load();
</script></body></html>`;

export function geographicPreviewServer() {
    return createServer(async (req, res) => {
        try {
            const url = new URL(req.url, 'http://localhost');
            res.setHeader('Cache-Control', 'no-store');
            if (url.pathname === '/') { res.setHeader('Content-Type', 'text/html'); return res.end(html); }
            if (url.pathname === '/state') {
                const key = url.searchParams.get('map') || 'germany';
                const state = geographicPreviewState(key, url.searchParams.get('regions') !== 'selected');
                res.setHeader('Content-Type', 'application/json');
                return res.end(JSON.stringify({ state, outline: geometry[key], ratio: state.map.adjustRatio }));
            }
            if (url.pathname === '/vue.js' || /^\/powergrid-viewer[\w.-]*\.(css|js)$/.test(url.pathname)) {
                res.setHeader('Content-Type', url.pathname.endsWith('.css') ? 'text/css' : 'text/javascript');
                return res.end(await readFile(url.pathname === '/vue.js' ? require.resolve('vue/dist/vue.min.js') : fileURLToPath(new URL('../dist' + url.pathname, import.meta.url))));
            }
            res.writeHead(404); res.end();
        } catch (error) { res.writeHead(422, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: error.message })); }
    });
}
if (process.argv[1] === fileURLToPath(import.meta.url)) geographicPreviewServer().listen(Number(process.env.PORT || 5209), '127.0.0.1', () => console.log('Geographic preview: http://127.0.0.1:' + (process.env.PORT || 5209)));
