'use strict';
// Synthetic hosts ONLY for transport fault injection. Passing these tests is NOT
// BGS host conformance; conformance.cjs separately pins the actual staged host.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { pathToFileURL } = require('node:url');
const { HostClient, openHost, LIMITS } = require('./host_client.cjs');

const SCRIPT = `
const readline = require('node:readline');
const prefix = '\\x1ebgs-engine ';
const methods = ['echo', 'inspect', 'hang', 'remote', 'noise', 'unknown', 'duplicate', 'malformed', 'twice', 'bigline', 'bigvalue', 'exit'];
const send = value => process.stdout.write(prefix + JSON.stringify(value) + '\\n');
const ready = () => send({ready: true, methods, constants: { marker: 7 }});
const lines = readline.createInterface({input: process.stdin});
lines.on('line', line => {
    const r = JSON.parse(line);
    const reply = value => send({id:r.id,ok:true,value});
    switch (r.method) {
        case 'echo': setTimeout(() => reply(r.args[0]), r.args[1] || 0); break;
        case 'inspect': reply({argv:process.argv.slice(1), execArgv:process.execArgv, cwd:process.cwd(), env:process.env}); break;
        case 'hang': break;
        case 'remote': send({id:r.id,ok:false,error:'PRIVATE_STATE_AND_SECRET',name:'PRIVATE_ERROR_NAME'}); break;
        case 'noise': process.stderr.write('PRIVATE_STATE_AND_SECRET'); process.stdout.write('private log\\n'); reply(9); break;
        case 'unknown': send({id:99999,ok:true,value:1}); break;
        case 'duplicate': reply(1); setTimeout(() => reply(2), 10); break;
        case 'malformed': process.stdout.write(prefix + '{private invalid json\\n'); break;
        case 'twice': ready(); break;
        case 'bigline': process.stdout.write('x'.repeat(2000)); break;
        case 'bigvalue': reply('x'.repeat(200)); break;
        case 'exit': process.exit(0);
    }
});
lines.on('close', () => process.exit(0));
ready();
`;
function fixture(t, options = {}, script = SCRIPT) {
    const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'pg-host-client-'));
    const hostFile = path.join(directory, 'host.cjs');
    const entryPoint = path.join(directory, 'entry with # and space.mjs');
    fs.writeFileSync(hostFile, script);
    fs.writeFileSync(entryPoint, 'export const unused = true;\n');
    const settings = { node: process.execPath, hostFile, entryPoint, readyTimeoutMs: 3000, ...options };
    const client = new HostClient(settings);
    t.after(async () => {
        await client.close().catch(() => {});
        fs.rmSync(directory, { recursive: true, force: true });
    });
    return { client, settings };
}
const code = (expected) => (error) => {
    assert.equal(error.name, 'HostClientError');
    assert.equal(error.code, expected);
    assert.equal(error.message, expected);
    assert(!error.stack.includes('PRIVATE_'));
    return true;
};

test('explicit executable/host/entry, 400 MiB old-space, slash cwd, no inherited credentials or NODE_OPTIONS', async (t) => {
    const previous = process.env.PG_HOST_CLIENT_TEST_SECRET;
    process.env.PG_HOST_CLIENT_TEST_SECRET = 'PRIVATE_TEST_TOKEN';
    t.after(() => {
        if (previous === undefined) delete process.env.PG_HOST_CLIENT_TEST_SECRET;
        else process.env.PG_HOST_CLIENT_TEST_SECRET = previous;
    });
    let invocation;
    const { client, settings } = fixture(t, {
        spawnProcess(node, args, options) {
            invocation = { node, args, options };
            return spawn(node, args, options);
        },
    });
    const metadata = await client.ready;
    assert(metadata.methods.includes('echo'));
    assert.deepEqual(metadata.constants, { marker: 7 });
    const actual = await client.call('inspect');
    assert.equal(invocation.node, process.execPath);
    assert.deepEqual(invocation.args, [
        '--max-old-space-size=400',
        settings.hostFile,
        pathToFileURL(settings.entryPoint).href,
    ]);
    assert.deepEqual(invocation.options, { cwd: '/', env: {}, stdio: ['pipe', 'pipe', 'pipe'], shell: false });
    assert.equal(actual.cwd, '/');
    assert.deepEqual(actual.env, {});
    assert.deepEqual(actual.execArgv, ['--max-old-space-size=400']);
    assert.equal(actual.argv[1], pathToFileURL(settings.entryPoint).href);
    assert(Number.isInteger(client.pid));
    assert(client.metrics.readyMs >= 0);
});

