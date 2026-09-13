# VibeAudio Backend Hybrid Architecture & REST API Specification
## Document ID: `SPEC-API-001`

**Status:** Authoritative Engineering Baseline  
**Version:** 1.0.0  
**Date:** September 2026  
**Lead Authors:** Backend Architect, Cloud Infrastructure Engineer, Security Lead  
**Target Repository:** `c:\Users\Suraj\Documents\Antigravity\VibeAudio`  
**Cross-References:** [`SEC-BASE-001`](../security/VibeAudio-Backend-Security-Baseline.md), [`PLAN-MIG-001`](./VibeAudio-API-Migration-Plan.md), [`SPEC-SLICE-001`](./VibeAudio-Sanctuary-Vertical-Slice.md), [`QA-STRAT-001`](../qa/VibeAudio-Testing-Strategy.md)

---

## 1. Architectural Overview & Invariants

VibeAudio implements a decoupled **Hybrid Backend Topology** engineered to deliver ultra-low-latency media streaming, instant edge-cached catalog delivery, resilient offline progress synchronization, and hardened authentication.

```mermaid
flowchart TD
    subgraph ClientLayer ["Client Layer (Browser / PWA)"]
        Client["VibeAudio Web Client / PWA\n(Vanilla ESM, Zero Build)"]
    end

    subgraph EdgeLayer ["Cloudflare Edge Gateway (api.vibeaudio.com)"]
        CF_Router["Cloudflare Worker Router\n(/api/v1/*)"]
        CF_Cache[("Cloudflare Edge Cache\n(KV / Cache API)")]
        CF_Stream["Stream Proxy Worker\n(Range & Presigned Auth)"]
    end

    subgraph StorageLayer ["Object Storage Layer"]
        R2_Audio[("Cloudflare R2 Bucket\n(Audio Chunks / M4B / MP3)")]
    end

    subgraph ComputeLayer ["AWS Core Compute (ap-south-1)"]
        ALB_Gateway["API Gateway / Lambda Function URLs\n(IAM & Custom Authorizer)"]
        Lambda_Auth["auth-session.js\n(Clerk JWKS Verify)"]
        Lambda_Progress["user-progress.js\n(LWW Conflict Resolution)"]
        Lambda_Migrate["migrate-guest.js\n(Guest-to-User Merging)"]
        Lambda_Sync["sync-batch.js\n(Bulk Progress Flush)"]
        Lambda_Library["user-library.js\n(Bookmarks & History)"]
    end

    subgraph PersistenceLayer ["Persistence Layer (Storage Agnostic)"]
        Repo_Interface["Repository Abstraction Interface\n(Database Selection Intentionally Deferred)"]
    end

    Client -->|"GET /api/v1/catalog\nGET /api/v1/catalog/:id"| CF_Router
    CF_Router <--> CF_Cache
    Client -->|"GET /api/v1/stream/:bookId/:chapterId"| CF_Stream
    CF_Stream -->|"HTTP 206 Partial Content (Range)"| R2_Audio

    Client -->|"POST /api/v1/auth/session\nGET/PUT /api/v1/user/progress\nPOST /api/v1/user/migrate-guest\nPOST /api/v1/sync/batch\nGET /api/v1/user/library"| ALB_Gateway

    ALB_Gateway --> Lambda_Auth
    ALB_Gateway --> Lambda_Progress
    ALB_Gateway --> Lambda_Migrate
    ALB_Gateway --> Lambda_Sync
    ALB_Gateway --> Lambda_Library

    Lambda_Auth --> Repo_Interface
    Lambda_Progress --> Repo_Interface
    Lambda_Migrate --> Repo_Interface
    Lambda_Sync --> Repo_Interface
    Lambda_Library --> Repo_Interface
```

### 1.1 Critical Architectural Invariants

