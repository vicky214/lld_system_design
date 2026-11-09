# Decompose by Subdomain (Domain-Driven Design) Pattern

## 1. Classification & Intent
- **Pattern Category:** Microservices Architecture Patterns
- **Core Intent:** Decompose a monolithic system by analyzing Domain-Driven Design (DDD) subdomains: Core Domain (competitive advantage), Supporting Domain (enhances core), and Generic Domain (off-the-shelf/commodity capability).

---

## 2. Real-Life Industry Example
Uber Transportation Platform (Core: Dynamic Dispatch & Surge Pricing Algorithm; Supporting: Driver Onboarding; Generic: Invoicing, SMS OTP notification via Twilio).

---

## 3. Architecture & Flow Diagram
```
+------------------------------------------------------------------------+
|                              UBER DOMAIN                               |
+------------------------------------------------------------------------+
       |                                |                       |
       v                                v                       v
+--------------------+        +--------------------+  +--------------------+
|    CORE DOMAIN     |        | SUPPORTING DOMAIN  |  |   GENERIC DOMAIN   |
| (Proprietary IP)   |        | (Complementary)    |  | (Commodity Svc)    |
| - Surge Pricing    |        | - Driver KYC       |  | - Auth / IAM       |
| - Dispatch Match   |        | - Vehicle Audit    |  | - SMS Notification |
| - Realtime Routing |        | - Trip History     |  | - Payment Gateway  |
+--------------------+        +--------------------+  +--------------------+
```

---

## 4. Practical Production Implementation (TypeScript)
```typescript
/**
 * DDD Subdomain Decomposition Pattern
 * Clean separation between Core, Supporting, and Generic Subdomains
 */

// 1. GENERIC SUBDOMAIN (Generic capabilities, can even be SaaS integrations)
export interface NotificationService {
  sendSMS(phone: string, message: string): Promise<boolean>;
  sendEmail(to: string, subject: string, body: string): Promise<boolean>;
}

export class GenericNotificationService implements NotificationService {
  async sendSMS(phone: string, message: string): Promise<boolean> {
    console.log(`[GenericDomain:SMS] Sent to ${phone}: "${message}"`);
    return true;
  }
  async sendEmail(to: string, subject: string, body: string): Promise<boolean> {
    console.log(`[GenericDomain:Email] Sent to ${to}: ${subject}`);
    return true;
  }
}

// 2. SUPPORTING SUBDOMAIN (Business context specific, but not core competitive moat)
export interface DriverProfile {
  driverId: string;
  licenseNumber: string;
  isBackgroundChecked: boolean;
  vehicleStatus: 'INSPECTED' | 'PENDING' | 'REJECTED';
}

export class DriverOnboardingService {
  private drivers = new Map<string, DriverProfile>();

  async verifyAndApprove(driverId: string, license: string): Promise<DriverProfile> {
    const profile: DriverProfile = {
      driverId,
      licenseNumber: license,
      isBackgroundChecked: true,
      vehicleStatus: 'INSPECTED'
    };
    this.drivers.set(driverId, profile);
    console.log(`[SupportingDomain:DriverOnboarding] Approved driver ${driverId}`);
    return profile;
  }

  isDriverEligible(driverId: string): boolean {
    const d = this.drivers.get(driverId);
    return !!d && d.isBackgroundChecked && d.vehicleStatus === 'INSPECTED';
  }
}

// 3. CORE DOMAIN (Proprietary algorithms, competitive moat, custom engineered)
export interface GeoLocation {
  lat: number;
  lng: number;
}

export class CoreDispatchMatchingEngine {
  constructor(
    private driverService: DriverOnboardingService,
    private notifier: NotificationService
  ) {}

  calculateSurgeMultiplier(demandCount: number, supplyCount: number): number {
    if (supplyCount === 0) return 3.0; // Max surge cap
    const ratio = demandCount / supplyCount;
    if (ratio > 2.0) return 2.2;
    if (ratio > 1.2) return 1.5;
    return 1.0;
  }

  findOptimalDriver(
    riderLocation: GeoLocation,
    availableDrivers: Array<{ driverId: string; location: GeoLocation }>
  ): string | null {
    // Only dispatch to vetted drivers from the supporting domain
    const eligibleDrivers = availableDrivers.filter(d => 
      this.driverService.isDriverEligible(d.driverId)
    );

    if (eligibleDrivers.length === 0) return null;

    // Core proprietary geospatial nearest-neighbor algorithm
    let bestDriverId = eligibleDrivers[0].driverId;
    let minDistance = Infinity;

    for (const d of eligibleDrivers) {
      const dist = Math.hypot(d.location.lat - riderLocation.lat, d.location.lng - riderLocation.lng);
      if (dist < minDistance) {
        minDistance = dist;
        bestDriverId = d.driverId;
      }
    }

    this.notifier.sendSMS('+15550199', `Dispatch match confirmed with driver ${bestDriverId}`);
    return bestDriverId;
  }
}
```

---

## 5. Edge Cases & Failure Scenarios
1. **Domain Boundary Leakage**: When developers mix generic domain logic (e.g., raw SQL parsing or Stripe webhook handling) directly inside the Core algorithmic domain model. Mitigation: Enforce strict hexagonal/ports-and-adapters architecture.
2. **Context Mapping Conflicts**: The term 'Account' means completely different entities to Billing (ledger balance), Identity (credentials and scopes), and Risk (fraud score). Mitigation: Bounded contexts with explicit anti-corruption layers (ACLs).

---

## 6. Trade-offs: When to Use vs When NOT to Use
### When to Use:
- Complex business ecosystems where allocating engineering talent needs strategic focus (spend senior algorithm engineering on Core Domain; leverage off-the-shelf or junior teams for Generic/Supporting Domains).

### When NOT to Use:
- Simple CRUD apps or systems with no significant algorithmic or distinct domain boundaries.
