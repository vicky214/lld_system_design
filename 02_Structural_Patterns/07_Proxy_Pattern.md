# Proxy Pattern

## Category: Structural Pattern

---

## 1. Core Intent & Definition
Provide a surrogate or placeholder for another object to control access to it, support lazy initialization, logging, caching, or access control.

---

## 2. Real-Life Problem & Industry Scenario
### The Problem:
Instantiating heavy third-party services (e.g. fetching gigabyte-sized satellite images from remote APIs, opening expensive database cursors) before they are actually needed degrades startup latency. Furthermore, auditing and caching access directly inside business logic violates Single Responsibility.

### Real-World Industry Example:
High-Resolution Image / Cloud Asset Loader with Redis Caching and RBAC Protection. A proxy intercepts asset downloads, enforces user security permissions, checks in-memory cache, and only lazily downloads the raw binary from S3 upon cache misses.

---

## 3. Architecture & Visual Flow Diagram
```
+-------------------------------------------------------+
|                       AssetLoader                     | (Subject Interface)
+-------------------------------------------------------+
| + loadAsset(assetId, userRole): Promise<Buffer>       |
+-------------------------------------------------------+
                           ▲
             ┌─────────────┴─────────────┐
             │                           │
+-------------------------+ +-------------------------+
|     RealAssetLoader     | |    CachedSecureProxy    |
+-------------------------+ +-------------------------+
| + loadAsset() -> S3 DL  | | - realLoader: Subject   |
+-------------------------+ | - cache: Map            |
                            +-------------------------+
                            | + loadAsset()           |
                            |   1. Check RBAC role    |
                            |   2. Check Cache Hit    |
                            |   3. Call realLoader()  |
                            +-------------------------+
```

---

## 4. Practical Implementation (TypeScript)
```typescript
export interface AssetLoader {
  loadAsset(assetId: string, userRole: string): Promise<{ data: string; fromCache: boolean }>;
}

// 1. Real Subject: Heavy Remote Storage Loader
export class RemoteS3AssetLoader implements AssetLoader {
  async loadAsset(assetId: string, _userRole: string) {
    console.log(`[S3 Storage] Executing expensive network download for asset: "${assetId}"`);
    // Simulated remote network latency
    await new Promise((r) => setTimeout(r, 150));
    return { data: `RAW_BINARY_DATA_FOR_${assetId}`, fromCache: false };
  }
}

// 2. Proxy: Security Verification + In-Memory Caching + Telemetry
export class SecureCachedAssetProxy implements AssetLoader {
  private realSubject: RemoteS3AssetLoader;
  private cache = new Map<string, string>();
  private readonly RESTRICTED_ASSETS = new Set(["TOP_SECRET_FINANCIALS", "INTERNAL_AUDIT_DOC"]);

  constructor(realSubject?: RemoteS3AssetLoader) {
    this.realSubject = realSubject || new RemoteS3AssetLoader();
  }

  async loadAsset(assetId: string, userRole: string) {
    console.log(`[Proxy] Intercepted access request for "${assetId}" by user role [${userRole}]`);

    // A. Security Access Control (Protection Proxy)
    if (this.RESTRICTED_ASSETS.has(assetId) && userRole !== "ADMIN") {
      throw new Error(`403 Forbidden: Role [${userRole}] cannot access restricted asset ${assetId}`);
    }

    // B. Caching Layer (Caching Proxy)
    if (this.cache.has(assetId)) {
      console.log(`[Proxy] Cache HIT for "${assetId}". Returning cached copy without S3 download.`);
      return { data: this.cache.get(assetId)!, fromCache: true };
    }

    // C. Lazy Delegation to Real Subject
    const result = await this.realSubject.loadAsset(assetId, userRole);
    this.cache.set(assetId, result.data);

    return result;
  }

  clearCache(): void {
    this.cache.clear();
  }
}

// --- Usage ---
const assetService: AssetLoader = new SecureCachedAssetProxy();

async function run() {
  // First Call: Fetches from Remote S3
  const res1 = await assetService.loadAsset("USER_AVATAR_101", "GUEST");
  console.log("Result 1:", res1);

  // Second Call: Immediate Cache Hit (Zero S3 I/O)
  const res2 = await assetService.loadAsset("USER_AVATAR_101", "GUEST");
  console.log("Result 2:", res2);

  // Security Check: Unauthorized access blocked at Proxy boundary
  try {
    await assetService.loadAsset("TOP_SECRET_FINANCIALS", "GUEST");
  } catch (err: any) {
    console.error("Blocked:", err.message);
  }
}

run();
```

---

## 5. Edge Cases & Failure Handling
- **Cache Invalidation Staleness**: Cached proxies can return outdated data if the underlying remote asset changes. Implement TTLs or cache eviction hooks.\n- **Recursive Proxy Overheads**: Wrapping proxies inside proxies (e.g. LoggingProxy -> CachingProxy -> SecurityProxy) can introduce latency if call stacks become excessive.

---

## 6. Trade-offs & Production Considerations
### When to Use:
- Lazy initialization (Virtual Proxy) for high-overhead objects.\n- Access control and permission verification (Protection Proxy).\n- Caching query results and API responses (Caching Proxy).\n- Logging and instrumentation without modifying the original class.

### When NOT to Use / Anti-patterns:
- When the overhead of proxy indirection exceeds the cost of direct instantiation.
