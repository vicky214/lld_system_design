# Fallback and Graceful Degradation Pattern

## 1. Classification & Intent
- **Pattern Category:** Resilience & Fault Tolerance Patterns
- **Core Intent:** Maintain core system availability during partial outages by switching to fallback strategies (stale caches, default static content, or disabled secondary features) instead of displaying an error page.

---

## 2. Real-Life Industry Example
Amazon Product Page & Netflix Home Screen (If the AI personalized recommendations engine is down, Amazon falls back to hardcoded Top 10 Best Sellers; if user bookmark sync fails, Netflix plays video without showing bookmarks).

---

## 3. Architecture & Flow Diagram
```
Client Requests Home Page
           |
           v
+------------------------------------+
| Personalization Service Available? |
+------------------------------------+
         /                  \
   (Yes)/                    \(No / Timeout 200ms)
       v                      v
[ Live AI Custom Rows ]  [ Fallback Static Top 10 Bestsellers ]
       \                      /
        v                    v
+------------------------------------+
| Client Receives Functional Webpage |
|      (No 500 Server Error)         |
+------------------------------------+
```

---

## 4. Practical Production Implementation (TypeScript)
```typescript
/**
 * Fallback & Graceful Degradation Pattern
 * Multi-tiered fallback hierarchy (Live -> Local Stale Cache -> Static Default)
 */

export interface ProductSummary {
  id: string;
  title: string;
  price: number;
  source: 'LIVE_SERVICE' | 'STALE_CACHE' | 'STATIC_FALLBACK';
}

export class GracefulRecommendationService {
  private staleCache = new Map<string, ProductSummary[]>();

  async getRecommendations(userId: string): Promise<ProductSummary[]> {
    try {
      // 1. Primary: Attempt live personalized microservice call with strict 300ms timeout
      const liveData = await this.fetchLiveWithTimeout(userId, 300);
      
      // Update stale cache for future resilience
      this.staleCache.set(userId, liveData);
      return liveData;
    } catch (err: any) {
      console.warn(`[FallbackService] Primary call failed (${err.message}). Degrading to Level 2: Stale Cache.`);

      // 2. Secondary Fallback: Serve stale personalized cache if available
      const cached = this.staleCache.get(userId);
      if (cached && cached.length > 0) {
        return cached.map(item => ({ ...item, source: 'STALE_CACHE' }));
      }

      // 3. Tertiary Fallback: Hardcoded static default catalog
      console.warn('[FallbackService] Stale cache missed. Degrading to Level 3: Static Default Catalog.');
      return this.getStaticFallbackCatalog();
    }
  }

  private async fetchLiveWithTimeout(userId: string, timeoutMs: number): Promise<ProductSummary[]> {
    // Simulating remote service timeout failure
    throw new Error('AI Personalization cluster timeout (> 300ms)');
  }

  private getStaticFallbackCatalog(): ProductSummary[] {
    return [
      { id: 'prod-01', title: 'Top Seller: Wireless Headphones', price: 99.99, source: 'STATIC_FALLBACK' },
      { id: 'prod-02', title: 'Top Seller: Ergonomic Keyboard', price: 129.99, source: 'STATIC_FALLBACK' }
    ];
  }
}
```

---

## 5. Edge Cases & Failure Scenarios
1. **Fallback Masquerading as Normal Operation**: If a fallback is too seamless, engineers might not notice the primary service has been offline for 3 days. Always emit telemetry metrics whenever a fallback path executes.
2. **Financial / Transactional Fallbacks**: NEVER provide optimistic fallbacks for payments or money transfers. If payment verification fails, fail explicitly rather than guessing approval.
3. **Stale Cache Expiry Threshold**: Serving cached data that is 10 minutes old is great; serving cached bank balances that are 3 days old is dangerous. Enforce maximum tolerable staleness.

---

## 6. Trade-offs: When to Use vs When NOT to Use
### When to Use:
- Customer-facing interfaces (browsing, search, recommendation, home feed) where showing slightly stale or generic data is vastly superior to displaying an error.

### When NOT to Use:
- Cryptographic verification, money disbursement, medical dosing, or operations where incorrect data causes severe harm.
