// ✅ AWS SDK v3
const { DynamoDBClient } = require("@aws-sdk/client-dynamodb");
const { DynamoDBDocumentClient, PutCommand } = require("@aws-sdk/lib-dynamodb");
const { getSafeCorsHeaders } = require("../shared/cors.js");

const client = new DynamoDBClient({});
const dynamo = DynamoDBDocumentClient.from(client);

// 🔥 FIX: Table name ab sahi hai
const TABLE_NAME = "Vibe_Users"; 

exports.handler = async (event) => {
    const origin = event.headers?.origin || event.headers?.Origin;
    const corsHeaders = getSafeCorsHeaders(origin);

    // Headers (AWS Console handle kar raha hai, par safe side rakh lete hain)
    const headers = { "Content-Type": "application/json", ...corsHeaders };

    if (event.requestContext && event.requestContext.http.method === 'OPTIONS') {
        return { statusCode: 200, headers: corsHeaders, body: '' };
    }

    try {
        const body = event.body ? JSON.parse(event.body) : {};

        // --- 🔥 SCENARIO 1: CLERK SYNC ---
        if (body.action === 'sync') {
            const userId = body.userId;
            const name = body.name || "Vibe User";

            if (!userId) {
                return {
                    statusCode: 400,
                    headers,
                    body: JSON.stringify({ error: "Missing userId" })
                };
            }

            // DynamoDB Write
            await dynamo.send(new PutCommand({
                TableName: TABLE_NAME,
                Item: {
                    userId: userId,   
                    name: name,
                    tier: 'free',
                    lastLogin: new Date().toISOString()
                }
            }));

            console.log(`✅ Synced User: ${name}`);

            return {
                statusCode: 200,
                headers,
                body: JSON.stringify({ success: true, message: "User Synced ✅" })
            };
        }

        return {
            statusCode: 401,
            headers,
            body: JSON.stringify({ success: false, error: "Unauthorized" })
        };

    } catch (e) {
        console.error("❌ SERVER ERROR:", e);
        return { 
            statusCode: 500, 
            headers, 
            body: JSON.stringify({ error: "Backend Crash", details: e.message }) 
        };
    }
};
