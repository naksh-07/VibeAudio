import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';

test('Test Suite 1: SSRF Protection Invariants', async () => {
    // Read the worker file
    const workerCode = await fs.readFile('backend/workers/proxymanager.js', 'utf8');
    
    // Create base64 data URL to import
    const b64 = Buffer.from(workerCode).toString('base64');
    const dataUrl = `data:text/javascript;base64,${b64}`;
    
    // Import the worker dynamically
    const worker = await import(dataUrl);
    
    // Create a mock request helper
    const createRequest = (targetUrl) => {
        return {
            method: 'GET',
            url: `https://our-worker.com/?url=${encodeURIComponent(targetUrl)}`,
            headers: new Headers()
        };
    };

    // Verify it rejects private IPs
    const privateIps = ['https://127.0.0.1/audio.mp3', 'https://169.254.169.254/meta', 'https://10.0.0.1/internal'];
    for (const ip of privateIps) {
        const req = createRequest(ip);
        const res = await worker.default.fetch(req);
        assert.equal(res.status, 403, `Should reject private IP: ${ip}`);
        const text = await res.text();
        assert.match(text, /Forbidden hostname/, `Should give Forbidden hostname error for ${ip}`);
    }

    // Verify http scheme rejection
    const httpUrl = 'http://media.vibeaudio.com/audio.mp3';
    const httpReq = createRequest(httpUrl);
    const httpRes = await worker.default.fetch(httpReq);
    assert.equal(httpRes.status, 403, `Should reject http protocol`);
    assert.match(await httpRes.text(), /Forbidden protocol/, `Should give Forbidden protocol error`);
    
    // Verify it allows correct domains
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async () => new Response("ok", {status: 200, headers: new Headers()});
    try {
        const allowedUrl = 'https://media.vibeaudio.com/audio.mp3';
        const allowedReq = createRequest(allowedUrl);
        const allowedRes = await worker.default.fetch(allowedReq);
        assert.equal(allowedRes.status, 200, `Should allow media.vibeaudio.com`);
    } finally {
        globalThis.fetch = originalFetch;
    }
});

test('Test Suite 2: Master Code Auth Bypass Eradication', async () => {
    const authCode = await fs.readFile('backend/lambda/auth.js', 'utf8');
    
    assert.ok(!authCode.includes('ADMIN_GOD'), 'ADMIN_GOD should not be present');
    assert.ok(!authCode.includes('VIBE2026'), 'VIBE2026 should not be present');
    assert.ok(!authCode.includes('BETA_TEST'), 'BETA_TEST should not be present');
    assert.ok(!authCode.includes('validCodes'), 'validCodes should not be present');
});

test('Test Suite 3: Runtime Dependency Declarations', async () => {
    const pkgJsonStr = await fs.readFile('backend/package.json', 'utf8');
    const pkgJson = JSON.parse(pkgJsonStr);
    
    assert.ok(pkgJson.dependencies, 'Dependencies should exist');
    assert.ok(pkgJson.dependencies['@aws-sdk/client-s3'], '@aws-sdk/client-s3 should be declared');
    assert.ok(pkgJson.dependencies['@aws-sdk/s3-request-presigner'], '@aws-sdk/s3-request-presigner should be declared');
    assert.ok(pkgJson.dependencies['jose'], 'jose should be declared');
    
    assert.equal(pkgJson.type, 'commonjs', 'type should be commonjs');
});

test('Test Suite 4: Zero-Build Frontend Invariants', async () => {
    const frontendDir = 'frontend';
    const forbiddenFiles = ['webpack.config.js', 'vite.config.js', 'rollup.config.js', 'tsconfig.json'];
    
    for (const file of forbiddenFiles) {
        let exists = false;
        try {
            await fs.access(path.join(frontendDir, file));
            exists = true;
        } catch (e) {
            // Expected
        }
        assert.equal(exists, false, `${file} should not exist in frontend directory`);
    }
    
    const jsDir = 'frontend/src/js';
    const files = await fs.readdir(jsDir);
    const jsFiles = files.filter(f => f.endsWith('.js'));
    
    for (const file of jsFiles) {
        const content = await fs.readFile(path.join(jsDir, file), 'utf8');
        assert.ok(!content.includes('require('), `${file} should not use require()`);
    }
});

test('Test Suite 5: Design Authority Preservation', async () => {
    let exists = false;
    try {
        const stat = await fs.stat('.stitch');
        exists = stat.isDirectory();
    } catch (e) {
        // Expected
    }
    assert.equal(exists, true, '.stitch directory should exist');
});