1. **Hybrid Infrastructure Partitioning**:
   - **Cloudflare Workers (Edge Gateway)**: Terminates client TLS, enforces edge rate limiting, delivers cached static catalog payloads, proxies byte-range audio chunks from Cloudflare R2, and validates stream token signatures.
   - **AWS Lambda (Core Compute)**: Executes high-trust computational logic, verifies Clerk JSON Web Tokens (JWT), processes Last-Write-Wins (LWW) progress reconciliation, and executes guest-to-user migrations.
2. **Database Engine Selection Intentionally Deferred**:
   - In accordance with architectural invariant #2, **no concrete database engine (e.g., PostgreSQL, DynamoDB, MongoDB) is finalized or enforced** in this API contract.
   - The compute layer communicates exclusively through an abstract **Repository Interface** (`IUserRepository`, `IProgressRepository`, `ILibraryRepository`, `ICatalogRepository`). Data models are expressed as strict JSON Schemas independent of underlying storage tables or indexing engines.
3. **Strict Zero-Trust Boundary**:
   - No Lambda function is exposed to the public Internet without JWT validation.
   - No user identity (`userId`) passed via query parameters or unauthenticated request bodies is trusted. All identity is derived directly from verified Clerk cryptographic claims.
4. **Media Range Streaming Compliance**:
   - All audio streaming endpoints MUST support standard RFC 7233 HTTP Byte-Range requests (`Range: bytes=start-end`), responding with `206 Partial Content` to support scrubbing and playback resumption.

---

## 2. Global Standards & Protocol Definitions

### 2.1 Base URLs
- **Edge Gateway Production**: `https://api.vibeaudio.com/api/v1`
- **Edge Gateway Staging**: `https://staging-api.vibeaudio.com/api/v1`
- **Local Development**: `http://localhost:8787/api/v1` (Wrangler local runner)

### 2.2 Standard Request Headers
| Header Name | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `Authorization` | String | Conditional | `Bearer <clerk_jwt>` required for all authenticated endpoints. |
| `Content-Type` | String | Conditional | `application/json` for all request bodies. |
| `X-Client-Version` | String | Yes | Semantic version of frontend client (e.g., `1.4.0`). |
| `X-Request-Id` | String | Optional | UUIDv4 client trace identifier; generated by Edge Worker if omitted. |
| `Range` | String | Conditional | `bytes=start-end` for audio streaming requests. |

### 2.3 Standard Response Headers
| Header Name | Type | Description |
| :--- | :--- | :--- |
| `Content-Type` | String | `application/json; charset=utf-8` or `audio/mpeg` / `audio/mp4`. |
| `X-Request-Id` | String | Propagated or worker-generated trace identifier. |
| `X-Vibe-Compute-Target` | String | `edge-cloudflare-worker` or `aws-lambda-core`. |
| `Cache-Control` | String | Directs intermediate and browser caching behavior. |
| `ETag` | String | Cryptographic entity tag for conditional caching. |
| `Access-Control-Allow-Origin` | String | Strictly bounded origin (`https://vibeaudio.pages.dev` or dev origin). |

