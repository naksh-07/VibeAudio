import test, { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { OFFLINE_STATES } from '../frontend/src/js/offline-shelf.js';

// Map download errors in alignment with offline-shelf.js and reliability contracts
function mapDownloadError(error, isOnline = true) {
    const isAborted = error?.name === 'AbortError' || String(error?.message || '').toLowerCase().includes('abort');
    const isQuota = error?.name === 'QuotaExceededError' || String(error?.message || '').toLowerCase().includes('quota');

    if (!isOnline) return 'Browser is offline';
    if (isAborted) return 'Download paused';
    if (isQuota) return 'Storage is full on this device. Free some space and try again.';
    if (error instanceof TypeError && error.message.includes('fetch')) return 'Network connection interrupted';
    if (error?.name === 'SecurityError') return 'Storage access restricted';
    return error?.message || 'Download failed';
}

// Download state transition validator
function isValidStateTransition(fromState, toState) {
    const transitions = {
        [OFFLINE_STATES.notDownloaded]: [OFFLINE_STATES.queued],
        [OFFLINE_STATES.queued]: [OFFLINE_STATES.downloading, OFFLINE_STATES.failed, OFFLINE_STATES.notDownloaded],
        [OFFLINE_STATES.downloading]: [OFFLINE_STATES.downloaded, OFFLINE_STATES.failed, OFFLINE_STATES.queued, OFFLINE_STATES.notDownloaded],
        [OFFLINE_STATES.downloaded]: [OFFLINE_STATES.updateAvailable, OFFLINE_STATES.notDownloaded, OFFLINE_STATES.queued],
        [OFFLINE_STATES.updateAvailable]: [OFFLINE_STATES.queued, OFFLINE_STATES.notDownloaded],
        [OFFLINE_STATES.failed]: [OFFLINE_STATES.queued, OFFLINE_STATES.downloading, OFFLINE_STATES.notDownloaded]
    };

    return Boolean(transitions[fromState]?.includes(toState));
}

describe('Download State Machine & Error Mapping Contract Tests', () => {
    describe('OFFLINE_STATES Enum Constants', () => {
        it('should define all canonical offline states', () => {
            assert.equal(OFFLINE_STATES.notDownloaded, 'not_downloaded');
            assert.equal(OFFLINE_STATES.queued, 'queued');
            assert.equal(OFFLINE_STATES.downloading, 'downloading');
            assert.equal(OFFLINE_STATES.downloaded, 'downloaded');
            assert.equal(OFFLINE_STATES.failed, 'failed');
            assert.equal(OFFLINE_STATES.updateAvailable, 'update_available');
        });
    });

    describe('State Transition Rules', () => {
        it('should permit standard happy path transitions', () => {
            assert.ok(isValidStateTransition(OFFLINE_STATES.notDownloaded, OFFLINE_STATES.queued));
            assert.ok(isValidStateTransition(OFFLINE_STATES.queued, OFFLINE_STATES.downloading));
            assert.ok(isValidStateTransition(OFFLINE_STATES.downloading, OFFLINE_STATES.downloaded));
        });

        it('should permit failure and retry transitions', () => {
            assert.ok(isValidStateTransition(OFFLINE_STATES.downloading, OFFLINE_STATES.failed));
            assert.ok(isValidStateTransition(OFFLINE_STATES.failed, OFFLINE_STATES.queued));
            assert.ok(isValidStateTransition(OFFLINE_STATES.queued, OFFLINE_STATES.downloading));
        });

        it('should permit cancellation and removal transitions', () => {
            assert.ok(isValidStateTransition(OFFLINE_STATES.downloading, OFFLINE_STATES.notDownloaded));
            assert.ok(isValidStateTransition(OFFLINE_STATES.queued, OFFLINE_STATES.notDownloaded));
            assert.ok(isValidStateTransition(OFFLINE_STATES.downloaded, OFFLINE_STATES.notDownloaded));
        });

        it('should permit update available detection on downloaded books', () => {
            assert.ok(isValidStateTransition(OFFLINE_STATES.downloaded, OFFLINE_STATES.updateAvailable));
            assert.ok(isValidStateTransition(OFFLINE_STATES.updateAvailable, OFFLINE_STATES.queued));
        });

        it('should reject invalid direct state jumps', () => {
            assert.equal(isValidStateTransition(OFFLINE_STATES.notDownloaded, OFFLINE_STATES.downloaded), false);
            assert.equal(isValidStateTransition(OFFLINE_STATES.notDownloaded, OFFLINE_STATES.updateAvailable), false);
            assert.equal(isValidStateTransition(OFFLINE_STATES.downloaded, OFFLINE_STATES.downloading), false);
        });
    });

    describe('Calm Error Mapping Logic', () => {
        it('should map QuotaExceededError to actionable user advice', () => {
            const quotaErr = new Error('Quota exceeded on device');
            quotaErr.name = 'QuotaExceededError';
            assert.equal(mapDownloadError(quotaErr, true), 'Storage is full on this device. Free some space and try again.');
        });

        it('should map offline network state calmly', () => {
            const fetchErr = new TypeError('Failed to fetch');
            assert.equal(mapDownloadError(fetchErr, false), 'Browser is offline');
        });

        it('should map network interruption when online', () => {
            const fetchErr = new TypeError('Failed to fetch resource');
            assert.equal(mapDownloadError(fetchErr, true), 'Network connection interrupted');
        });

        it('should map user or system aborts as paused', () => {
            const abortErr = new Error('The user aborted a request.');
            abortErr.name = 'AbortError';
            assert.equal(mapDownloadError(abortErr, true), 'Download paused');
        });

        it('should map storage security/permission errors cleanly', () => {
            const secErr = new Error('Permission denied');
            secErr.name = 'SecurityError';
            assert.equal(mapDownloadError(secErr, true), 'Storage access restricted');
        });

        it('should pass through descriptive unknown messages safely', () => {
            const customErr = new Error('Audio file corrupted at source');
            assert.equal(mapDownloadError(customErr, true), 'Audio file corrupted at source');
            assert.equal(mapDownloadError(null, true), 'Download failed');
        });
    });
});