test('concurrent out-of-order replies are correlated; EOF waits for every reply, then exit', async (t) => {
    const { client } = fixture(t);
    await client.ready;
    const order = [];
    const calls = [80, 5, 30, 1].map((delay, i) =>
        client.call('echo', [{ game: i }, delay]).then((v) => {
            order.push(i);
            return v;
        })
    );
    // close must drain even calls accepted in this same tick, before their await-ready resumes.
    const closing = client.close();
    assert.deepEqual(await Promise.all(calls), [{ game: 0 }, { game: 1 }, { game: 2 }, { game: 3 }]);
    assert.notDeepEqual(order, [0, 1, 2, 3]);
    assert.deepEqual(await closing, { code: 0, signal: null });
    assert.equal(client.metrics.replies, 4);
    assert.equal(client.metrics.pending, 0);
    assert.equal(client.close(), closing);
    await assert.rejects(client.call('echo', []), code('host-closed'));
});

test('arguments detach before ready; fragmented UTF-8 ready/data frames and undefined result', async (t) => {
    const script = `
const rl = require('node:readline').createInterface({input:process.stdin});
const frame = value => Buffer.from('\\x1ebgs-engine ' + JSON.stringify(value) + '\\n');
const split = value => { const b=frame(value); for(let i=0;i<b.length;i++) process.stdout.write(b.subarray(i,i+1)); };
rl.on('line', raw => { const r=JSON.parse(raw); split({id:r.id,ok:true,value:r.args[0]}); });
rl.on('close',()=>process.exit(0));
setTimeout(()=>split({ready:true,methods:['echo'],constants:{text:'é😀'}}),40);
`;
    const { client } = fixture(t, {}, script);
    const state = { text: 'é😀', nested: { value: 1 } };
    const call = client.call('echo', [state]);
    state.nested.value = 2;
    assert.deepEqual(await call, { text: 'é😀', nested: { value: 1 } });
    assert.equal((await client.ready).constants.text, 'é😀');
    assert.equal(await client.call('echo'), undefined);
});

test('close before ready still drains an already-accepted call before host EOF', async (t) => {
    const { client } = fixture(t, {}, SCRIPT.replace('ready();\n', 'setTimeout(ready, 40);\n'));
    const call = client.call('echo', [7, 20]);
    const closing = client.close();
    assert.equal(await call, 7);
    assert.deepEqual(await closing, { code: 0, signal: null });
});

test('remote errors are sanitized and per-call; arbitrary stdout/stderr never retained', async (t) => {
    const { client } = fixture(t);
    await client.ready;
    await assert.rejects(client.call('remote'), code('host-remote-error'));
    assert.equal(await client.call('noise'), 9);
    assert.equal(await client.call('echo', [3]), 3);
    assert(client.metrics.stderrBytes > 0);
    assert.equal(client.metrics.ignoredStdoutLines, 1);
    assert.equal(client.metrics.remoteErrors, 1);
    assert(!JSON.stringify(client.metrics).includes('PRIVATE_'));
});