### 2.4 Error Response Envelope Schema
All error responses across both Cloudflare Workers and AWS Lambda MUST conform to this canonical JSON schema:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["success", "error"],
  "properties": {
    "success": { "type": "boolean", "const": false },
    "error": {
      "type": "object",
      "required": ["code", "message", "timestamp", "requestId"],
      "properties": {
        "code": { "type": "string" },
        "message": { "type": "string" },
        "details": { "type": "object" },
        "timestamp": { "type": "string", "format": "date-time" },
        "requestId": { "type": "string" }
      }
    }
  }
}
```

---

## 3. Detailed Endpoint Specifications

### 3.1 `GET /api/v1/catalog`
- **Target Environment**: Cloudflare Worker (Edge Gateway)
- **Purpose**: Retrieve the full or genre-filtered public catalog of available audiobooks. Delivers lightweight metadata optimized for landing shelves and library discovery.
- **Authentication**: None (Public)
- **Caching**: Edge Cache: 1 hour (`max-age=3600`), Stale-While-Revalidate: 24 hours (`stale-while-revalidate=86400`). ETag validation enabled.
- **Rate Limiting**: 300 requests per minute per IP address.

#### Query Parameters
| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `genre` | String | No | - | Filter catalog by primary genre (e.g., `Sci-Fi`, `Philosophy`). |
| `mood` | String | No | - | Filter catalog by mood tag (e.g., `Focus`, `Calm`, `Late Night`). |
| `limit` | Integer | No | `50` | Maximum items to return (clamped between 1 and 100). |
| `cursor` | String | No | - | Opaque cursor token for catalog pagination. |

#### Request Headers
```http
GET /api/v1/catalog?genre=Sci-Fi&limit=20 HTTP/1.1
Host: api.vibeaudio.com
X-Client-Version: 1.4.0
Accept: application/json
```

#### Response Schemas
- **Status 200 OK**:
```json
{
  "success": true,
  "data": {
    "books": [
      {
        "bookId": "dune-herbert",
        "title": "Dune",
        "author": "Frank Herbert",
        "narrator": "Scott Brick",
        "coverUrl": "https://media.vibeaudio.com/covers/dune.webp",
        "accentColor": "#C64E00",
        "genre": "Sci-Fi",
        "moods": ["Epic", "Focus"],
        "totalChapters": 24,
        "totalDuration": 75600,
        "publishedYear": 1965
      }
    ],
    "nextCursor": "eyJsYXN0SWQiOiJkdW5lLWhlcmJlcnQifQ==",
    "totalCount": 142
  }
}
```
- **Status 304 Not Modified**: Returned when `If-None-Match` matches current catalog ETag.
- **Status 400 Bad Request**: Invalid query parameters.
```json
{
  "success": false,
  "error": {
    "code": "INVALID_QUERY_PARAMETER",
    "message": "Parameter 'limit' must be an integer between 1 and 100",
    "timestamp": "2026-09-13T20:00:00.000Z",
    "requestId": "req-cf-7a8b9c0d"
  }
}
```

#### Automated Test Cases
1. `CAT-001`: Returns 200 with full book array and correct ETag when no query params are provided.
2. `CAT-002`: Subsequent request with `If-None-Match` returns 304 with empty body.
3. `CAT-003`: Filtering by `?genre=Sci-Fi` returns only books matching that genre.
4. `CAT-004`: Passing `?limit=200` clamps to 100 or returns 400 validation error.

---

### 3.2 `GET /api/v1/catalog/:bookId`
- **Target Environment**: Cloudflare Worker (Edge Gateway)
- **Purpose**: Retrieve comprehensive metadata, chapter breakdown, audio track durations, and media manifest for a specific audiobook.
- **Authentication**: None (Public)
- **Caching**: Edge Cache: 10 minutes (`max-age=600`), Browser Cache: 5 minutes.
- **Rate Limiting**: 300 requests per minute per IP address.

#### Path Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `bookId` | String | Yes | Canonical slug or alphanumeric identifier of the book (e.g., `the-prophet`). |

#### Response Schemas
- **Status 200 OK**:
```json
{
  "success": true,
  "data": {
    "bookId": "the-prophet",
    "title": "The Prophet",
    "author": "Kahlil Gibran",
    "narrator": "Paul O'Neill",
    "coverUrl": "https://media.vibeaudio.com/covers/the-prophet.webp",
    "accentColor": "#8C6A48",
    "genre": "Philosophy",
    "moods": ["Spiritual", "Calm"],
    "description": "A collection of poetic essays dealing with the human condition.",
    "totalChapters": 8,
    "totalDuration": 14400,
    "chapters": [
      {
        "chapterIndex": 0,
        "title": "On Love",
        "duration": 1800,
        "streamEndpoint": "/api/v1/stream/the-prophet/0"
      },
      {
        "chapterIndex": 1,
        "title": "On Marriage",
        "duration": 1650,
        "streamEndpoint": "/api/v1/stream/the-prophet/1"
      }
    ]
  }
}
```
- **Status 404 Not Found**:
```json
{
  "success": false,
  "error": {
    "code": "BOOK_NOT_FOUND",
    "message": "Book with ID 'unknown-slug' was not found in catalog",
    "timestamp": "2026-09-13T20:01:00.000Z",
    "requestId": "req-cf-11223344"
  }
}
```

#### Automated Test Cases
1. `BOOK-001`: Valid `bookId` returns full chapter list with strictly ordered `chapterIndex` (0 to N-1).
2. `BOOK-002`: Missing `bookId` returns 404 with standard error envelope.
3. `BOOK-003`: Invalid characters in `bookId` (`../../etc/passwd`) are rejected with 400 Bad Request.

---

### 3.3 `GET /api/v1/stream/:bookId/:chapterId`
- **Target Environment**: Cloudflare Worker (Stream Proxy Worker)
- **Purpose**: Authenticate streaming requests and proxy raw audio byte ranges directly from Cloudflare R2 bucket with zero buffering and low time-to-first-byte (TTFB < 45ms).
- **Authentication**: Signed Stream Token (`?token=<hmac_token>`) or Session Bearer Token.
- **Caching**: Partial content is cached conditionally at Cloudflare Edge based on Cache-Control directives from R2 (`public, max-age=604800, immutable`).
- **Rate Limiting**: 600 requests per minute per IP (allowing media chunk seeking).

#### Path & Query Parameters
| Parameter | Location | Type | Required | Description |
| :--- | :--- | :--- | :--- | :--- |
| `bookId` | Path | String | Yes | Book identifier. |
| `chapterId` | Path | Integer | Yes | 0-indexed chapter index. |
| `token` | Query | String | Yes | HMAC-SHA256 signed token generated by catalog manifest. |
| `Range` | Header | String | Optional | HTTP Range specification (e.g., `bytes=0-1048575`). |

#### Request Headers
```http
GET /api/v1/stream/the-prophet/0?token=a1b2c3d4e5f6... HTTP/1.1
Host: api.vibeaudio.com
Range: bytes=0-1048575
User-Agent: VibeAudio-PWA/1.4.0
```

#### Response Schemas
- **Status 206 Partial Content**:
```http
HTTP/1.1 206 Partial Content
Content-Type: audio/mp4
Content-Range: bytes 0-1048575/18432000
Content-Length: 1048576
Accept-Ranges: bytes
Cache-Control: public, max-age=604800, immutable
ETag: "w/r2-the-prophet-ch0-v1"
X-Vibe-Compute-Target: edge-cloudflare-worker

