# Feature Toggles and Canary Release Pattern

## 1. Classification & Intent
- **Pattern Category:** Deployment & Observability Patterns
- **Core Intent:** Decouple code deployment from feature release by wrapping new code paths behind dynamic runtime feature flags and routing a small percentage of real production traffic to canary versions to verify stability before full rollout.

---

## 2. Real-Life Industry Example
LaunchDarkly, Split.io, and Meta Gatekeeper (Facebook deploying code to production daily with features dark; enabling features dynamically for 1% of users, monitoring error rates, and expanding to 100%).

---

## 3. Architecture & Flow Diagram
```
Client Request (User ID: 'usr-9281')
                |
                v
  +-------------------------------+
  | Feature Flag Evaluator        |
  | Hash(userId + flag) % 100 < 5 |
  +-------------------------------+
         /                 \
   (In 5% Canary)       (In 95% Baseline)
        v                     v
[ New Checkout V2 ]   [ Stable Checkout V1 ]
        |                     |
        v                     v
   Log Error Rates       Log Error Rates
   (If Error Spike -> Kill switch drops Canary to 0% instantly!)
```

---

## 4. Practical Production Implementation (TypeScript)
```typescript
/**
 * Feature Toggles & Canary Release Pattern
 * Deterministic hash-based percentage rollout with targeted rule evaluation
 */

export interface ToggleUserContext {
  userId: string;
  email?: string;
  country?: string;
  isInternalEmployee?: boolean;
}

export interface FeatureFlagRule {
  key: string;
  enabled: boolean;
  canaryPercentage: number; // 0 to 100
  allowedUserIds?: string[];
  allowedCountries?: string[];
}

export class FeatureFlagEngine {
  private flags = new Map<string, FeatureFlagRule>();

  registerFlag(rule: FeatureFlagRule): void {
    this.flags.set(rule.key, rule);
  }

  // Instant emergency kill switch
  killSwitch(key: string): void {
    const flag = this.flags.get(key);
    if (flag) {
      flag.enabled = false;
      flag.canaryPercentage = 0;
      console.warn(`[FeatureFlag KILL SWITCH] Flag '${key}' has been forcibly DISABLED.`);
    }
  }

  isEnabled(key: string, user: ToggleUserContext): boolean {
    const flag = this.flags.get(key);
    if (!flag || !flag.enabled) return false;

    // 1. Rule: Explicit user ID whitelist
    if (flag.allowedUserIds && flag.allowedUserIds.includes(user.userId)) {
      return true;
    }

    // 2. Rule: Internal employees always get canary features
    if (user.isInternalEmployee) {
      return true;
    }

    // 3. Rule: Geographic targeting
    if (flag.allowedCountries && user.country && !flag.allowedCountries.includes(user.country)) {
      return false;
    }

    // 4. Deterministic Canary Rollout Percentage via hashing
    // Ensures the same user consistently sees the same feature version on page reloads!
    const userHashBucket = this.hashUserToPercent(user.userId, key);
    return userHashBucket < flag.canaryPercentage;
  }

  private hashUserToPercent(userId: string, flagKey: string): number {
    const str = `${userId}:${flagKey}`;
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      hash = (hash << 5) - hash + str.charCodeAt(i);
      hash |= 0; // Convert to 32bit integer
    }
    return Math.abs(hash) % 100;
  }
}
```

---

## 5. Edge Cases & Failure Scenarios
1. **Dead Feature Flag Debt**: Obsolete flags left in code for years create combinatorial test permutations and unreadable spaghetti code. Establish a policy to remove flag checks once a feature is at 100% for 30 days.
2. **Flag Evaluation Latency**: Fetching flags via remote HTTP on every user request adds 50ms latency. Always cache flags locally in memory and stream updates via WebSockets / Redis Pub/Sub.
3. **Database Schema Divergence**: If Canary V2 writes a new column that Baseline V1 cannot read, rolling back the canary corrupts baseline queries. Always make database changes backward-compatible before rolling out canaries.

---

## 6. Trade-offs: When to Use vs When NOT to Use
### When to Use:
- Continuous deployment workflows where teams release code multiple times daily and require zero-downtime progressive rollouts and instant rollback capabilities.

### When NOT to Use:
- Core low-level mathematical or cryptographic utility libraries where behavior must remain invariant across all invocations.
