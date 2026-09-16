import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const files = {
    '/bundle.js': fileURLToPath(new URL('../dist/powergrid-viewer.umd.min.js', import.meta.url)),
    '/bundle.css': fileURLToPath(new URL('../dist/powergrid-viewer.css', import.meta.url)),
    '/vue.js': require.resolve('vue/dist/vue.min.js'),
};
const html = `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Powergrid tutorials</title><link rel="stylesheet" href="/bundle.css"><style>body{margin:0;background:#f0f1e9}</style></head><body><div id="app"></div><script src="/vue.js"></script><script src="/bundle.js"></script><script>
const chapters=['auctions','resources','network','income','upgrades','steps','final-round'];
const chapter=new URL(location.href).searchParams.get('chapter')||chapters[0];
const index=chapters.indexOf(chapter);
powergrid.launchTutorial('#app',{chapter,onProgress:progress=>window.progress=progress,nextChapter:index<chapters.length-1?{id:chapters[index+1],title:'Next chapter',open:()=>location.search='?chapter='+chapters[index+1]}:undefined});
</script></body></html>`;
export function previewServer() {
    return createServer(async (req, res) => {
        const path = new URL(req.url, 'http://localhost').pathname;
        try {
            const file = files[path];
            if (path !== '/' && !file) {
                res.writeHead(404).end();
                return;
            }
            res.writeHead(200, {
                'access-control-allow-origin': '*',
                'cache-control': 'no-store',
                'content-type': path === '/' ? 'text/html' : path.endsWith('.css') ? 'text/css' : 'text/javascript',
            });
            res.end(file ? await readFile(file) : html);
        } catch (error) {
            res.writeHead(500).end(String(error));
        }
    });
}
if (process.argv[1] === fileURLToPath(import.meta.url)) {
    const port = Number(process.env.PORT || 5199);
    previewServer().listen(port, '127.0.0.1', () => console.log(`Tutorial preview: http://127.0.0.1:${port}`));
}
