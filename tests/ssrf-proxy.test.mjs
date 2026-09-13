import test from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';

// Read the worker code and create a data URL for dynamic import
const workerPath = path.resolve('backend/workers/proxymanager.js');
const workerCode = fs.readFileSync(workerPath, 'utf8');
const dataUrl = 'data:text/javascript;base64,' + Buffer.from(workerCode).toString('base64');

// We will load the worker in before() to make sure it loads correctly
let worker;

// Mock Response class if not in environment
class MockResponse {
  constructor(body, init) {
    this.body = body;
    this.status = init?.status || 200;
    this.statusText = init?.statusText || 'OK';
    this.headers = new Map(Object.entries(init?.headers || {}));
  }
}

// Mock Request class
class MockRequest {
  constructor(url, init = {}) {
    this.url = url;
    this.method = init.method || 'GET';
    // Use simple Map for headers simulation
    this.headers = new Map();
    if (init.headers) {
      for (const [key, value] of Object.entries(init.headers)) {
        this.headers.set(key.toLowerCase(), value);
      }
    }
  }
}

// Mock Headers class
class MockHeaders {
  constructor(init = {}) {
    this.map = new Map();
    for (const [key, value] of Object.entries(init)) {
      this.map.set(key.toLowerCase(), value);
    }
  }
  set(name, value) {
    this.map.set(name.toLowerCase(), value);
  }
  get(name) {
    const val = this.map.get(name.toLowerCase());
    return val === undefined ? null : val;
  }
  [Symbol.iterator]() {
    return this.map.entries();
  }
}

// Global scope mocks for the worker
global.Response = global.Response || MockResponse;
global.Request = global.Request || MockRequest;
global.Headers = global.Headers || MockHeaders;

// Setup a mock fetch globally to intercept the outgoing calls
let fetchCalls = [];
global.fetch = async (url, init) => {
  fetchCalls.push({ url, init });
  return new MockResponse('mock-body', {
    status: 200,
    headers: { 'Content-Type': 'audio/mpeg' }
  });
};

