const { DynamoDBClient } = require("@aws-sdk/client-dynamodb");
const { DynamoDBDocumentClient, PutCommand } = require("@aws-sdk/lib-dynamodb");
const { authenticateRequest } = require("../shared/auth-middleware.js");

const client = new DynamoDBClient({
    region: process.env.AWS_REGION || "ap-south-1",
    ...(process.env.NODE_ENV === "test" && {
        endpoint: "http://localhost:8000",
        credentials: { accessKeyId: "test", secretAccessKey: "test" }
    })
});
let docClient = DynamoDBDocumentClient.from(client);

// For testing purposes, allow replacing the docClient
exports.setDocClientForTest = (mockClient) => {
    docClient = mockClient;
};

function toSafeNumber(value, fallback = 0) {
    const number = Number(value);
    return Number.isFinite(number) ? number : fallback;
}

exports.handler = async (event) => {
    const headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
    };

    if (event.requestContext?.http?.method === "OPTIONS") {
        return {
            statusCode: 200,
            headers,
            body: ""
        };
    }

    let user;
    try {
        user = await authenticateRequest(event);
    } catch (error) {
        return {
            statusCode: 401,
            headers,
            body: JSON.stringify({ error: "Unauthorized" })
        };
    }

    if (!event.body) {
        return { statusCode: 400, headers, body: JSON.stringify({ error: "Empty Body" }) };
    }

    let body;
    try {
        body = typeof event.body === "string" ? JSON.parse(event.body) : event.body;
    } catch (error) {
        return { statusCode: 400, headers, body: JSON.stringify({ error: "Invalid JSON" }) };
    }

    // Ignore client-supplied userId and strictly use JWT sub
    const userId = user.userId;
    const bookId = String(body.bookId || "").trim();

    if (!bookId) {
        return {
            statusCode: 400,
            headers,
            body: JSON.stringify({ error: "bookId is required" })
        };
    }

    const chapterIndex = Math.max(0, Math.floor(toSafeNumber(body.chapterIndex, 0)));
    const currentTime = Math.max(0, toSafeNumber(body.currentTime, 0));
    const totalDuration = Math.max(0, toSafeNumber(body.totalDuration, 0));
    const totalChapters = Math.max(0, Math.floor(toSafeNumber(body.totalChapters, 0)));
    const currentChapterFinished = totalDuration > 0 && currentTime >= totalDuration * 0.98;
    const legacyFinishedFlag = typeof body.isFinished === "boolean" ? body.isFinished : false;
    const bookFinished = typeof body.bookFinished === "boolean"
        ? body.bookFinished
        : Boolean(totalChapters && chapterIndex >= totalChapters - 1 && currentChapterFinished)
            || Boolean(!totalChapters && legacyFinishedFlag && currentChapterFinished);
    const lastInteractionAt = body.lastInteractionAt || body.updatedAt || body.lastUpdated || new Date().toISOString();

    const item = {
        userId,
        bookId,
        chapterIndex,
        currentTime,
        totalDuration,
        currentChapterFinished,
        bookFinished,
        lastInteractionAt
    };

    if (totalChapters > 0) {
        item.totalChapters = totalChapters;
    }

    try {
        await docClient.send(new PutCommand({
            TableName: "Vibe_UserProgress",
            Item: item
        }));

        return {
            statusCode: 200,
            headers,
            body: JSON.stringify({ message: "Progress saved", progress: item })
        };
    } catch (error) {
        console.error("DB Error:", error);
        return {
            statusCode: 500,
            headers,
            body: JSON.stringify({ error: error.message })
        };
    }
};