test('one timed-out call kills child and rejects all pending without retry', async (t) => {
    const { client } = fixture(t, { callTimeoutMs: 40 });
    await client.ready;
    const a = assert.rejects(client.call('hang'), code('host-call-timeout'));
    const b = assert.rejects(client.call('echo', [1, 500]), code('host-call-timeout'));
    await Promise.all([a, b]);
    const exit = await client.close();
    assert.equal(exit.signal, 'SIGKILL');
    assert.equal(client.metrics.callsSent, 2);
    await assert.rejects(client.call('echo'), code('host-call-timeout'));
});

for (const [method, expected] of [
    ['unknown', 'host-unknown-response'],
    ['malformed', 'host-protocol'],
    ['twice', 'host-protocol'],
    ['exit', 'host-exit'],
])
    test(`${method}: protocol/process failure poisons all calls`, async (t) => {
        const { client } = fixture(t);
        await client.ready;
        await Promise.all([
            assert.rejects(client.call(method), code(expected)),
            assert.rejects(client.call('hang'), code(expected)),
        ]);
        await client.close();
        assert.equal(client.metrics.pending, 0);
    });

test('a duplicated response is fatal, even after its original call has resolved', async (t) => {
    const { client } = fixture(t);
    await client.ready;
    const pending = assert.rejects(client.call('hang'), code('host-unknown-response'));
    assert.equal(await client.call('duplicate'), 1);
    await pending;
});

test('ready is bounded independently of calls', async (t) => {
    const { client } = fixture(t, { readyTimeoutMs: 40 }, 'setInterval(()=>{},1000);');
    await assert.rejects(client.ready, code('host-ready-timeout'));
    assert.equal((await client.close()).signal, 'SIGKILL');
});

test('close waits for actual exit and kills a host ignoring EOF within its bound', async (t) => {
    const { client } = fixture(
        t,
        { closeTimeoutMs: 40 },
        `
process.stdout.write('\\x1ebgs-engine '+JSON.stringify({ready:true,methods:[],constants:{}})+'\\n');
process.stdin.resume(); setInterval(()=>{},1000);
`
    );
    await client.ready;
    await assert.rejects(client.close(), code('host-close-timeout'));
    assert.equal((await client.exited).signal, 'SIGKILL');
});

test('output line limit applies before newline, even to non-protocol logging', async (t) => {
    const { client } = fixture(t, { maxLineBytes: 1024 });
    await client.ready;
    await assert.rejects(client.call('bigline'), code('host-line-limit'));
});

test('JSON request and response limits; oversize local input does not poison valid calls', async (t) => {
    const { client } = fixture(t, { maxStateBytes: 128 });
    await client.ready;
    await assert.rejects(client.call('echo', ['x'.repeat(200)]), code('host-state-limit'));
    assert.equal(client.metrics.callsSent, 0);
    assert.equal(await client.call('echo', [1]), 1);
    await assert.rejects(client.call('bigvalue'), code('host-state-limit'));
});

test('bounded arguments/method admission and no implicit executable/environment defaults', async (t) => {
    for (const options of [
        null,
        [],
        {},
        { node: process.execPath, hostFile: 'relative', entryPoint: '/tmp/a' },
        { node: process.execPath, hostFile: '/tmp/h', entryPoint: '/tmp/a', env: process.env },
        { node: process.execPath, hostFile: '/tmp/h', entryPoint: '/tmp/a', callTimeoutMs: LIMITS.callMs + 1 },
    ]) {
        assert.throws(() => new HostClient(options), code('host-config'));
    }
    const { client } = fixture(t);
    await client.ready;
    await assert.rejects(client.call('notExported'), code('host-unknown-method'));
    await assert.rejects(client.call('echo', {}), code('host-call-arguments'));
    const circular = [];
    circular.push(circular);
    await assert.rejects(client.call('echo', circular), code('host-call-arguments'));
    assert.equal(client.metrics.callsSent, 0);
});

test('spawn failures sanitized, including executable path; openHost cleans failed startup', async () => {
    await assert.rejects(
        openHost({ node: '/missing/PRIVATE_SECRET/node', hostFile: '/missing/h', entryPoint: '/missing/e' }),
        code('host-spawn')
    );
});