test('ProxyManager SSRF and Security tests', async (t) => {
  // Load the worker
  const module = await import(dataUrl);
  worker = module.default;

  t.beforeEach(() => {
    fetchCalls = [];
  });

  await t.test('Missing URL returns HTTP 400', async () => {
    const req = new MockRequest('https://worker.dev/');
    const res = await worker.fetch(req);
    assert.strictEqual(res.status, 400);
  });

  await t.test('Malformed URL returns HTTP 400', async () => {
    const req = new MockRequest('https://worker.dev/?url=not-a-url');
    const res = await worker.fetch(req);
    assert.strictEqual(res.status, 400);
  });

  await t.test('Non-HTTPS schemes return HTTP 403', async () => {
    const schemes = ['http', 'ftp', 'file', 'data', 'javascript'];
    for (const scheme of schemes) {
      const targetUrl = `${scheme}://media.vibeaudio.com/test`;
      const req = new MockRequest(`https://worker.dev/?url=${encodeURIComponent(targetUrl)}`);
      const res = await worker.fetch(req);
      assert.strictEqual(res.status, 403, `Scheme ${scheme} should be rejected`);
    }
  });

  await t.test('URLs with credentials return HTTP 403', async () => {
    const req = new MockRequest('https://worker.dev/?url=https://user:pass@media.vibeaudio.com/file');
    const res = await worker.fetch(req);
    assert.strictEqual(res.status, 403);
  });

  await t.test('Private IPs and localhost return HTTP 403', async () => {
    const targets = [
      'https://127.0.0.1/file',
      'https://localhost/file',
      'https://169.254.169.254/latest/meta-data', // AWS Metadata IP
      'https://10.0.0.1/file',
      'https://192.168.1.1/file'
    ];
    for (const target of targets) {
      const req = new MockRequest(`https://worker.dev/?url=${encodeURIComponent(target)}`);
      const res = await worker.fetch(req);
      assert.strictEqual(res.status, 403, `Target ${target} should be rejected`);
    }
  });

  await t.test('Domain confusion returns HTTP 403', async () => {
    const targets = [
      'https://media.vibeaudio.com.attacker.com/file',
      'https://evil-archive.org/file',
      'https://archive.org.evil.com/file'
    ];
    for (const target of targets) {
      const req = new MockRequest(`https://worker.dev/?url=${encodeURIComponent(target)}`);
      const res = await worker.fetch(req);
      assert.strictEqual(res.status, 403, `Target ${target} should be rejected`);
    }
  });

  await t.test('Allowed origins succeed', async () => {
    const targets = [
      'https://media.vibeaudio.com/file.mp3',
      'https://archive.org/download/item/file.mp3',
      'https://test.archive.org/file.mp3',
      'https://bucket.r2.cloudflarestorage.com/file.mp3'
    ];
    for (const target of targets) {
      const req = new MockRequest(`https://worker.dev/?url=${encodeURIComponent(target)}`);
      const res = await worker.fetch(req);
      assert.strictEqual(res.status, 200, `Target ${target} should be allowed`);
      assert.strictEqual(fetchCalls.length, 1);
      assert.strictEqual(fetchCalls[0].url, target);
      fetchCalls = []; // reset for next iteration
    }
  });

  await t.test('Header filtering passes safe headers and drops sensitive ones', async () => {
    const req = new MockRequest('https://worker.dev/?url=https://media.vibeaudio.com/file.mp3', {
      headers: {
        'Range': 'bytes=0-100',
        'If-Range': 'w/"123"',
        'If-None-Match': 'w/"456"',
        'If-Modified-Since': 'Wed, 21 Oct 2015 07:28:00 GMT',
        'Accept': 'audio/*',
        'Authorization': 'Bearer secret-token',
        'Cookie': 'session_id=12345',
        'Host': 'worker.dev',
        'X-Custom-Header': 'should-be-dropped'
      }
    });

    const res = await worker.fetch(req);
    assert.strictEqual(res.status, 200);
    assert.strictEqual(fetchCalls.length, 1);

    const outgoingHeaders = fetchCalls[0].init.headers;
    assert(outgoingHeaders instanceof global.Headers, 'Headers should be a Headers object');

    // Check included
    assert.strictEqual(outgoingHeaders.get('range'), 'bytes=0-100');
    assert.strictEqual(outgoingHeaders.get('if-range'), 'w/"123"');
    assert.strictEqual(outgoingHeaders.get('if-none-match'), 'w/"456"');
    assert.strictEqual(outgoingHeaders.get('if-modified-since'), 'Wed, 21 Oct 2015 07:28:00 GMT');
    assert.strictEqual(outgoingHeaders.get('accept'), 'audio/*');

    // Check dropped
    assert.strictEqual(outgoingHeaders.get('authorization'), null);
    assert.strictEqual(outgoingHeaders.get('cookie'), null);
    assert.strictEqual(outgoingHeaders.get('host'), null);
    assert.strictEqual(outgoingHeaders.get('x-custom-header'), null);
  });

  await t.test('Upstream fetch uses redirect: manual', async () => {
    const req = new MockRequest('https://worker.dev/?url=https://media.vibeaudio.com/file.mp3');
    await worker.fetch(req);
    assert.strictEqual(fetchCalls.length, 1);
    assert.strictEqual(fetchCalls[0].init.redirect, 'manual');
  });

  await t.test('CORS headers on OPTIONS preflight are preserved', async () => {
    const req = new MockRequest('https://worker.dev/', { method: 'OPTIONS' });
    const res = await worker.fetch(req);

    // In our MockResponse, headers is a Map, so we get with string keys
    assert.strictEqual(res.headers.get('Access-Control-Allow-Origin'), '*');
    assert.strictEqual(res.headers.get('Access-Control-Allow-Methods'), 'GET, HEAD, POST, OPTIONS');
    assert.strictEqual(res.headers.get('Access-Control-Allow-Headers'), 'Range');
    assert.strictEqual(res.headers.get('Access-Control-Expose-Headers'), 'Content-Length, Content-Range');

    assert.strictEqual(fetchCalls.length, 0, 'Should not fetch on preflight');
  });

  await t.test('CORS headers on normal responses are preserved', async () => {
    const req = new MockRequest('https://worker.dev/?url=https://media.vibeaudio.com/file.mp3');
    const res = await worker.fetch(req);

    assert.strictEqual(res.status, 200);
    // Standard response includes our mocked backend Content-Type plus CORS headers
    assert.strictEqual(res.headers.get('Access-Control-Allow-Origin'), '*');
  });
});
