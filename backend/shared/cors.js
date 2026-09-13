/**
 * Centralized CORS and Security Headers utility.
 */

const PROD_REGEX = /^https:\/\/([a-z0-9-]+\.)?vibeaudio\.(pages\.dev|com)$/;
const DEV_REGEX = /^http:\/\/(localhost|127\.0\.0\.1)(:[0-9]+)?$/;
const FALLBACK_ORIGIN = "https://vibeaudio.pages.dev";

function getSafeCorsHeaders(requestOrigin, environment = process.env.NODE_ENV) {
    let allowedOrigin = FALLBACK_ORIGIN;

    if (requestOrigin) {
        if (PROD_REGEX.test(requestOrigin)) {
            allowedOrigin = requestOrigin;
        } else if (environment !== 'production' && DEV_REGEX.test(requestOrigin)) {
            allowedOrigin = requestOrigin;
        }
    }

    return {
        "Access-Control-Allow-Origin": allowedOrigin,
        "Access-Control-Allow-Methods": "GET, POST, PUT, OPTIONS",
        "Access-Control-Allow-Headers": "Authorization, Content-Type, Range, X-Client-Version, X-Request-Id",
        "Access-Control-Expose-Headers": "Content-Range, Content-Length, ETag, X-Request-Id",
        "Access-Control-Max-Age": "86400",
        "Vary": "Origin",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin"
    };
}

module.exports = { getSafeCorsHeaders };