<binary audio stream data>
```
- **Status 401 Unauthorized**: Invalid or expired stream token.
```json
{
  "success": false,
  "error": {
    "code": "STREAM_TOKEN_INVALID",
    "message": "Audio stream authorization token has expired or is invalid",
    "timestamp": "2026-09-13T20:02:00.000Z",
    "requestId": "req-cf-streaming-01"
  }
}
```
- **Status 416 Range Not Satisfiable**: Requested range exceeds media file byte length.
```http
HTTP/1.1 416 Range Not Satisfiable
Content-Range: bytes */18432000
```

#### Automated Test Cases
1. `STR-001`: Request with valid token and `bytes=0-1024` returns 206 with exactly 1025 bytes.
2. `STR-002`: Missing or expired token returns 401 Unauthorized.
3. `STR-003`: Requesting out-of-bounds byte range returns 416 Range Not Satisfiable.
4. `STR-004`: Preflight `OPTIONS` returns strict CORS headers (`Access-Control-Allow-Origin: https://vibeaudio.pages.dev`, `Access-Control-Expose-Headers: Content-Range, Content-Length`).

---

### 3.4 `POST /api/v1/auth/session`
- **Target Environment**: AWS Lambda (Core Compute)
- **Purpose**: Exchange a client-side Clerk JWT for a verified backend session, ensure user profile persistence in the abstract repository, and synchronize user identity.
- **Authentication**: Clerk Bearer Token (`Authorization: Bearer <clerk_jwt>`).
- **Idempotency**: Idempotent. Subsequent calls refresh session metadata without mutating canonical creation timestamps.
- **Rate Limiting**: 60 requests per minute per IP.

