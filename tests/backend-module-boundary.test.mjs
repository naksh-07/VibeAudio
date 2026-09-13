import test from 'node:test';
import assert from 'node:assert';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);

test('Backend Module Boundaries', async (t) => {
  await t.test('Worker ESM modules can be imported directly via standard ESM import', async () => {
    // Dynamic import to test if the worker package boundary correctly scopes it as ESM
    const proxymanager = await import('../backend/workers/proxymanager.js');
    assert.ok(proxymanager.default, 'Expected worker to have a default export');
    assert.strictEqual(typeof proxymanager.default.fetch, 'function', 'Expected worker to export a fetch function');
  });

  await t.test('Lambda CommonJS modules can be cleanly required', () => {
    // We should be able to require the CJS lambdas
    const getBooks = require('../backend/lambda/getBooks.js');
    const getBookDetails = require('../backend/lambda/getBookDetails.js');
    const getProgress = require('../backend/lambda/getProgress.js');
    const saveProgress = require('../backend/lambda/saveProgress.js');
    const auth = require('../backend/lambda/auth.js');

    assert.strictEqual(typeof getBooks.handler, 'function');
    assert.strictEqual(typeof getBookDetails.handler, 'function');
    assert.strictEqual(typeof getProgress.handler, 'function');
    assert.strictEqual(typeof saveProgress.handler, 'function');
    assert.strictEqual(typeof auth.handler, 'function');
  });

  await t.test('Shared backend modules are interoperable across boundaries (can be required)', () => {
    const cors = require('../backend/shared/cors.js');
    const errorHandler = require('../backend/shared/error-handler.js');
    const authMiddleware = require('../backend/shared/auth-middleware.js');

    assert.strictEqual(typeof cors.getSafeCorsHeaders, 'function');
    assert.strictEqual(typeof errorHandler.handleLambdaError, 'function');
    assert.strictEqual(typeof authMiddleware.authenticateRequest, 'function');
  });
});
