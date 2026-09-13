# VibeAudio Playwright Cross-Browser Test Suite Specification
## Document ID: `QA-E2E-001`

**Status:** Authoritative Engineering Baseline  
**Version:** 1.0.0  
**Date:** September 2026  
**Lead Authors:** E2E Automation Lead, Browser Infrastructure Engineer, QA Architect  
**Target Repository:** `c:\Users\Suraj\Documents\Antigravity\VibeAudio`  
**Cross-References:** [`QA-STRAT-001`](./VibeAudio-Testing-Strategy.md), [`QA-GATES-001`](./VibeAudio-Release-Gates.md), [`SPEC-API-001`](../implementation/VibeAudio-Backend-Hybrid-API-Spec.md)

---

## 1. Test Architecture & Browser Matrix

VibeAudio requires comprehensive validation across diverse rendering engines, audio hardware abstractions, and touch interfaces. Playwright serves as the automated cross-browser testing harness.

### 1.1 Multi-Platform Browser Matrix

| Target Name | Engine | Viewport | DPR | Device Emulation | User-Agent Type |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Desktop Chromium** | Blink (V8) | 1920 x 1080 | 1.0 | Standard Desktop | Chrome Desktop |
| **Desktop WebKit** | WebKit (JSC) | 1440 x 900 | 2.0 | Mac Safari Desktop | Safari Desktop |
| **Desktop Firefox** | Gecko (SpiderMonkey) | 1920 x 1080 | 1.0 | Standard Desktop | Firefox Desktop |
| **Mobile Chrome** | Blink (Touch) | 393 x 851 | 2.75 | Google Pixel 5 | Android Mobile Chrome |
| **Mobile Safari** | WebKit (Touch) | 390 x 844 | 3.0 | Apple iPhone 13 | iOS Mobile Safari |

---

## 2. Local Test Harness & Zero-Build Static Server Setup

### 2.1 Static Server Configuration
In alignment with VibeAudio's zero-build invariant, the test runner serves the repository statically without bundling or compilation:

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 45000,
  expect: { timeout: 7000 },
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: [
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['list']
  ],
  use: {
    baseURL: 'http://localhost:8080',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure'
  },
  webServer: {
    command: 'npx http-server ./frontend -p 8080 -c-1 --silent',
    url: 'http://localhost:8080/src/pages/app.html',
    reuseExistingServer: !process.env.CI,
    timeout: 15000
  },
  projects: [
    { name: 'chromium-desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'webkit-desktop', use: { ...devices['Desktop Safari'] } },
    { name: 'firefox-desktop', use: { ...devices['Desktop Firefox'] } },
    { name: 'mobile-chrome-pixel5', use: { ...devices['Pixel 5'] } },
    { name: 'mobile-safari-iphone13', use: { ...devices['iPhone 13'] } }
  ]
});
```

### 2.2 Reusable Fixtures & Storage State Initialization
```typescript
// tests/e2e/fixtures/vibe-fixture.ts
import { test as base, Page } from '@playwright/test';

export const test = base.extend<{ authenticatedPage: Page; cleanGuestPage: Page }>({
  cleanGuestPage: async ({ page }, use) => {
    await page.goto('/src/pages/app.html');
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await page.reload();
    await use(page);
  },
  authenticatedPage: async ({ page }, use) => {
    await page.goto('/src/pages/app.html');
    await page.evaluate(() => {
      localStorage.setItem('vibe_user_id', 'usr_test_e2e_playwright');
      localStorage.setItem('vibe_user_name', 'Playwright Tester');
      localStorage.setItem('vibe_auth_token', 'mock_valid_e2e_jwt_token');
    });
    await page.reload();
    await use(page);
  }
});
```

---

## 3. Concrete Test Specifications

---

### 3.1 Spec 1: `player.spec.ts` (Audio Player Subsystem)
- **File Location**: `tests/e2e/player.spec.ts`
- **Objective**: Verify complete audio playback controls, seeking scrubber, chapter transitions, mini-player docking, full-player overlay, and keyboard shortcuts.

#### Test Scenarios & Assertions
1. **Scenario 1.1: Play/Pause Toggle & Audio State Verification**:
   - Navigate to `#home`. Click first book card.
   - Assert `#view-player` becomes visible (`.active` class present).
   - Click `#btn-play-pause`.
   - Assert `<audio id="audio-element">` has `paused === false` and `currentTime > 0`.
   - Click `#btn-play-pause` again.
   - Assert audio element `paused === true`.