#### Request Headers
```http
POST /api/v1/auth/session HTTP/1.1
Host: api.vibeaudio.com
Authorization: Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6Imluc18...
Content-Type: application/json
X-Client-Version: 1.4.0
```

#### Request Body Schema
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["clientTimestamp"],
  "properties": {
    "clientTimestamp": { "type": "string", "format": "date-time" },
    "deviceMeta": {
      "type": "object",
      "properties": {
        "platform": { "type": "string" },
        "userAgent": { "type": "string" }
      }
    }
  }
}
```

#### Response Schemas
- **Status 200 OK**:
```json
{
  "success": true,
  "data": {
    "userId": "user_2N9xK8LmP4qR1vT7wXyZ",
    "name": "Suraj",
    "email": "suraj@example.com",
    "tier": "member",
    "sessionExpiresAt": "2026-09-14T20:00:00.000Z",
    "syncedAt": "2026-09-13T20:03:00.000Z"
  }
}
```
- **Status 401 Unauthorized**: Missing, forged, or expired Clerk JWT.
```json
{
  "success": false,
  "error": {
    "code": "AUTH_TOKEN_INVALID",
    "message": "Clerk JWT signature verification failed via JWKS",
    "timestamp": "2026-09-13T20:03:05.000Z",
    "requestId": "req-aws-auth-01"
  }
}
```

#### Automated Test Cases
1. `AUTH-001`: Valid Clerk JWT signed by Clerk development/production JWKS returns 200 with synced user profile.
2. `AUTH-002`: Expired JWT returns 401 with `AUTH_TOKEN_EXPIRED`.
3. `AUTH-003`: Request without Authorization header returns 401 with `AUTH_HEADER_MISSING`.
4. `AUTH-004`: Verification that legacy bypass codes (`VIBE2026`, `ADMIN_GOD`) return 401 Unauthorized.

---

### 3.5 `GET /api/v1/user/progress`
- **Target Environment**: AWS Lambda (Core Compute)
- **Purpose**: Retrieve the user's complete or book-filtered playback progress records. All records are resolved using Last-Write-Wins (LWW) freshness timestamps.
- **Authentication**: Verified Clerk Bearer Token. Identity is extracted strictly from the token's `sub` claim; query parameters cannot override caller identity.
- **Caching**: Private, No-Cache (`Cache-Control: private, no-cache, no-store`).
- **Rate Limiting**: 120 requests per minute per user.

#### Query Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `bookId` | String | No | If provided, returns progress only for this specific book. |

#### Response Schemas
- **Status 200 OK**:
```json
{
  "success": true,
  "data": {
    "progress": [
      {
        "bookId": "the-prophet",
        "chapterIndex": 2,
        "currentTime": 420.5,
        "totalDuration": 1800.0,
        "totalChapters": 8,
        "currentChapterFinished": false,
        "bookFinished": false,
        "lastInteractionAt": "2026-09-13T19:45:12.345Z",
        "version": 4
      }
    ]
  }
}
```
- **Status 401 Unauthorized**: Missing or invalid Authorization header.

#### Automated Test Cases
1. `PROG-GET-001`: Returns all progress items matching caller's authenticated `sub` ID.
2. `PROG-GET-002`: Passing `?userId=attacker` is IGNORED; only the authenticated user's records are returned (preventing BOLA).
3. `PROG-GET-003`: Requesting a specific `?bookId=the-prophet` filters the response array to that book.

---

### 3.6 `PUT /api/v1/user/progress`
- **Target Environment**: AWS Lambda (Core Compute)
- **Purpose**: Upsert a single audiobook playback progress record. Implements strict Last-Write-Wins (LWW) monotonic freshness verification to prevent older cloud or client state from overwriting newer listening progress.
- **Authentication**: Verified Clerk Bearer Token.
- **Idempotency**: Fully idempotent based on `lastInteractionAt` and monotonic versioning.
- **Rate Limiting**: 180 requests per minute per user (supports frequent playback checkpoints).

#### Request Body Schema
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": [
    "bookId",
    "chapterIndex",
    "currentTime",
    "totalDuration",
    "lastInteractionAt"
  ],
  "properties": {
    "bookId": { "type": "string", "minLength": 1 },
    "chapterIndex": { "type": "integer", "minimum": 0 },
    "currentTime": { "type": "number", "minimum": 0 },
    "totalDuration": { "type": "number", "minimum": 0 },
    "totalChapters": { "type": "integer", "minimum": 1 },
    "currentChapterFinished": { "type": "boolean" },
    "bookFinished": { "type": "boolean" },
    "lastInteractionAt": { "type": "string", "format": "date-time" }
  }
}
```

