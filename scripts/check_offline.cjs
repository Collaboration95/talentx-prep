/* Exercise the real generated worker with Cache/Fetch stand-ins. No dependencies. */
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const {webcrypto} = require('node:crypto');
const root = path.resolve(__dirname, '..');
const scope = 'https://example.test/talentx-prep/';
const handlers = {};
const stores = new Map();
let online = true;
const key = input => new URL(typeof input === 'string' ? input : input.url, scope).href;
const readResponse = async input => {
  if (!online) throw Error('Simulated offline');
  const url = new URL(key(input));
  let relative = decodeURIComponent(url.pathname).slice('/talentx-prep/'.length);
  if (!relative) relative = 'index.html';
  const filename = path.join(root, relative);
  return fs.existsSync(filename) ? new Response(fs.readFileSync(filename), {status:200}) : new Response('missing', {status:404});
};
class TestCache {
  constructor() { this.items = new Map(); }
  async match(request) { return this.items.get(key(request))?.clone(); }
  async put(request, response) { this.items.set(key(request), response.clone()); }
  async keys() { return [...this.items.keys()].map(url => new Request(url)); }
  async addAll(urls) { for (const url of urls) await this.put(url, await readResponse(url)); }
}
const caches = {
  async open(name) {if (!stores.has(name)) stores.set(name, new TestCache()); return stores.get(name);},
  async keys() {return [...stores.keys()];},
  async delete(name) {return stores.delete(name);}
};
const context = {URL, Request, Response, Uint8Array, crypto:webcrypto, fetch:readResponse, caches,
  location:{origin:'https://example.test'}, self:{registration:{scope},clients:{claim:async()=>{}},skipWaiting:async()=>{},
    addEventListener:(name,handler)=>handlers[name]=handler}};
vm.runInNewContext(fs.readFileSync(path.join(root, 'sw.js'), 'utf8'),context);
async function lifecycle(name) {let pending; handlers[name]({waitUntil:p=>pending=p}); await pending;}
async function workerFetch(relative, mode='cors') {
  const request={url:key(relative),method:'GET',mode};
  let pending;
  handlers.fetch({request,respondWith:p=>pending=p});
  assert.ok(pending, 'Worker must handle a same-project request');
  return pending;
}
(async()=>{
  const previous=await caches.open('talentx-previous');
  await previous.put('resumes/ailytics.pdf',await readResponse('resumes/ailytics.pdf'));
  await previous.put('resumes/rezonate.pdf',new Response('superseded resume'));
  await lifecycle('install');
  await lifecycle('activate');
  assert.equal(stores.has('talentx-previous'),false,'Old cache is removed after migration');
  online=false;
  for (const file of ['index.html','assets/fonts/kalam-bold.ttf','resumes/ailytics.pdf','resumes/rezonate.pdf']) {
    const response=await workerFetch(file);
    assert.equal(response.status,200,file+' available offline');
    assert.deepEqual(Buffer.from(await response.arrayBuffer()),fs.readFileSync(path.join(root,file)),file+' is the current exact file');
  }
  const missing=await workerFetch('not-saved.pdf');
  assert.equal(missing.status,503,'A missing PDF must never return the HTML shell');
  const shell=await workerFetch('deep-route','navigate');
  assert.equal(shell.status,200,'Offline app navigation can use the shell');
  let intercepted=false;
  handlers.fetch({request:{url:'https://example.test/unrelated/',method:'GET'},respondWith:()=>intercepted=true});
  assert.equal(intercepted,false,'Worker is scoped to the companion');
  console.log('PASS: offline shell/fonts/PDFs; cache migration; superseded-PDF replacement; missing-file and scope boundaries');
})().catch(error=>{console.error(error);process.exitCode=1;});
