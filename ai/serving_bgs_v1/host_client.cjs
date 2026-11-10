'use strict';
// Generic client for the unchanged BGS engine host. No platform implementation,
// models, credentials, host revision/CAS emulation, retries or persistence here.
const { spawn } = require('node:child_process');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { performance } = require('node:perf_hooks');

const PREFIX = '\x1ebgs-engine ';
const LIMITS = Object.freeze({
    readyMs: 20000,
    callMs: 10000,
    closeMs: 10000,
    lineBytes: 16 * 1024 * 1024,
    stateBytes: 8 * 1024 * 1024,
    pending: 64,
});
const CODES = new Set([
    'host-config',
    'host-spawn',
    'host-ready-timeout',
    'host-call-timeout',
    'host-close-timeout',
    'host-closed',
    'host-exit',
    'host-io',
    'host-line-limit',
    'host-state-limit',
    'host-protocol',
    'host-unknown-response',
    'host-remote-error',
    'host-call-arguments',
    'host-unknown-method',
    'host-busy',
]);
class HostClientError extends Error {
    constructor(code) {
        super(CODES.has(code) ? code : 'host-protocol');
        this.name = 'HostClientError';
        this.code = this.message;
    }
}
const fail = (code) => new HostClientError(code);
const object = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);
function absolute(v) {
    return typeof v === 'string' && path.isAbsolute(v) && !v.includes('\0');
}
function bounded(value, maximum) {
    return Number.isSafeInteger(value) && value >= 1 && value <= maximum;
}