2. **Scenario 1.2: Scrubber Dragging & Seek Precision**:
   - Locate seek track `.player-scrubber-track`.
   - Emulate mouse drag from 10% to 60% of track bounding box width.
   - Assert `#audio-element.currentTime` updates proportionally to $\approx 60\%$ of total duration.
   - Assert UI timecode display (`#current-timecode`) updates with `JetBrains Mono` font.
3. **Scenario 1.3: Chapter Navigation Drawer**:
   - Click chapter list toggle button `#btn-chapter-drawer`.
   - Assert chapter drawer slides open.
   - Click Chapter 3 (`.chapter-item:nth-child(3)`).
   - Assert active track changes; current chapter title displays Chapter 3 name.
   - Assert audio restarts from `currentTime === 0` for the new chapter.
4. **Scenario 1.4: Mini-Player Docking & Full Player Expand**:
   - Click minimize button `#btn-player-minimize`.
   - Assert `#view-player` transitions to hidden.
   - Assert `#mini-player` dock appears floating `16px` from viewport bottom.
   - Assert mini-player shows live track title, play/pause state, and 2px progress bar.
   - Click mini-player card body.
   - Assert `#view-player` re-expands smoothly to full screen.
5. **Scenario 1.5: Global Keyboard Shortcuts**:
   - Press `Space`: Toggles Play/Pause.
   - Press `ArrowRight`: Advances playback by 15 seconds.
   - Press `ArrowLeft`: Rewinds playback by 15 seconds.
   - Press `KeyM`: Toggles mute state.

---

### 3.2 Spec 2: `offline.spec.ts` (Offline Shelf & OPFS Engine)
- **File Location**: `tests/e2e/offline.spec.ts`
- **Objective**: Verify book chapter downloads to local Origin Private File System (OPFS), network disconnection handling, and offline playback.

#### Test Scenarios & Assertions
1. **Scenario 2.1: Chapter Download & Storage State Transition**:
   - Open book details view.
   - Click *"Save to Device"* button (`#btn-download-book`).
   - Intercept network calls to `/api/v1/stream/*`; provide synthetic audio byte streams.
   - Assert progress indicator transitions: `queued` ➔ `downloading (0-100%)` ➔ `saved`.
   - Query OPFS storage via `page.evaluate()` to verify binary file presence at `offline-audio/...`.
2. **Scenario 2.2: Offline Playback Without Network**:
   - Emulate complete network offline:
     ```typescript
     await context.setOffline(true);
     ```
   - Navigate to `#offline` view.
   - Assert downloaded book card is displayed with green offline badge.
   - Click downloaded book; press Play.
   - Assert audio plays from local `blob:` or `opfs:` URL without network requests.
   - Assert zero unhandled network exceptions in console.
3. **Scenario 2.3: Storage Quota & Deletion**:
   - Click *"Remove from Device"* (`#btn-delete-offline`).
   - Assert book is removed from `#offline` view.
   - Assert OPFS directory entry is unlinked and storage quota reclaimed.

---

### 3.3 Spec 3: `sync.spec.ts` (LWW Progress & Background Sync)
- **File Location**: `tests/e2e/sync.spec.ts`
- **Objective**: Verify Last-Write-Wins (LWW) conflict resolution, offline progress queuing, and automatic cloud flush upon network reconnection.

#### Test Scenarios & Assertions
1. **Scenario 3.1: Online Real-Time Progress Persistence**:
   - Route interception: Intercept `PUT /api/v1/user/progress`.
   - Start playback. Advance time to 45 seconds.
   - Wait 6 seconds for periodic auto-save throttle.
   - Assert outgoing PUT request contains `currentTime: 45` and valid ISO `lastInteractionAt`.
2. **Scenario 3.2: Offline Queue Accumulation & Reconnection Flush**:
   - Set context offline: `await context.setOffline(true)`.
   - Listen to track; advance from 45s to 120s.
   - Inspect IndexedDB `vibeaudio-sync-v1` via `page.evaluate()`.
   - Assert 1 pending entry exists in `sync_progress_queue`.
   - Restore network: `await context.setOffline(false)`.
   - Intercept `POST /api/v1/sync/batch`.
   - Trigger `window.dispatchEvent(new Event('online'))`.
   - Assert batch sync payload received with `currentTime: 120`.
   - Assert IndexedDB sync queue is cleared upon successful 200 OK.
