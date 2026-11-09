# Backend for Frontend (BFF) Pattern

## 1. Classification & Intent
- **Pattern Category:** Microservices Architecture Patterns
- **Core Intent:** Create separate specialized API gateways tailored specifically to the requirements of different client frontend interfaces (e.g., Mobile App vs Desktop Web vs Smart TV) rather than one generic catch-all gateway.

---

## 2. Real-Life Industry Example
SoundCloud & Netflix (Mobile BFF strips out heavy payload fields to conserve 4G data and battery; Desktop BFF aggregates rich metadata and analytics; TV BFF formats optimized grid views).

---

## 3. Architecture & Flow Diagram
```
Mobile App                  Web Desktop Browser
     |                              |
     v                              v
+---------------+             +---------------+
|   Mobile BFF  |             |    Web BFF    |
| (Lightweight, |             | (Rich payload,|
|  Aggregated)  |             |  High bandw.) |
+---------------+             +---------------+
        \                             /
         v                           v
  +-----------------------------------------+
  | Downstream Microservices                |
  | [User Svc] [Catalog Svc] [Playback Svc] |
  +-----------------------------------------+
```

---

## 4. Practical Production Implementation (TypeScript)
```typescript
/**
 * Backend For Frontend (BFF) Pattern
 * Tailored client payloads minimizing roundtrips and bandwidth
 */

export interface RawCatalogItem {
  id: string;
  title: string;
  hdPosterUrl: string;
  uhdPosterUrl: string;
  synopsis: string;
  cast: string[];
  producerNotes: string;
  analyticsTokens: string[];
}

export class DownstreamCatalogService {
  async fetchMedia(id: string): Promise<RawCatalogItem> {
    return {
      id,
      title: 'Interstellar Odyssey',
      hdPosterUrl: 'https://cdn.example.com/poster-hd.jpg',
      uhdPosterUrl: 'https://cdn.example.com/poster-4k.jpg',
      synopsis: 'A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival.',
      cast: ['Actor A', 'Actor B', 'Actor C'],
      producerNotes: 'Production budget $150M. Shot on IMAX 70mm.',
      analyticsTokens: ['trk_88291', 'trk_99120']
    };
  }
}

// 1. Mobile BFF: Optimized for low mobile bandwidth and small screen
export class MobileBff {
  constructor(private catalog: DownstreamCatalogService) {}

  async getMediaScreen(id: string) {
    const raw = await this.catalog.fetchMedia(id);
    return {
      id: raw.id,
      title: raw.title,
      // Provide compressed HD image only, omit 4k
      poster: raw.hdPosterUrl,
      shortSynopsis: raw.synopsis.slice(0, 60) + '...',
      castCount: raw.cast.length
      // internal producerNotes and analytics are stripped out!
    };
  }
}

// 2. Desktop Web BFF: High bandwidth, full cast details, 4K artwork
export class WebDesktopBff {
  constructor(private catalog: DownstreamCatalogService) {}

  async getMediaScreen(id: string) {
    const raw = await this.catalog.fetchMedia(id);
    return {
      id: raw.id,
      title: raw.title,
      backdrop: raw.uhdPosterUrl,
      fullSynopsis: raw.synopsis,
      topBilledCast: raw.cast,
      hasProductionNotes: !!raw.producerNotes
    };
  }
}
```

---

## 5. Edge Cases & Failure Scenarios
1. **Code Duplication Across BFFs**: Different BFFs often need identical authentication, logging, and error handling. Mitigation: Share core npm libraries/middlewares across BFF codebases while maintaining independent deployment pipelines.
2. **BFF Team Ownership Silos**: If frontend developers don't own the BFF and backend teams build them, communication bottlenecks remain. The BFF should ideally be owned and deployed by the respective frontend team.

---

## 6. Trade-offs: When to Use vs When NOT to Use
### When to Use:
- Multi-platform products with radically different user experiences, network constraints, or screen form factors.

### When NOT to Use:
- Single client applications (e.g. only a desktop web application exists). A standard API Gateway is sufficient.
