import test from 'node:test';
import assert from 'node:assert/strict';
import { generateKeyPair, exportJWK, SignJWT, createLocalJWKSet } from '../backend/node_modules/jose/dist/webapi/index.js';
import { setJWKSForTest } from '../backend/shared/auth-middleware.js';

process.env.AWS_REGION = 'us-east-1';
process.env.AWS_ACCESS_KEY_ID = 'test';
process.env.AWS_SECRET_ACCESS_KEY = 'test';
import { handler as saveProgressHandler, setDocClientForTest as setSaveDocClient } from '../backend/lambda/saveProgress.js';
import { handler as getProgressHandler, setDocClientForTest as setGetDocClient } from '../backend/lambda/getProgress.js';

test('Progress Endpoints Auth & BOLA Tests', async (t) => {
    // 1. Setup Test Keys
    const { publicKey, privateKey } = await generateKeyPair('RS256');
    const publicJwk = await exportJWK(publicKey);
    publicJwk.alg = 'RS256';
    publicJwk.kid = 'test-kid';

    const localJWKS = createLocalJWKSet({ keys: [publicJwk] });
    setJWKSForTest(localJWKS);

    // Ensure our mock doesn't fail due to CLERK_ISSUER if set
    const testIssuer = 'https://test-issuer';
    process.env.CLERK_ISSUER = testIssuer;

    // 2. Mock DynamoDB
    let dbState = {}; // userId -> array of records

    const mockDocClient = {
        send: async (command) => {
            if (command.constructor.name === 'PutCommand' || (command.input && command.input.Item)) {
                const item = command.input.Item;
                const userId = item.userId;
                if (!dbState[userId]) dbState[userId] = [];

                const existingIdx = dbState[userId].findIndex(r => r.bookId === item.bookId);
                if (existingIdx >= 0) {
                    dbState[userId][existingIdx] = item;
                } else {
                    dbState[userId].push(item);
                }
                return {};
            }
            if (command.constructor.name === 'QueryCommand' || (command.input && command.input.KeyConditionExpression)) {
                let userId = 'userA'; // Fallback
                if (command.input.ExpressionAttributeValues && command.input.ExpressionAttributeValues[':u']) {
                    userId = command.input.ExpressionAttributeValues[':u'];
                }
                return { Items: dbState[userId] || [] };
            }
            return {};
        }
    };

    setSaveDocClient(mockDocClient);
    setGetDocClient(mockDocClient);

    // Helper to generate tokens
    const generateToken = async ({ sub, issuer = testIssuer, expiresIn = '1h', kid = 'test-kid', customPrivateKey = privateKey }) => {
        const jwt = new SignJWT({})
            .setProtectedHeader({ alg: 'RS256', kid })
            .setIssuedAt()
            .setIssuer(issuer)
            .setExpirationTime(expiresIn);

        if (sub) {
            jwt.setSubject(sub);
        }

        return jwt.sign(customPrivateKey);
    };

    await t.test('1. Valid Clerk JWT authenticated successfully and writes progress', async () => {
        const token = await generateToken({ sub: 'userA' });
        const event = {
            headers: { authorization: `Bearer ${token}` },
            body: JSON.stringify({ bookId: 'book1', chapterIndex: 1, currentTime: 100 })
        };
        const response = await saveProgressHandler(event);
        assert.equal(response.statusCode, 200);

        const resBody = JSON.parse(response.body);
        assert.equal(resBody.progress.userId, 'userA');
        assert.equal(resBody.progress.bookId, 'book1');
        assert.equal(dbState['userA'][0].bookId, 'book1');
    });

    await t.test('2. Invalid signature returns 401', async () => {
        // Sign with a different key
        const { privateKey: badKey } = await generateKeyPair('RS256');
        const token = await generateToken({ sub: 'userA', customPrivateKey: badKey });
        const event = {
            headers: { authorization: `Bearer ${token}` }
        };
        const response = await getProgressHandler(event);
        assert.equal(response.statusCode, 401);
        assert.equal(JSON.parse(response.body).error, 'Unauthorized');
    });

    await t.test('3. Expired token returns 401', async () => {
        // Create an expired token by setting expiration in the past
        const jwt = new SignJWT({})
            .setProtectedHeader({ alg: 'RS256', kid: 'test-kid' })
            .setIssuedAt()
            .setIssuer(testIssuer)
            .setSubject('userA')
            .setExpirationTime(Math.floor(Date.now() / 1000) - 3600); // 1 hour ago
        const token = await jwt.sign(privateKey);
        const event = {
            headers: { authorization: `Bearer ${token}` }
        };
        const response = await getProgressHandler(event);
        assert.equal(response.statusCode, 401);
    });

    await t.test('4. Wrong issuer returns 401', async () => {
        const token = await generateToken({ sub: 'userA', issuer: 'wrong-issuer' });
        const event = {
            headers: { authorization: `Bearer ${token}` }
        };
        const response = await getProgressHandler(event);
        assert.equal(response.statusCode, 401);
    });

    await t.test('5. Missing sub claim returns 401', async () => {
        const token = await generateToken({ sub: null }); // no sub
        const event = {
            headers: { authorization: `Bearer ${token}` }
        };
        const response = await getProgressHandler(event);
        assert.equal(response.statusCode, 401);
    });

    await t.test('6. Missing Authorization header returns 401', async () => {
        const event = { headers: {} };
        const response = await getProgressHandler(event);
        assert.equal(response.statusCode, 401);
    });

    await t.test('7. User A reading own progress returns 200 with User A records', async () => {
        const token = await generateToken({ sub: 'userA' });
        const event = {
            headers: { authorization: `Bearer ${token}` }
        };
        const response = await getProgressHandler(event);
        assert.equal(response.statusCode, 200);
        const body = JSON.parse(response.body);
        assert.equal(body.progress.length, 1);
        assert.equal(body.progress[0].userId, 'userA');
    });

    await t.test('8. User A passing ?userId=userB still reads User A records (BOLA blocked)', async () => {
        const token = await generateToken({ sub: 'userA' });
        const event = {
            headers: { authorization: `Bearer ${token}` },
            queryStringParameters: { userId: 'userB' }
        };
        const response = await getProgressHandler(event);
        assert.equal(response.statusCode, 200);
        const body = JSON.parse(response.body);
        assert.equal(body.progress.length, 1);
        assert.equal(body.progress[0].userId, 'userA'); // Used JWT sub, ignored userB
    });

    await t.test('9. User A writing progress saves under User A even if body specifies userId: userB (BOLA blocked)', async () => {
        const token = await generateToken({ sub: 'userA' });
        const event = {
            headers: { authorization: `Bearer ${token}` },
            body: JSON.stringify({ userId: 'userB', bookId: 'book2', chapterIndex: 2 })
        };
        const response = await saveProgressHandler(event);
        assert.equal(response.statusCode, 200);
        const body = JSON.parse(response.body);
        assert.equal(body.progress.userId, 'userA'); // Ignored userB
        assert.equal(dbState['userA'].length, 2); // Now has 2 books
        assert.equal(dbState['userB'], undefined); // Nothing saved under userB
    });

    await t.test('10. OPTIONS request returns 200 without checking auth', async () => {
        const event = {
            requestContext: { http: { method: 'OPTIONS' } }
        };
        // No headers provided, but should still pass
        const response1 = await getProgressHandler(event);
        assert.equal(response1.statusCode, 200);

        const response2 = await saveProgressHandler(event);
        assert.equal(response2.statusCode, 200);
    });
});
