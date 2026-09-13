function handleLambdaError(error, requestId, corsHeaders = {}) {
    // Log the full error internally
    console.error("Internal Error Details:", {
        name: error.name,
        message: error.message,
        stack: error.stack,
        code: error.code,
        statusCode: error.statusCode,
        requestId: requestId
    });

    // Default timestamp
    const timestamp = new Date().toISOString();
    const resolvedRequestId = requestId || "unknown";

    // Handle 400-499 Client Errors
    if (error.statusCode >= 400 && error.statusCode < 500) {
        return {
            statusCode: error.statusCode,
            headers: {
                ...corsHeaders,
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                success: false,
                error: {
                    code: error.code || "CLIENT_ERROR",
                    message: error.message,
                    timestamp: timestamp,
                    requestId: resolvedRequestId
                }
            })
        };
    }

    // Handle 500+ Internal Errors or Unhandled Exceptions
    return {
        statusCode: 500,
        headers: {
            ...corsHeaders,
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            success: false,
            error: {
                code: error.code || "INTERNAL_SERVER_ERROR",
                message: "An unexpected internal error occurred. Please try again later.",
                timestamp: timestamp,
                requestId: resolvedRequestId
            }
        })
    };
}

module.exports = {
    handleLambdaError
};
