'use strict';
// Credential-free HF admission probe. No models, downloads, servers or game execution.
const fs = require('node:fs');
const { spawnSync } = require('node:child_process');
const read = (file) => {
    try {
        return fs.readFileSync(file, 'utf8').trim();
    } catch (_) {
        return null;
    }
};
const limits = {};
for (const name of [
    'cpu.max',
    'memory.max',
    'memory.swap.max',
    'pids.max',
    'cgroup.controllers',
    'cgroup.subtree_control',
])
    limits[name] = read('/sys/fs/cgroup/' + name);
const status = read('/proc/self/status') || '';
const security = Object.fromEntries(
    status
        .split('\n')
        .filter((x) => /^(CapEff|NoNewPrivs|Seccomp):/.test(x))
        .map((x) => x.split(/:\s*/))
);
const namespaceProbe = spawnSync(
    'unshare',
    ['--user', '--map-root-user', '--mount', '--net', '--pid', '--fork', 'true'],
    { timeout: 5000, encoding: 'utf8' }
);
let delegated = false,
    cgroupError = null;
const child = '/sys/fs/cgroup/pg-bgs-admission-' + process.pid;
try {
    fs.mkdirSync(child);
    try {
        for (const [file, value] of Object.entries({
            'memory.max': '536870912',
            'memory.swap.max': '0',
            'cpu.max': '100000 100000',
            'pids.max': '64',
        })) {
            fs.writeFileSync(child + '/' + file, value);
            if (read(child + '/' + file) !== value) throw Error('controller-mismatch');
        }
        delegated = true;
    } finally {
        fs.rmdirSync(child);
    }
} catch (error) {
    cgroupError = error.code || 'controller-unavailable';
}
const report = {
    schema: 'pg-bgs-container-admission-v1',
    node: process.version,
    platform: process.platform,
    arch: process.arch,
    os: (read('/etc/os-release') || '').split('\n').filter((x) => /^(ID|VERSION_ID)=/.test(x)),
    security,
    outerLimits: limits,
    namespace: {
        executableAvailable: namespaceProbe.error?.code !== 'ENOENT',
        success: namespaceProbe.status === 0,
        exitCode: namespaceProbe.status,
        errorCode: namespaceProbe.error?.code || null,
    },
    delegatedChildControllers: delegated,
    cgroupError,
    nestedContainerPossible: namespaceProbe.status === 0 && delegated,
    productionSandboxValidated: false,
    modelsLoaded: false,
    networkExposed: false,
};
console.log(JSON.stringify(report));
// A report of denied isolation is a successful admission measurement, not a serving qualification.
