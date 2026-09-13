import test from "node:test";
import assert from "node:assert";
import { handleLambdaError } from "../backend/shared/error-handler.js";

test("handleLambdaError should sanitize 500 internal errors and provide a safe message", () => {
    // Override console.error temporarily to test its invocation
    const originalConsoleError = console.error;
    let loggedDetails = null;
    console.error = (msg, details) => {
        loggedDetails = details;
    };

    try {
        const fakeDbError = new Error("ResourceNotFoundException: Table Vibe_Books not found");
        fakeDbError.code = "ResourceNotFoundException";

        const requestId = "req-12345";
        const corsHeaders = { "Access-Control-Allow-Origin": "*" };

        const response = handleLambdaError(fakeDbError, requestId, corsHeaders);
        const body = JSON.parse(response.body);

        // Asserts internal masking
        assert.strictEqual(response.statusCode, 500);
        assert.strictEqual(response.headers["Content-Type"], "application/json");
        assert.strictEqual(response.headers["Access-Control-Allow-Origin"], "*");
        assert.strictEqual(body.success, false);
        assert.strictEqual(body.error.code, "ResourceNotFoundException");
        assert.strictEqual(body.error.message, "An unexpected internal error occurred. Please try again later.");
        assert.strictEqual(body.error.requestId, "req-12345");
        assert.ok(body.error.timestamp);

        // Ensure real error message is not in output
        assert.ok(!response.body.includes("Table Vibe_Books not found"));

        // Asserts logger works
        assert.ok(loggedDetails, "console.error should have been called");
        assert.strictEqual(loggedDetails.message, "ResourceNotFoundException: Table Vibe_Books not found");
    } finally {
        console.error = originalConsoleError;
    }
});

test("handleLambdaError should sanitize unhandled exceptions (undefined statusCode)", () => {
    const originalConsoleError = console.error;
    let loggedDetails = null;
    console.error = (msg, details) => {
        loggedDetails = details;
    };

    try {
        const fakeTypeError = new TypeError("Cannot read properties of null (reading 'Item')");

        const response = handleLambdaError(fakeTypeError, "req-9999");
        const body = JSON.parse(response.body);

        assert.strictEqual(response.statusCode, 500);
        assert.strictEqual(body.error.code, "INTERNAL_SERVER_ERROR");
        assert.strictEqual(body.error.message, "An unexpected internal error occurred. Please try again later.");

        assert.ok(!response.body.includes("reading 'Item'"));
        assert.strictEqual(loggedDetails.message, "Cannot read properties of null (reading 'Item')");
    } finally {
        console.error = originalConsoleError;
    }
});

test("handleLambdaError should pass through client errors (400-499) with their original messages", () => {
    const originalConsoleError = console.error;
    let loggedDetails = null;
    console.error = (msg, details) => {
        loggedDetails = details;
    };

    try {
        const fakeClientError = new Error("Invalid format provided");
        fakeClientError.statusCode = 400;
        fakeClientError.code = "ValidationError";

        const response = handleLambdaError(fakeClientError, "req-client");
        const body = JSON.parse(response.body);

        assert.strictEqual(response.statusCode, 400);
        assert.strictEqual(body.success, false);
        assert.strictEqual(body.error.code, "ValidationError");
        assert.strictEqual(body.error.message, "Invalid format provided");
        assert.strictEqual(body.error.requestId, "req-client");

        assert.ok(loggedDetails);
        assert.strictEqual(loggedDetails.statusCode, 400);
    } finally {
        console.error = originalConsoleError;
    }
});

test("handleLambdaError handles missing requestId properly", () => {
    const originalConsoleError = console.error;
    console.error = () => {}; // mock silently

    try {
        const fakeError = new Error("Some other error");
        fakeError.statusCode = 404;

        const response = handleLambdaError(fakeError); // No requestId
        const body = JSON.parse(response.body);

        assert.strictEqual(response.statusCode, 404);
        assert.strictEqual(body.error.requestId, "unknown");
    } finally {
        console.error = originalConsoleError;
    }
});