#### Conflict Resolution Logic (LWW)
```mermaid
flowchart TD
    Start["Incoming PUT /api/v1/user/progress"] --> Fetch["Fetch existing cloud record for (userId, bookId)"]
    Fetch --> Exists{"Record exists?"}
    Exists -- No --> Save["Persist incoming record\nSet version = 1\nReturn 200 OK"]
    Exists -- Yes --> Compare{"incoming.lastInteractionAt > existing.lastInteractionAt ?"}
    Compare -- Yes --> Overwrite["Persist incoming record\nIncrement version\nReturn 200 OK"]
    Compare -- No --> Reject["Reject mutation\nReturn 409 Conflict with current cloud state"]
```

#### Response Schemas
- **Status 200 OK**:
```json
{
  "success": true,
  "data": {
    "status": "persisted",
    "progress": {
      "bookId": "the-prophet",
      "chapterIndex": 2,
      "currentTime": 420.5,
      "totalDuration": 1800.0,
      "totalChapters": 8,
      "currentChapterFinished": false,
      "bookFinished": false,
      "lastInteractionAt": "2026-09-13T19:45:12.345Z",
      "version": 5
    }
  }
}
```
- **Status 409 Conflict**: Returned when incoming `lastInteractionAt` is older than existing record.
```json
{
  "success": false,
  "error": {
    "code": "STALE_PROGRESS_CONFLICT",
    "message": "Incoming progress timestamp is older than existing cloud record",
    "timestamp": "2026-09-13T20:04:00.000Z",
    "requestId": "req-aws-prog-02"
  },
  "currentRecord": {
    "bookId": "the-prophet",
    "chapterIndex": 3,
    "currentTime": 12.0,
    "lastInteractionAt": "2026-09-13T19:50:00.000Z"
  }
}
```

#### Automated Test Cases
1. `PROG-PUT-001`: Valid newer timestamp overwrites record and increments version.
2. `PROG-PUT-002`: Outdated timestamp returns 409 Conflict alongside current cloud record.
3. `PROG-PUT-003`: Current chapter marked finished automatically when `currentTime >= totalDuration * 0.98`.

---

### 3.7 `POST /api/v1/user/migrate-guest`
- **Target Environment**: AWS Lambda (Core Compute)
- **Purpose**: Migrate an anonymous/guest user's local listening progress, bookmarks, and history into their newly authenticated account upon sign-up or sign-in, without overwriting newer authenticated records.
- **Authentication**: Verified Clerk Bearer Token.
- **Idempotency**: Fully idempotent; running repeatedly merges monotonically.
- **Rate Limiting**: 20 requests per minute per user.

