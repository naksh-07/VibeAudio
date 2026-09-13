import assert from 'node:assert/strict';

/**
 * Returns a promise that resolves after the specified number of milliseconds.
 * Useful for deterministic waiting in tests without relying on real timeouts where possible.
 * @param {number} ms - Milliseconds to sleep.
 * @returns {Promise<void>}
 */
export function mockSleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Builds a simple mock object with a given set of properties.
 * @param {Object} props - Properties to apply to the mock object.
 * @returns {Object}
 */
export function buildMockObject(props = {}) {
    return { ...props };
}

/**
 * Asserts that an actual object contains all properties and values of an expected subset object.
 * @param {Object} actual - The actual object to test.
 * @param {Object} expectedSubset - The expected subset of properties.
 */
export function assertDeepIncludes(actual, expectedSubset) {
    for (const key of Object.keys(expectedSubset)) {
        assert.deepEqual(actual[key], expectedSubset[key], `Property '${key}' did not match.`);
    }
}