3. **Scenario 3.3: LWW Cloud Conflict Resolution**:
   - Simulate cloud having a newer timestamp (`2026-09-13T20:30:00Z`) than local device (`2026-09-13T20:15:00Z`).
   - Trigger sync. Mock server responds with 409 Conflict and latest cloud position.
   - Assert client adopts cloud position without overwriting with stale local data.

---

### 3.4 Spec 4: `visual-qa.spec.ts` (Stitch Visual Regression)
- **File Location**: `tests/e2e/visual-qa.spec.ts`
- **Objective**: Verify pixel-perfect fidelity across all 8 registered Stitch design screens against baseline screenshots with strict diff thresholds.

#### Test Scenarios & Baselines
1. **Registered Screens Covered**:
   - `SCR-01`: Landing Marketing Page (`frontend/index.html`)
   - `SCR-02`: Home Sanctuary Shelf (`#home`)
   - `SCR-03`: Library & Bookmarks View (`#library`)
   - `SCR-04`: On This Device Vault (`#offline`)
   - `SCR-05`: Full Player Overlay (`#view-player`)
   - `SCR-06`: User Profile & Storage Management (`#profile`)
   - `SCR-07`: Floating Mini-Player Dock (`#mini-player`)
   - `SCR-08`: Mobile Navigation Drawer (`#mobile-drawer`)

#### Screenshot Assertion Implementation
```typescript
// tests/e2e/visual-qa.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Stitch Visual Regression Benchmarks', () => {
  test('SCR-02: Home Sanctuary Shelf Parity', async ({ page }) => {
    await page.goto('/src/pages/app.html#home');
    await page.waitForSelector('.book-shelf-grid');
    // Freeze animations & cursor
    await page.addStyleTag({ content: '*, *::before, *::after { animation: none !important; transition: none !important; }' });
    await expect(page).toHaveScreenshot('home-shelf-baseline.png', {
      maxDiffPixelRatio: 0.005, // < 0.5% tolerance
      threshold: 0.2
    });
  });

  test('SCR-05: Full Player Overlay Parity', async ({ page }) => {
    await page.goto('/src/pages/app.html#player');
    await page.waitForSelector('#view-player.active');
    await expect(page).toHaveScreenshot('full-player-baseline.png', {
      maxDiffPixelRatio: 0.005
    });
  });
});
```

---

## 4. Network Interception Rules & Mocking Contracts

All E2E tests isolate frontend behavior using Playwright's `page.route()` mechanism to eliminate external cloud dependencies:

```typescript
export async function setupDefaultMocks(page: Page) {
  // Mock Catalog
  await page.route('**/api/v1/catalog', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        data: {
          books: [
            {
              bookId: 'e2e-the-prophet',
              title: 'The Prophet',
              author: 'Kahlil Gibran',
              coverUrl: '/src/assets/sample-cover.webp',
              totalChapters: 4,
              totalDuration: 7200
            }
          ]
        }
      })
    });
  });

  // Mock Audio Streaming (Byte Range Support)
  await page.route('**/api/v1/stream/**', (route) => {
    const syntheticBuffer = Buffer.alloc(1024 * 1024); // 1MB mock audio
    route.fulfill({
      status: 206,
      contentType: 'audio/mp4',
      headers: {
        'Accept-Ranges': 'bytes',
        'Content-Range': `bytes 0-1048575/${syntheticBuffer.length}`,
        'Content-Length': '1048576'
      },
      body: syntheticBuffer
    });
  });
}
```

---

## 5. Expected Failure Modes & Diagnostic Runbook

| Failure Mode | Common Cause | Diagnostic Remedy |
| :--- | :--- | :--- |
| **Audio Timeout (`expect(audio.currentTime).toBeGreaterThan(0)`)** | Autoplay policy restriction in headless browser | Ensure `launchOptions: { args: ['--autoplay-policy=no-user-gesture-required'] }` is configured. |
| **OPFS `NotFoundError`** | Headless WebKit running in insecure HTTP context | Ensure `baseURL` is `localhost` or `127.0.0.1` (secure context required for OPFS). |
| **Visual Diff Breached (> 0.5%)** | Dynamic font rendering variance or scrollbars | Ensure `page.addStyleTag({ content: '::-webkit-scrollbar { display: none; }' })` is injected. |