#### Request Body Schema
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["guestProgress"],
  "properties": {
    "guestProgress": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["bookId", "chapterIndex", "currentTime", "lastInteractionAt"],
        "properties": {
          "bookId": { "type": "string" },
          "chapterIndex": { "type": "integer", "minimum": 0 },
          "currentTime": { "type": "number", "minimum": 0 },
          "totalDuration": { "type": "number" },
          "totalChapters": { "type": "integer" },
          "lastInteractionAt": { "type": "string", "format": "date-time" }
        }
      }
    }
  }
}
```

#### Response Schemas
- **Status 200 OK**:
```json
{
  "success": true,
  "data": {
    "totalSubmitted": 5,
    "migratedCount": 3,
    "skippedCount": 2,
    "reasons": {
      "staleComparedToExistingUserProgress": 2
    },
    "completedAt": "2026-09-13T20:05:00.000Z"
  }
}
```
- **Status 400 Bad Request**: Invalid payload format or array length exceeds 100 items.

#### Automated Test Cases
1. `MIG-001`: Guest items for books not in user account are inserted directly.
2. `MIG-002`: Guest items older than user cloud records are skipped and recorded in `reasons`.
3. `MIG-003`: Guest items newer than user cloud records supersede them via LWW rule.

---

### 3.8 `POST /api/v1/sync/batch`
- **Target Environment**: AWS Lambda (Core Compute)
- **Purpose**: Bulk-synchronize offline playback progress accumulated during airplane or tunnel listening sessions. Triggered by Service Worker Background Sync or network reconnection.
- **Authentication**: Verified Clerk Bearer Token.
- **Idempotency**: Idempotent batch processing with per-item status reporting.
- **Rate Limiting**: 60 requests per minute per user.

#### Request Body Schema
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["batchId", "entries"],
  "properties": {
    "batchId": { "type": "string", "format": "uuid" },
    "entries": {
      "type": "array",
      "maxItems": 50,
      "items": {
        "type": "object",
        "required": [
          "bookId",
          "chapterIndex",
          "currentTime",
          "totalDuration",
          "lastInteractionAt"
        ],
        "properties": {
          "bookId": { "type": "string" },
          "chapterIndex": { "type": "integer" },
          "currentTime": { "type": "number" },
          "totalDuration": { "type": "number" },
          "lastInteractionAt": { "type": "string", "format": "date-time" }
        }
      }
    }
  }
}
```

#### Response Schemas
- **Status 200 OK**:
```json
{
  "success": true,
  "data": {
    "batchId": "a8f3b2c1-d4e5-4a6b-8c7d-9e0f1a2b3c4d",
    "processed": 4,
    "applied": 3,
    "rejected": [
      {
        "bookId": "the-prophet",
        "reason": "STALE_TIMESTAMP",
        "cloudTimestamp": "2026-09-13T19:50:00.000Z"
      }
    ],
    "syncedAt": "2026-09-13T20:06:00.000Z"
  }
}
```

#### Automated Test Cases
1. `SYNC-001`: Batch with multiple items updates all newer records in a single transactional or atomic operation.
2. `SYNC-002`: Items exceeding 50 limit return 400 Bad Request.
3. `SYNC-003`: Malformed item in batch does not corrupt other valid items in the batch.

---

### 3.9 `GET /api/v1/user/library`
- **Target Environment**: AWS Lambda (Core Compute)
- **Purpose**: Retrieve user-curated library items, including saved bookmarks, custom audio notes, favorite books, and recently completed audiobooks.
- **Authentication**: Verified Clerk Bearer Token.
- **Caching**: Private, No-Cache.
- **Rate Limiting**: 120 requests per minute per user.

