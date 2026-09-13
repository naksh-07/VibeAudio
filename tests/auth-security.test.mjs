import test, { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const Module = require('node:module');

// Mock AWS SDK to prevent actual network calls during tests
const originalRequire = Module.prototype.require;
Module.prototype.require = function(path) {
    if (path === '@aws-sdk/client-dynamodb') {
        return { DynamoDBClient: class {} };
    }
    if (path === '@aws-sdk/lib-dynamodb') {
        return {
            DynamoDBDocumentClient: {
                from: () => ({
                    send: async () => ({})
                })
            },
            PutCommand: class {}
        };
    }
    return originalRequire.call(this, path);
};

const { handler } = require('../backend/lambda/auth.js');

describe('Auth Security Validation', () => {
    it('returns 401 for legacy ADMIN_GOD code', async () => {
        const response = await handler({
            body: JSON.stringify({ code: 'ADMIN_GOD' })
        });
        assert.equal(response.statusCode, 401);
        assert.deepEqual(JSON.parse(response.body), { success: false, error: 'Unauthorized' });
    });

    it('returns 401 for legacy VIBE2026 code', async () => {
        const response = await handler({
            body: JSON.stringify({ code: 'VIBE2026' })
        });
        assert.equal(response.statusCode, 401);
        assert.deepEqual(JSON.parse(response.body), { success: false, error: 'Unauthorized' });
    });

    it('returns 401 for legacy BETA_TEST code', async () => {
        const response = await handler({
            body: JSON.stringify({ code: 'BETA_TEST' })
        });
        assert.equal(response.statusCode, 401);
        assert.deepEqual(JSON.parse(response.body), { success: false, error: 'Unauthorized' });
    });

    it('returns 401 for non-sync request', async () => {
        const response = await handler({
            body: JSON.stringify({ action: 'random' })
        });
        assert.equal(response.statusCode, 401);
        assert.deepEqual(JSON.parse(response.body), { success: false, error: 'Unauthorized' });
    });

    it('returns 200 for valid Clerk sync request', async () => {
        const response = await handler({
            body: JSON.stringify({ action: 'sync', userId: 'usr_123', name: 'Test User' })
        });
        assert.equal(response.statusCode, 200);
        assert.deepEqual(JSON.parse(response.body), { success: true, message: 'User Synced ✅' });
    });

    it('returns 400 for Clerk sync request without userId', async () => {
        const response = await handler({
            body: JSON.stringify({ action: 'sync' })
        });
        assert.equal(response.statusCode, 400);
        assert.deepEqual(JSON.parse(response.body), { error: 'Missing userId' });
    });

    it('returns 200 for OPTIONS preflight request', async () => {
        const response = await handler({
            requestContext: { http: { method: 'OPTIONS' } }
        });
        assert.equal(response.statusCode, 200);
        assert.equal(response.body, '');
    });
});