class HostClient {
    constructor(options = {}) {
        if (!object(options)) throw fail('host-config');
        const {
            node,
            hostFile,
            entryPoint,
            readyTimeoutMs = LIMITS.readyMs,
            callTimeoutMs = LIMITS.callMs,
            closeTimeoutMs = LIMITS.closeMs,
            maxLineBytes = LIMITS.lineBytes,
            maxStateBytes = LIMITS.stateBytes,
            spawnProcess = spawn,
        } = options;
        if (
            ![node, hostFile, entryPoint].every(absolute) ||
            typeof spawnProcess !== 'function' ||
            !bounded(readyTimeoutMs, LIMITS.readyMs) ||
            !bounded(callTimeoutMs, LIMITS.callMs) ||
            !bounded(closeTimeoutMs, LIMITS.closeMs) ||
            !bounded(maxLineBytes, LIMITS.lineBytes) ||
            !bounded(maxStateBytes, LIMITS.stateBytes) ||
            Object.keys(options).some(
                (k) =>
                    ![
                        'node',
                        'hostFile',
                        'entryPoint',
                        'readyTimeoutMs',
                        'callTimeoutMs',
                        'closeTimeoutMs',
                        'maxLineBytes',
                        'maxStateBytes',
                        'spawnProcess',
                    ].includes(k)
            )
        )
            throw fail('host-config');
        this._limits = { readyTimeoutMs, callTimeoutMs, closeTimeoutMs, maxLineBytes, maxStateBytes };
        this._pending = new Map();
        this._admitted = 0; // Calls accepted before ready/close, not yet written.
        this._sequence = 0;
        this._chunks = [];
        this._lineBytes = 0;
        this._failure = null;
        this._closing = false;
        this._exited = false;
        this._endedInput = false;
        this._metrics = {
            readyMs: null,
            callsSent: 0,
            replies: 0,
            remoteErrors: 0,
            stdoutBytes: 0,
            stderrBytes: 0,
            ignoredStdoutLines: 0,
        };
        this._started = performance.now();
        this._readyUntil = this._started + readyTimeoutMs;
        this.ready = new Promise((resolve, reject) => {
            this._readyResolve = resolve;
            this._readyReject = reject;
        });
        // A constructor-started child can fail before the caller attaches a waiter.
        this.ready.catch(() => {});
        this.exited = new Promise((resolve) => {
            this._exitResolve = resolve;
        });
        this._readyTimer = setTimeout(() => this._fatal('host-ready-timeout'), readyTimeoutMs);
        try {
            this._child = spawnProcess(node, ['--max-old-space-size=400', hostFile, pathToFileURL(entryPoint).href], {
                cwd: '/',
                env: {},
                stdio: ['pipe', 'pipe', 'pipe'],
                shell: false,
            });
            const child = this._child;
            child.on('error', () => this._fatal('host-spawn'));
            child.stdin.on('error', () => this._fatal('host-io'));
            child.stdout.on('error', () => this._fatal('host-io'));
            child.stderr.on('error', () => this._fatal('host-io'));
            child.stderr.on('data', (chunk) => {
                this._metrics.stderrBytes += chunk.length;
            });
            child.stdout.on('data', (chunk) => this._read(chunk));
            // exit, not just close: a terminated host must invalidate in-flight work immediately.
            child.on('exit', () => {
                if (!this._closing || this._pending.size || this._admitted || !this._metadata) this._fatal('host-exit');
            });
            child.on('close', (code, signal) => {
                this._exited = true;
                clearTimeout(this._readyTimer);
                clearTimeout(this._closeTimer);
                if (
                    !this._failure &&
                    (!this._closing ||
                        this._pending.size ||
                        this._admitted ||
                        !this._metadata ||
                        code !== 0 ||
                        this._lineBytes)
                ) {
                    this._fatal('host-exit');
                }
                this._exitResolve(
                    Object.freeze({ code: Number.isInteger(code) ? code : null, signal: signal || null })
                );
            });
        } catch (_) {
            this._fatal('host-spawn');
            this._exited = true;
            this._exitResolve({ code: null, signal: null });
        }
    }
    get pid() {
        return this._child?.pid || null;
    }
    get closed() {
        return this._closing || !!this._failure || this._exited;
    }
    get metrics() {
        return Object.freeze({ ...this._metrics, pending: this._pending.size });
    }
    _fatal(code) {
        if (this._failure) return;
        this._failure = fail(code);
        clearTimeout(this._readyTimer);
        this._readyReject(this._failure);
        for (const row of this._pending.values()) {
            clearTimeout(row.timer);
            row.reject(this._failure);
        }
        this._pending.clear();
        this._chunks = [];
        this._lineBytes = 0;
        // A timeout/invalid response poisons the entire child, never just one call.
        // Do not end stdin first: the real host exits on EOF even with work in flight.
        try {
            this._child?.kill('SIGKILL');
        } catch (_) {
            /* No raw OS errors. */
        }
    }
    _read(chunk) {
        if (this._failure) return;
        if (!Buffer.isBuffer(chunk)) chunk = Buffer.from(chunk);
        this._metrics.stdoutBytes += chunk.length;
        let offset = 0;
        while (offset < chunk.length && !this._failure) {
            const newline = chunk.indexOf(10, offset);
            const end = newline === -1 ? chunk.length : newline;
            const piece = chunk.subarray(offset, end);
            this._lineBytes += piece.length;
            if (this._lineBytes > this._limits.maxLineBytes) return this._fatal('host-line-limit');
            if (piece.length) this._chunks.push(piece);
            if (newline === -1) break;
            const line = Buffer.concat(this._chunks, this._lineBytes).toString('utf8');
            this._chunks = [];
            this._lineBytes = 0;
            this._line(line);
            offset = newline + 1;
        }
    }
    _line(line) {
        if (!line.startsWith(PREFIX)) {
            this._metrics.ignoredStdoutLines++;
            return;
        }
        let message;
        try {
            message = JSON.parse(line.slice(PREFIX.length));
        } catch (_) {
            return this._fatal('host-protocol');
        }
        if (!object(message)) return this._fatal('host-protocol');
        if (message.ready === true) {
            if (
                this._metadata ||
                Object.hasOwn(message, 'id') ||
                !Array.isArray(message.methods) ||
                !message.methods.every((m) => typeof m === 'string' && /^[A-Za-z_$][\w$]*$/.test(m)) ||
                new Set(message.methods).size !== message.methods.length ||
                !object(message.constants)
            )
                return this._fatal('host-protocol');
            if (performance.now() >= this._readyUntil) return this._fatal('host-ready-timeout');
            clearTimeout(this._readyTimer);
            this._metadata = Object.freeze({
                methods: Object.freeze([...message.methods]),
                constants: message.constants,
            });
            this._metrics.readyMs = performance.now() - this._started;
            this._readyResolve(this._metadata);
            this._endWhenDrained();
            return;
        }
        if (!this._metadata || !Object.hasOwn(message, 'id') || typeof message.ok !== 'boolean') {
            return this._fatal('host-protocol');
        }
        const row = this._pending.get(message.id);
        if (!row) return this._fatal('host-unknown-response');
        if (performance.now() >= row.until) return this._fatal('host-call-timeout');
        if (message.ok && Object.hasOwn(message, 'value')) {
            if (Buffer.byteLength(JSON.stringify(message.value)) > this._limits.maxStateBytes) {
                return this._fatal('host-state-limit');
            }
        }
        clearTimeout(row.timer);
        this._pending.delete(message.id);
        this._metrics.replies++;
        if (message.ok) row.resolve(message.value);
        else {
            // Never echo the host's error/name/stack; they may embed a state or secret.
            this._metrics.remoteErrors++;
            row.reject(fail('host-remote-error'));
        }
        this._endWhenDrained();
    }
    async call(method, args = []) {
        if (typeof method !== 'string' || !/^[A-Za-z_$][\w$]*$/.test(method) || !Array.isArray(args)) {
            throw fail('host-call-arguments');
        }
        if (this.closed) throw this._failure || fail('host-closed');
        // Serialize BEFORE awaiting ready: caller mutations cannot cross the boundary.
        let rawArgs;
        try {
            rawArgs = JSON.stringify(args);
        } catch (_) {
            throw fail('host-call-arguments');
        }
        if (typeof rawArgs !== 'string' || !rawArgs.startsWith('[')) throw fail('host-call-arguments');
        if (Buffer.byteLength(rawArgs) > this._limits.maxStateBytes) throw fail('host-state-limit');
        if (this._pending.size + this._admitted >= LIMITS.pending) throw fail('host-busy');
        this._admitted++;
        try {
            const metadata = await this.ready;
            // close() drains calls already accepted, including calls waiting for ready.
            if (this._failure || this._exited) throw this._failure || fail('host-closed');
            if (!metadata.methods.includes(method)) throw fail('host-unknown-method');
            const id = ++this._sequence;
            const line = `{"id":${id},"method":${JSON.stringify(method)},"args":${rawArgs}}\n`;
            if (Buffer.byteLength(line) > this._limits.maxLineBytes) throw fail('host-line-limit');
            return new Promise((resolve, reject) => {
                const until = performance.now() + this._limits.callTimeoutMs;
                const timer = setTimeout(() => this._fatal('host-call-timeout'), this._limits.callTimeoutMs);
                this._pending.set(id, { resolve, reject, timer, until });
                this._metrics.callsSent++;
                try {
                    this._child.stdin.write(line, (error) => {
                        if (error) this._fatal('host-io');
                    });
                } catch (_) {
                    this._fatal('host-io');
                }
            });
        } finally {
            this._admitted--;
            this._endWhenDrained();
        }
    }
    _endWhenDrained() {
        if (
            this._closing &&
            this._metadata &&
            !this._pending.size &&
            !this._admitted &&
            !this._failure &&
            !this._endedInput
        ) {
            this._endedInput = true;
            this._child.stdin.end();
        }
    }
    close() {
        if (this._closePromise) return this._closePromise;
        this._closing = true;
        if (!this._exited) {
            this._closeTimer = setTimeout(() => this._fatal('host-close-timeout'), this._limits.closeTimeoutMs);
            this._endWhenDrained();
        }
        this._closePromise = this.exited.then((result) => {
            clearTimeout(this._closeTimer);
            if (this._failure?.code === 'host-close-timeout') throw this._failure;
            return result;
        });
        this._closePromise.catch(() => {});
        return this._closePromise;
    }
}
async function openHost(options) {
    const client = new HostClient(options);
    try {
        await client.ready;
        return client;
    } catch (error) {
        await client.close();
        throw error;
    }
}
module.exports = { HostClient, HostClientError, openHost, PREFIX, LIMITS };
