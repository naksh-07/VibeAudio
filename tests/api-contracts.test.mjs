import { describe, it, mock, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

process.env.AWS_REGION = "us-east-1";
process.env.AWS_ACCESS_KEY_ID = "test-access";
process.env.AWS_SECRET_ACCESS_KEY = "test-secret";
process.env.R2_ACCOUNT_ID = "test-account";
process.env.R2_ACCESS_KEY_ID = "test-r2-access";
process.env.R2_SECRET_ACCESS_KEY = "test-r2-secret";
process.env.R2_BUCKET_NAME = "test-bucket";

const requireBackend = createRequire(new URL("../backend/package.json", import.meta.url));
const { DynamoDBDocumentClient } = requireBackend("@aws-sdk/lib-dynamodb");
const s3Presigner = requireBackend("@aws-sdk/s3-request-presigner");

describe("API Contracts Regression Test Suite", () => {
    let dynamoMock;
    beforeEach(() => {
        dynamoMock = mock.method(DynamoDBDocumentClient.prototype, "send", async () => ({ Items: [], Item: null }));
    });
    afterEach(() => {
        mock.restoreAll();
    });
    it("setup structure", () => {
        assert.ok(true);
    });
});

describe("getBooks.js Contracts", () => {
    let dynamoMock;
    const { handler } = requireBackend("./lambda/getBooks.js");

    beforeEach(() => {
        dynamoMock = mock.method(DynamoDBDocumentClient.prototype, "send");
    });
    afterEach(() => {
        mock.restoreAll();
    });

    it("OPTIONS returns 200 with CORS headers", async () => {
        const event = {
            headers: { origin: "https://vibeaudio.pages.dev" },
            requestContext: { http: { method: "OPTIONS" } }
        };
        const response = await handler(event);
        assert.equal(response.statusCode, 200);
        assert.ok(response.headers["Access-Control-Allow-Origin"] || response.headers["access-control-allow-origin"]);
    });

    it("Success returns mapped items and excludes chapters", async () => {
        dynamoMock.mock.mockImplementation(async () => ({
            Items: [
                { bookId: "b1", title: "Book 1", chapters: [{ name: "c1", url: "u1" }] },
                { bookId: "b2", title: "Book 2", totalChapters: 0 }
            ]
        }));
        const event = {
            headers: { origin: "https://vibeaudio.pages.dev" },
            requestContext: { http: { method: "GET" } }
        };
        const response = await handler(event);
        assert.equal(response.statusCode, 200);
        const body = JSON.parse(response.body);
        assert.equal(body[0].bookId, "b1");
        assert.equal(body[0].chapters, undefined);
    });

    it("DB scan failure returns 500 with CORS headers", async () => {
        dynamoMock.mock.mockImplementation(async () => {
            throw new Error("DynamoDB error");
        });
        const event = {
            headers: { origin: "https://vibeaudio.pages.dev" },
            requestContext: { http: { method: "GET" } }
        };
        const response = await handler(event);
        assert.equal(response.statusCode, 500);
        assert.ok(response.headers["Access-Control-Allow-Origin"] || response.headers["access-control-allow-origin"]);
    });
});

describe("getBookDetails.js Contracts", () => {
    let dynamoMock;
    let s3PresignerMock;
    const { handler } = requireBackend("./lambda/getBookDetails.js");

    beforeEach(() => {
        dynamoMock = mock.method(DynamoDBDocumentClient.prototype, "send");
        s3PresignerMock = mock.method(s3Presigner, "getSignedUrl", async () => {
            return "https://mocked-signed-url.com?bucket=test-bucket";
        });
    });
    afterEach(() => {
        mock.restoreAll();
    });

    it("OPTIONS returns 200 with CORS headers", async () => {
        const event = {
            headers: { origin: "https://vibeaudio.pages.dev" },
            requestContext: { http: { method: "OPTIONS" } }
        };
        const response = await handler(event);
        assert.equal(response.statusCode, 200);
    });

    it("Missing bookId in JSON body returns HTTP 400", async () => {
        const response = await handler({
            body: JSON.stringify({}),
            requestContext: { http: { method: "POST" } }
        });
        assert.equal(response.statusCode, 400);
    });

    it("Missing Item in DynamoDB returns HTTP 404", async () => {
        dynamoMock.mock.mockImplementation(async () => ({ Item: null }));
        const response = await handler({
            body: JSON.stringify({ bookId: "missing-1" }),
            requestContext: { http: { method: "POST" } }
        });
        assert.equal(response.statusCode, 404);
    });

    it("Existing book returns HTTP 200 with signed chapter URLs", async () => {
        dynamoMock.mock.mockImplementation(async () => ({
            Item: {
                bookId: "b1",
                chapters: [
                    { name: "Chap 1", url: "r2://path/to/chap1.mp3" },
                    { name: "Chap 2", url: "https://already-signed.com/chap2" }
                ]
            }
        }));
        const response = await handler({
            body: JSON.stringify({ bookId: "b1" }),
            requestContext: { http: { method: "POST" } }
        });
        assert.equal(response.statusCode, 200);
        const body = JSON.parse(response.body);
        assert.ok(body.chapters[0].url.includes("test-bucket"), "url should be signed and have bucket");
    });

    it("Unhandled error is handled via handleLambdaError returning HTTP 500", async () => {
        dynamoMock.mock.mockImplementation(async () => {
            throw new Error("Crash DB");
        });
        const response = await handler({
            body: JSON.stringify({ bookId: "crash-1" }),
            requestContext: { http: { method: "POST" } }
        });
        assert.equal(response.statusCode, 500);
    });
});

describe("auth.js Contracts", () => {
    let dynamoMock;
    const { handler } = requireBackend("./lambda/auth.js");

    beforeEach(() => {
        dynamoMock = mock.method(DynamoDBDocumentClient.prototype, "send");
    });
    afterEach(() => {
        mock.restoreAll();
    });

    it("OPTIONS returns 200 with CORS headers", async () => {
        const response = await handler({ requestContext: { http: { method: "OPTIONS" } } });
        assert.equal(response.statusCode, 200);
    });

    it("Empty body (or non-sync action) returns HTTP 401", async () => {
        const response = await handler({ body: JSON.stringify({}) });
        assert.equal(response.statusCode, 401);
    });

    it("Missing userId (for sync) returns HTTP 400", async () => {
        const response = await handler({ body: JSON.stringify({ action: "sync" }) });
        assert.equal(response.statusCode, 400);
    });

    it("Valid sync action returns HTTP 200", async () => {
        dynamoMock.mock.mockImplementation(async () => ({}));
        const response = await handler({
            body: JSON.stringify({ action: "sync", userId: "u1", name: "User 1" })
        });
        assert.equal(response.statusCode, 200);
    });
});

describe("saveProgress.js & getProgress.js Contracts", () => {
    let dynamoMock;
    let saveProgress, getProgress, authMiddleware;

    beforeEach(() => {
        authMiddleware = requireBackend("./shared/auth-middleware.js");
        const originalAuth = authMiddleware.authenticateRequest;

        // Mock it in the module cache
        authMiddleware.authenticateRequest = async () => ({ userId: "u1" });

        // Clear caches so they require the updated module
        delete requireBackend.cache[requireBackend.resolve("./lambda/saveProgress.js")];
        delete requireBackend.cache[requireBackend.resolve("./lambda/getProgress.js")];

        saveProgress = requireBackend("./lambda/saveProgress.js");
        getProgress = requireBackend("./lambda/getProgress.js");

        authMiddleware.authenticateRequest = originalAuth;
        dynamoMock = mock.method(DynamoDBDocumentClient.prototype, "send");
    });

    afterEach(() => {
        mock.restoreAll();
    });

    it("OPTIONS returns 200 for both", async () => {
        const event = { requestContext: { http: { method: "OPTIONS" } } };
        const res1 = await saveProgress.handler(event);
        assert.equal(res1.statusCode, 200);
        const res2 = await getProgress.handler(event);
        assert.equal(res2.statusCode, 200);
    });

    it("Missing auth header returns 401", async () => {
        authMiddleware.authenticateRequest = async () => {
            const e = new Error("Unauthorized");
            e.statusCode = 401;
            throw e;
        };
        delete requireBackend.cache[requireBackend.resolve("./lambda/saveProgress.js")];
        delete requireBackend.cache[requireBackend.resolve("./lambda/getProgress.js")];
        const localSave = requireBackend("./lambda/saveProgress.js");
        const localGet = requireBackend("./lambda/getProgress.js");

        const event = { headers: {} };
        const res1 = await localSave.handler(event);
        assert.equal(res1.statusCode, 401);
        const res2 = await localGet.handler(event);
        assert.equal(res2.statusCode, 401);
    });

    it("saveProgress: Missing body returns 400", async () => {
        authMiddleware.authenticateRequest = async () => ({ userId: "u1" });
        delete requireBackend.cache[requireBackend.resolve("./lambda/saveProgress.js")];
        const localSave = requireBackend("./lambda/saveProgress.js");
        const res = await localSave.handler({ headers: { authorization: "Bearer valid-token" } });
        assert.equal(res.statusCode, 400);
    });

    it("saveProgress: Invalid JSON body returns 400", async () => {
        authMiddleware.authenticateRequest = async () => ({ userId: "u1" });
        delete requireBackend.cache[requireBackend.resolve("./lambda/saveProgress.js")];
        const localSave = requireBackend("./lambda/saveProgress.js");
        const res = await localSave.handler({
            headers: { authorization: "Bearer valid-token" },
            body: "{bad json"
        });
        assert.equal(res.statusCode, 400);
    });

    it("saveProgress: Missing bookId returns 400", async () => {
        authMiddleware.authenticateRequest = async () => ({ userId: "u1" });
        delete requireBackend.cache[requireBackend.resolve("./lambda/saveProgress.js")];
        const localSave = requireBackend("./lambda/saveProgress.js");
        const res = await localSave.handler({
            headers: { authorization: "Bearer valid-token" },
            body: JSON.stringify({})
        });
        assert.equal(res.statusCode, 400);
    });

    it("saveProgress: Parameter clamping (negative clamped to 0) and success 200", async () => {
        authMiddleware.authenticateRequest = async () => ({ userId: "u1" });
        delete requireBackend.cache[requireBackend.resolve("./lambda/saveProgress.js")];
        const localSave = requireBackend("./lambda/saveProgress.js");

        dynamoMock.mock.mockImplementation(async () => ({}));
        const reqBody = {
            bookId: "b1",
            chapterIndex: -5,
            currentTime: -100,
            totalDuration: -50,
            totalChapters: -10
        };
        const res = await localSave.handler({
            headers: { authorization: "Bearer valid-token" },
            body: JSON.stringify(reqBody)
        });
        assert.equal(res.statusCode, 200);

        const responseBody = JSON.parse(res.body);
        assert.equal(responseBody.message, "Progress saved");
        const prog = responseBody.progress;
        assert.equal(prog.chapterIndex, 0);
        assert.equal(prog.currentTime, 0);
        assert.equal(prog.totalDuration, 0);
        assert.equal(prog.totalChapters, undefined);
    });

    it("getProgress: Successful DB read returns 200", async () => {
        authMiddleware.authenticateRequest = async () => ({ userId: "u1" });
        delete requireBackend.cache[requireBackend.resolve("./lambda/getProgress.js")];
        const localGet = requireBackend("./lambda/getProgress.js");

        dynamoMock.mock.mockImplementation(async () => ({ Items: [{ bookId: "b1", chapterIndex: 1 }] }));
        const res = await localGet.handler({ headers: { authorization: "Bearer valid-token" } });
        assert.equal(res.statusCode, 200);
        const body = JSON.parse(res.body);
        assert.equal(body.progress.length, 1);
        assert.equal(body.progress[0].bookId, "b1");
    });
});
