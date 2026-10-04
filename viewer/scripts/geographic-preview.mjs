// Local preview of the geographic background, using the built viewer.
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
const require = createRequire(import.meta.url);
const engine = require('../../engine/dist/index.js');
const wrapper = require('../../engine/dist/wrapper.js');
const mapKeys = Object.values(JSON.parse(await readFile(new URL('../src/geography/names.json', import.meta.url))));
const geometry = Object.fromEntries(await Promise.all(mapKeys.map(async key => [key, JSON.parse(await readFile(new URL('../src/geography/assets/' + key + '.json', import.meta.url)))])));
const maps = Object.fromEntries(Object.keys(geometry).map(key => [key, require(`../../engine/dist/src/maps/${key}.js`)]));

export function geographicPreviewState(key = 'germany', allRegions = true, variant = 'original', playerCount = 3) {
    const authored = variant === 'recharged' ? maps[key]?.mapRecharged || maps[key]?.map : maps[key]?.map;
    if (!authored) throw Error('Unknown preview map');
    const state = engine.setup(playerCount, { map: authored.name, variant, showMoney: true }, 'outline-preview');
    if (allRegions) {
        const [rx, ry] = state.map.adjustRatio;
        state.map.cities = authored.cities.map((city) => ({ ...city, x: city.x * rx, y: city.y * ry }));
        state.map.connections = JSON.parse(JSON.stringify(authored.connections));
    }
    state.players.forEach((player, i) => {
        player.name = ['You', 'Nora', 'Leo', 'Jules', 'Mia', 'Sam'][i];
        player.availableMoves = {};
    });
    state.currentPlayers = [];
    return wrapper.stripSecret(state, 0);
}

