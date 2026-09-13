import test from 'node:test';
import assert from 'node:assert';
import { getSafeCorsHeaders } from '../backend/shared/cors.js';

test('CORS Policy Hardening', async (t) => {

    await t.test('Approved production origins', () => {
        const prodOrigins = [
            'https://vibeaudio.pages.dev',
            'https://preview.vibeaudio.pages.dev',
            'https://vibeaudio.com'
        ];

        for (const origin of prodOrigins) {
            const headers = getSafeCorsHeaders(origin, 'production');
            assert.strictEqual(headers['Access-Control-Allow-Origin'], origin);
        }
    });

    await t.test('Rejected origins fall back to safe default', () => {
        const rejectedOrigins = [
            'https://attacker.com',
            'https://evil-vibeaudio.pages.dev.attacker.com',
            'http://vibeaudio.pages.dev', // Must be https
            'https://vibeaudio.pages.dev.com'
        ];

        for (const origin of rejectedOrigins) {
            const headers = getSafeCorsHeaders(origin, 'production');
            assert.strictEqual(headers['Access-Control-Allow-Origin'], 'https://vibeaudio.pages.dev');
        }
    });

    await t.test('Development origins allowed in non-production', () => {
        const devOrigins = [
            'http://localhost:8080',
            'http://127.0.0.1:3000',
            'http://localhost'
        ];

        for (const origin of devOrigins) {
            const headers = getSafeCorsHeaders(origin, 'development');
            assert.strictEqual(headers['Access-Control-Allow-Origin'], origin);
        }
    });

    await t.test('Development origins rejected in production', () => {
        const devOrigins = [
            'http://localhost:8080',
            'http://127.0.0.1:3000'
        ];

        for (const origin of devOrigins) {
            const headers = getSafeCorsHeaders(origin, 'production');
            assert.strictEqual(headers['Access-Control-Allow-Origin'], 'https://vibeaudio.pages.dev');
        }
    });

    await t.test('OPTIONS preflight and security headers are present', () => {
        const headers = getSafeCorsHeaders('https://vibeaudio.pages.dev', 'production');

        assert.strictEqual(headers['Access-Control-Allow-Methods'], 'GET, POST, PUT, OPTIONS');
        assert.strictEqual(headers['Access-Control-Allow-Headers'], 'Authorization, Content-Type, Range, X-Client-Version, X-Request-Id');
        assert.strictEqual(headers['Access-Control-Expose-Headers'], 'Content-Range, Content-Length, ETag, X-Request-Id');
        assert.strictEqual(headers['Access-Control-Max-Age'], '86400');
        assert.strictEqual(headers['Vary'], 'Origin');

        // Security headers
        assert.strictEqual(headers['X-Content-Type-Options'], 'nosniff');
        assert.strictEqual(headers['X-Frame-Options'], 'DENY');
        assert.strictEqual(headers['Referrer-Policy'], 'strict-origin-when-cross-origin');
    });
});
