const { jwtVerify, createRemoteJWKSet } = require('jose');

let JWKS;

async function authenticateRequest(event) {
    const authHeader = event.headers?.authorization || event.headers?.Authorization;
    if (!authHeader || !authHeader.toLowerCase().startsWith('bearer ')) {
        const error = new Error('Missing or invalid Authorization header');
        error.statusCode = 401;
        throw error;
    }

    const token = authHeader.substring(7);

    if (!JWKS) {
        const jwksUrl = process.env.CLERK_JWKS_URL || 'https://quality-hare-99.clerk.accounts.dev/.well-known/jwks.json';
        JWKS = createRemoteJWKSet(new URL(jwksUrl));
    }

    try {
        const options = {};
        if (process.env.CLERK_ISSUER) {
            options.issuer = process.env.CLERK_ISSUER;
        }

        const { payload } = await jwtVerify(token, JWKS, options);

        if (!payload.sub) {
            const error = new Error('Missing sub claim');
            error.statusCode = 401;
            throw error;
        }

        return {
            userId: payload.sub,
            claims: payload
        };
    } catch (err) {
        const error = new Error(err.message || 'Invalid token');
        error.statusCode = 401;
        throw error;
    }
}

// Allow overriding JWKS for testing
function setJWKSForTest(customJWKS) {
    JWKS = customJWKS;
}

module.exports = { authenticateRequest, setJWKSForTest };
