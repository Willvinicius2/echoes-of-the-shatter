// Uso: node gerar_pranchas.mjs <pasta com os .glb> <pasta de saída> [objeto ...]
// Ex.: node gerar_pranchas.mjs ../../../godot/art/models /mnt/project-files/pranchas-cripta estandarte velas estatua
// Sem objetos na lista, gera todos. Objeto = nome sem o prefixo SM_Cripta_ e sem .glb, em minúsculas.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const aqui = path.dirname(fileURLToPath(import.meta.url));
const [glbDir, outDir, ...filtro] = process.argv.slice(2);
if (!glbDir || !outDir) { console.error('uso: node gerar_pranchas.mjs <glbDir> <outDir> [objeto ...]'); process.exit(2); }
fs.mkdirSync(outDir, { recursive: true });

const norm = s => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const arquivos = fs.readdirSync(glbDir).filter(f => /^SM_Cripta_.*\.glb$/.test(f))
  .map(f => ({ f, id: norm(f.replace(/^SM_Cripta_/, '').replace(/\.glb$/, '')) }))
  .filter(o => !filtro.length || filtro.map(norm).includes(o.id));

const tipos = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.glb': 'model/gltf-binary', '.json': 'application/json' };
const server = http.createServer((req, res) => {
  const u = decodeURIComponent(req.url.split('?')[0]);
  const p = u.startsWith('/glb/') ? path.join(glbDir, u.slice(5)) : path.join(aqui, u === '/' ? 'render.html' : u);
  if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': tipos[path.extname(p)] || 'application/octet-stream' });
  fs.createReadStream(p).pipe(res);
}).listen(0);
const porta = server.address().port;

const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: 480, height: 480 } });
page.on('console', m => { if (m.type() === 'error') console.error('[pagina]', m.text()); });
await page.goto(`http://127.0.0.1:${porta}/`);
await page.waitForFunction('window.ready === true', null, { timeout: 30000 });

for (const { f, id } of arquivos) {
  const nome = id.replace(/_/g, ' ').replace(/^./, c => c.toUpperCase());
  const t0 = Date.now();
  const dataUrl = await page.evaluate(([u, n]) => window.makeSheet(u, n), [`/glb/${f}`, nome]);
  const destino = path.join(outDir, `${id}.png`);
  fs.writeFileSync(destino, Buffer.from(dataUrl.split(',')[1], 'base64'));
  console.log(`${destino}  (${((Date.now() - t0) / 1000).toFixed(1)} s)`);
}
await browser.close();
server.close();
