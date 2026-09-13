const { DynamoDBClient } = require("@aws-sdk/client-dynamodb");
const { DynamoDBDocumentClient, ScanCommand } = require("@aws-sdk/lib-dynamodb");
const { getSafeCorsHeaders } = require("../shared/cors.js");

// --- 1. SETUP (Sirf DB chahiye, S3 ki zarurat nahi ab) ---
const dbClient = new DynamoDBClient({ region: "ap-south-1" });
const docClient = DynamoDBDocumentClient.from(dbClient);
const TABLE_NAME = "Vibe_Books";

exports.handler = async (event) => {
    const origin = event.headers?.origin || event.headers?.Origin;
    const corsHeaders = getSafeCorsHeaders(origin);

    // OPTIONS request (CORS) handling
    if (event.requestContext?.http?.method === "OPTIONS") {
        return {
            statusCode: 200,
            headers: corsHeaders
        };
    }

    try {
        console.log("⚡ Fetching Book List (Lite Mode)...");
        
        // Sirf DB Scan karo
        const data = await docClient.send(new ScanCommand({ TableName: TABLE_NAME }));
        
        // Data ko clean karo (Chapters hata do taaki payload chhota rahe)
        const lightBooks = data.Items.map(book => ({
            bookId: book.bookId,
            title: book.title,
            author: book.author,
            cover: book.cover, // Amazon link hai, seedha use hoga
            moods: book.moods,
            genre: book.genre, // ✅ Add genre for frontend filtering & personalization
            totalChapters: book.chapters ? book.chapters.length : 0
        }));

        return {
            statusCode: 200,
            headers: { "Content-Type": "application/json", ...corsHeaders }, // CORS AWS handle karega
            body: JSON.stringify(lightBooks)
        };

    } catch (err) {
        console.error("❌ Error:", err);
        return { statusCode: 500, headers: corsHeaders, body: JSON.stringify({ error: err.message }) };
    }
};