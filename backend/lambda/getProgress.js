const { DynamoDBClient } = require("@aws-sdk/client-dynamodb");
const { DynamoDBDocumentClient, QueryCommand } = require("@aws-sdk/lib-dynamodb");
const { authenticateRequest } = require("../shared/auth-middleware.js");

const client = new DynamoDBClient({
    region: process.env.AWS_REGION || "ap-south-1",
    ...(process.env.NODE_ENV === "test" && {
        endpoint: "http://localhost:8000",
        credentials: { accessKeyId: "test", secretAccessKey: "test" }
    })
});
let docClient = DynamoDBDocumentClient.from(client);

exports.setDocClientForTest = (mockClient) => {
    docClient = mockClient;
};

exports.handler = async (event) => {
    const headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
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

    // Ignore client-supplied userId and strictly use JWT sub
    const userId = user.userId;

    try {
        const data = await docClient.send(new QueryCommand({
            TableName: "Vibe_UserProgress",
            KeyConditionExpression: "userId = :u",
            ExpressionAttributeValues: {
                ":u": userId
            }
        }));

        return {
            statusCode: 200,
            headers,
            body: JSON.stringify({ progress: Array.isArray(data.Items) ? data.Items : [] })
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