const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Powergrid · Geographic outlines</title><link rel="stylesheet" href="/powergrid-viewer.css"><style>
*{box-sizing:border-box}body{margin:0;background:#171717;color:#e8ece7;font:14px/1.4 system-ui}header{padding:14px 20px;border-bottom:1px solid #3e493e;display:flex;align-items:center;gap:18px;flex-wrap:wrap}header strong{margin-right:auto}header small{font-weight:400;color:#aeb9ad}label{display:flex;align-items:center;gap:7px}select,button{font:inherit;background:#263027;color:inherit;border:1px solid #63715f;border-radius:5px;padding:7px 10px}button{cursor:pointer}main{max-width:none;margin:auto;padding:16px}#map-only{width:100%;height:calc(100vh - 160px);min-height:380px;background:yellowgreen;border-radius:5px}#app{position:absolute;left:-20000px;width:1300px;visibility:hidden}body.full #app{position:static;left:auto;width:auto;visibility:visible}body.full #map-only{display:none}footer{padding:10px 0;color:#b7c2b2;font-size:12px}footer a{color:inherit}body.light{background:#e7ebda;color:#1d2a1d}body.light header{border-color:#a6b297}body.light select,body.light button{background:#f0f2e9;color:#1d2a1d}body.light small,body.light footer{color:#4c6043}#error{color:#ffaba0}svg .geographic-backdrop{pointer-events:none}@media(max-width:600px){header{padding:12px;gap:10px}header strong{width:100%}main{padding:10px}#map-only{height:calc(100vh - 240px)}}
</style></head><body><header><strong>Geographic outlines <small>Local preview</small></strong><label>Map <select id="map">${Object.entries(geometry).map(([key,map]) => '<option value="'+key+'">'+map.name.replaceAll('&','&amp;')+'</option>').join('')}</select></label><label>Backdrop <select id="style"><option value="terrain">Blue water + green land</option><option value="wash">Soft land + outline</option><option value="line">Outline only</option><option value="none">Off</option></select></label><label>Rules <select id="variant"><option value="original">Original</option><option value="recharged">Recharged</option></select></label><label><input type="checkbox" id="regions" checked> All regions</label><button id="full">Full board</button><button id="theme">Light mode</button></header><main><svg id="map-only" role="img" aria-label="Geographic outline behind the Power Grid network"></svg><div id="app"></div><div id="error" role="alert"></div><footer>Existing cities and links, with a fitted geographic backdrop. Hover a city for its name. <a href="https://www.naturalearthdata.com/about/terms-of-use/">Natural Earth</a> · <a href="https://www.geonames.org/">GeoNames (CC BY 4.0)</a> · <a href="https://data.cityofnewyork.us/d/gthc-hcne">NYC Open Data</a>. Local visual experiment; full-region view is illustrative.</footer></main><script src="/vue.js"></script><script src="/powergrid-viewer.umd.min.js"></script><script>
const params=new URLSearchParams(location.search), key=params.get('map')||'germany';let mode=params.get('style')||'terrain',dark=true,full=params.get('view')==='full',current;
document.querySelector('#variant').value=params.get('variant')||'original';document.querySelector('#map').value=key;document.querySelector('#style').value=mode;document.querySelector('#regions').checked=params.get('regions')!=='selected';
document.body.classList.toggle('full',full);document.querySelector('#full').textContent=full?'Map only':'Full board';
const host=window.host=powergrid.launch('#app');host.emit('player',{index:params.get('fixture')==='live'?-1:0});host.emit('theme',{dark});host.emit('preferences',{sound:false,locale:params.get('locale')||'en',fitToScreen:params.get('fit')==='true',stackOnPortrait:true,geographicBackground:mode,showUnselectedRegions:params.has('context')?params.get('context')==='true':JSON.parse(localStorage.getItem('powergrid-preview-showUnselectedRegions')||'true')});host.on('update:preference',p=>{localStorage.setItem('powergrid-preview-'+p.name,JSON.stringify(p.value));Vue.nextTick(()=>requestAnimationFrame(draw));});
host.emit('chat:state',{canSend:false,mentions:[]});host.emit('avatars',Array(3).fill('data:image/svg+xml,'+encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30"><circle cx="15" cy="15" r="15" fill="#bbc9ae"/></svg>')));
const ns='http://www.w3.org/2000/svg';
function draw(){
 const slot=document.querySelector('#app [data-tutorial="map"]');if(!slot||!slot.firstElementChild||!current)return;
 const group=slot.firstElementChild,svg=document.querySelector('#map-only');
 const box=group.getBBox(); // Measure the original network before adding any decoration.
 svg.replaceChildren(group.cloneNode(true));svg.firstElementChild.removeAttribute('transform');
 const background=document.querySelector('#app [data-geography-map]');
 if(background){const copy=background.cloneNode(true);const clip=copy.querySelector('clipPath'), clipped=copy.querySelector('[data-geography-content]');clip.id+='-preview';clipped.setAttribute('clip-path','url(#'+clip.id+')');svg.insertBefore(copy,svg.firstChild);}
 const inactive=document.querySelector('#app [data-unselected-regions]');
 if(inactive)svg.insertBefore(inactive.cloneNode(true),svg.lastChild);
 svg.style.background=mode==='terrain'?'#263027':'yellowgreen';
 svg.setAttribute('viewBox',[box.x-24,box.y-24,box.width+48,box.height+48].join(' '));
}
async function load(){try{const r=await fetch('/state?fixture='+(params.get('fixture')||'')+'&players='+(params.get('players')||'3')+'&map='+key+'&variant='+document.querySelector('#variant').value+'&regions='+(document.querySelector('#regions').checked?'all':'selected'));current=await r.json();if(!r.ok)throw Error(current.error);host.emit('state',current.state);Vue.nextTick(()=>requestAnimationFrame(()=>requestAnimationFrame(draw)));}catch(e){document.querySelector('#error').textContent=e.message}}
// A cold load can finish its optional geography chunk after the first draw.
new MutationObserver(()=>requestAnimationFrame(draw)).observe(document.querySelector('#app'),{childList:true,subtree:true});
host.on('fetchState',load);document.querySelector('#map').onchange=e=>{params.set('map',e.target.value);params.delete('fixture');location.search=params;};
document.querySelector('#variant').onchange=e=>{params.set('variant',e.target.value);history.replaceState(null,'','?'+params);load();};
document.querySelector('#style').onchange=e=>{mode=e.target.value;params.set('style',mode);history.replaceState(null,'','?'+params);host.emit('preferences',{geographicBackground:mode});Vue.nextTick(()=>requestAnimationFrame(draw));};
document.querySelector('#regions').onchange=e=>{params.set('regions',e.target.checked?'all':'selected');history.replaceState(null,'','?'+params);load();};
document.querySelector('#full').onclick=e=>{full=!full;params.set('view',full?'full':'map');location.search=params;};
document.querySelector('#theme').onclick=e=>{dark=!dark;document.body.classList.toggle('light',!dark);host.emit('theme',{dark});e.target.textContent=dark?'Light mode':'Dark mode';};load();
</script></body></html>`;

// Compact asset review: all authored spaces and connections, without game UI.
function gallery(page, fullBoard = false) {
    const cards=Object.entries(geometry).slice(page*6,page*6+6).map(([key, geo])=>{
        const map=maps[key].map, [rx,ry]=map.adjustRatio || [1,1];
        const xs=map.cities.map(c=>c.x*rx),ys=map.cities.map(c=>c.y*ry);
        const x=Math.min(...xs)-30,y=Math.min(...ys)-30,w=Math.max(...xs)-x+30,h=Math.max(...ys)-y+30;
        const scene=engine.setup(3,{map:map.name,variant:'original'},'gallery').map;
        const cx=(Math.min(...xs)+Math.max(...xs))/2,cy=(Math.min(...ys)+Math.max(...ys))/2;
        const framing=fullBoard?[0,0,...scene.viewBox]:[x,y,w,h];
        const transform=fullBoard?'translate('+scene.mapPosition.join(',')+') rotate('+(map.mapRotation||0)+','+cx+','+cy+')':'';
        const point=Object.fromEntries(map.cities.map(c=>[c.name,c]));
        const paths=(data,fill,stroke)=>data.map(d=>'<path d="'+d+'" fill="'+fill+'" stroke="'+stroke+'" stroke-width="'+1/Math.max(rx,ry)+'"/>').join('');
        const links=map.connections.map(c=>{const [a,b]=c.nodes.map(n=>point[n]);return '<line x1="'+a.x+'" y1="'+a.y+'" x2="'+b.x+'" y2="'+b.y+'" stroke="#647063" stroke-width="'+3/Math.max(rx,ry)+'"/>'}).join('');
        const cities=map.cities.map(c=>'<circle cx="'+c.x+'" cy="'+c.y+'" r="'+5/Math.max(rx,ry)+'" fill="'+c.region+'" stroke="#222" stroke-width="'+1/Math.max(rx,ry)+'"><title>'+c.name+'</title></circle>').join('');
        return '<article><a href="/?map='+key+'&style=terrain&view=full">'+geo.name+'</a><svg viewBox="'+framing.join(' ')+'"><g transform="'+transform+'"><g transform="scale('+rx+','+ry+')" fill-rule="evenodd">'+paths(geo.context,'#91b374','none')+paths(geo.land,'#bfd58c','#526b39')+links+cities+'</g></g></svg></article>';
    }).join('');
    return '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>All maps · geographic review</title><style>body{margin:16px;background:#171717;color:#eee;font:16px system-ui}nav{margin-bottom:12px}a{color:inherit;padding:8px}main{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}article{min-width:0}svg{display:block;width:100%;height:auto;background:#96bcc5;margin-top:8px}article>a{display:block}</style><nav>'+[0,1,2,3].map(i=>'<a href="/gallery?page='+i+'&view='+(fullBoard?'full':'map')+'">Maps '+(i*6+1)+'–'+(i*6+6)+'</a>').join('')+'</nav><main>'+cards+'</main>';
}

export function geographicPreviewServer() {
    return createServer(async (req, res) => {
        try {
            const url = new URL(req.url, 'http://localhost');
            res.setHeader('Cache-Control', 'no-store');
            if (url.pathname === '/gallery') { res.setHeader('Content-Type', 'text/html'); return res.end(gallery(Math.max(0, Math.min(3, Number(url.searchParams.get('page')) || 0)),url.searchParams.get('view')==='full')); }
            if (url.pathname === '/') { res.setHeader('Content-Type', 'text/html'); return res.end(html); }
            if (url.pathname === '/state') {
                const key = url.searchParams.get('map') || 'germany';
                const state = url.searchParams.get('fixture') === 'live' && process.env.PREVIEW_STATE
                    ? JSON.parse(await readFile(process.env.PREVIEW_STATE, 'utf8'))
                    : geographicPreviewState(key, url.searchParams.get('regions') !== 'selected', url.searchParams.get('variant') || 'original', Math.min(6, Math.max(2, Number(url.searchParams.get('players')) || 3)));
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