#### Response Schemas
- **Status 200 OK**:
```json
{
  "success": true,
  "data": {
    "favorites": ["the-prophet", "dune-herbert"],
    "bookmarks": [
      {
        "bookmarkId": "bm-01",
        "bookId": "the-prophet",
        "chapterIndex": 1,
        "timecode": 345.2,
        "note": "Remarkable passage on self-knowledge",
        "createdAt": "2026-09-13T18:20:00.000Z"
      }
    ],
    "finishedBooks": [
      {
        "bookId": "the-prophet",
        "finishedAt": "2026-09-10T14:15:00.000Z"
      }
    ],
    "lastUpdated": "2026-09-13T20:00:00.000Z"
  }
}
```

#### Automated Test Cases
1. `LIB-001`: Returns empty arrays for new users with no prior bookmarks.
2. `LIB-002`: Properly orders bookmarks chronologically by `createdAt` descending.
3. `LIB-003`: Rejects unauthenticated requests with 401 Unauthorized.

---

## 4. Observability, Logging & Error Taxonomy

### 4.1 Structured Log Schema
All backend components (Cloudflare Workers and AWS Lambda) MUST emit structured JSON logs to stdout:

```json
{
  "timestamp": "2026-09-13T20:07:00.123Z",
  "level": "INFO",
  "environment": "production",
  "service": "vibeaudio-edge-gateway",
  "requestId": "req-cf-7a8b9c0d",
  "http": {
    "method": "GET",
    "path": "/api/v1/catalog",
    "status": 200,
    "durationMs": 14.2,
    "clientIp": "198.51.100.42",
    "userAgent": "Mozilla/5.0..."
  },
  "user": {
    "id": "anonymous",
    "tier": "guest"
  },
  "cache": {
    "status": "HIT",
    "edgeTtl": 3600
  }
}
```

### 4.2 Standard Error Codes Taxonomy
| Error Code | HTTP Status | Description |
| :--- | :--- | :--- |
| `AUTH_HEADER_MISSING` | 401 | `Authorization` header omitted from request. |
| `AUTH_TOKEN_INVALID` | 401 | Clerk JWT signature verification failed. |
| `AUTH_TOKEN_EXPIRED` | 401 | Clerk JWT expiration claim (`exp`) is in the past. |
| `STREAM_TOKEN_INVALID` | 401 | Audio stream presigned token invalid or tampered with. |
| `BOOK_NOT_FOUND` | 404 | Requested `bookId` does not exist in catalog repository. |
| `STALE_PROGRESS_CONFLICT`| 409 | Incoming progress write has an older timestamp than existing state. |
| `RATE_LIMIT_EXCEEDED` | 429 | IP or User rate limit quota breached. |
| `INTERNAL_COMPUTE_ERROR`| 500 | Unhandled exception in worker or lambda (details masked). |

---

## 5. Summary Matrix: Hybrid Endpoints

| Method | Path | Target Environment | Auth Model | Caching Strategy | Rate Limit |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/catalog` | Cloudflare Worker | Public | Edge 1h, SWR 24h | 300 / min / IP |
| `GET` | `/api/v1/catalog/:bookId` | Cloudflare Worker | Public | Edge 10m, Browser 5m | 300 / min / IP |
| `GET` | `/api/v1/stream/:bookId/:chapterId` | Cloudflare Worker | Signed Token | Range proxy / Edge Cache | 600 / min / IP |
| `POST`| `/api/v1/auth/session` | AWS Lambda | Clerk JWT | Private, No-Cache | 60 / min / IP |
| `GET` | `/api/v1/user/progress` | AWS Lambda | Clerk JWT | Private, No-Cache | 120 / min / User |
| `PUT` | `/api/v1/user/progress` | AWS Lambda | Clerk JWT | Private, No-Cache | 180 / min / User |
| `POST`| `/api/v1/user/migrate-guest` | AWS Lambda | Clerk JWT | Private, No-Cache | 20 / min / User |
| `POST`| `/api/v1/sync/batch` | AWS Lambda | Clerk JWT | Private, No-Cache | 60 / min / User |
| `GET` | `/api/v1/user/library` | AWS Lambda | Clerk JWT | Private, No-Cache | 120 / min / User |
