# Factory Method Pattern

## Category: Creational Pattern

---

## 1. Core Intent & Definition
Define an interface for creating an object, but let subclasses or specialized creator classes decide which class to instantiate.

---

## 2. Real-Life Problem & Industry Scenario
### The Problem:
Hardcoding concrete class instantiations (`new TwilioSmsService()`, `new SendGridEmailService()`) directly inside business controllers tightly couples the core system to third-party vendor APIs, making vendor migration or dynamic multi-channel routing difficult and error-prone.

### Real-World Industry Example:
Omnichannel Notification Dispatcher. An enterprise platform sends transactional alerts via SMS, Email, Push Notification, or WhatsApp based on user preferences and regional regulatory compliance.

---

## 3. Architecture & Visual Flow Diagram
```
+-----------------------+
                    |      Notification     | <--- (Product Interface)
                    +-----------------------+
                    | + send(to, msg): void |
                    +-----------------------+
                               ▲
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
+---------------+      +----------------+     +----------------+
|  EmailChannel |      |   SmsChannel   |     | PushChannel    |
+---------------+      +----------------+     +----------------+
| + send()      |      | + send()       |     | + send()       |
+---------------+      +----------------+     +----------------+
        ▲                      ▲                      ▲
        │                      │                      │
+--------------------------------------------------------------+
|                    NotificationFactory                       |
+--------------------------------------------------------------+
| + createChannel(type: ChannelType): Notification             |
+--------------------------------------------------------------+
```

---

## 4. Practical Implementation (TypeScript)
```typescript
export type ChannelType = "EMAIL" | "SMS" | "PUSH" | "WHATSAPP";

export interface NotificationPayload {
  recipient: string;
  message: string;
  metadata?: Record<string, any>;
}

// 1. Product Interface
export interface NotificationChannel {
  send(payload: NotificationPayload): Promise<{ success: boolean; messageId: string }>;
}

// 2. Concrete Products
export class EmailNotificationChannel implements NotificationChannel {
  async send(payload: NotificationPayload) {
    console.log(`[Email Channel] Dispatching SMTP message to ${payload.recipient}: "${payload.message}"`);
    return { success: true, messageId: `email-${Date.now()}` };
  }
}

export class SmsNotificationChannel implements NotificationChannel {
  async send(payload: NotificationPayload) {
    console.log(`[SMS Channel] Transmitting carrier SMS to ${payload.recipient}: "${payload.message}"`);
    return { success: true, messageId: `sms-${Date.now()}` };
  }
}

export class PushNotificationChannel implements NotificationChannel {
  async send(payload: NotificationPayload) {
    console.log(`[Push Channel] Emitting APNS/FCM device token push to ${payload.recipient}`);
    return { success: true, messageId: `push-${Date.now()}` };
  }
}

// 3. Creator / Factory
export class NotificationFactory {
  private static registry = new Map<ChannelType, () => NotificationChannel>([
    ["EMAIL", () => new EmailNotificationChannel()],
    ["SMS", () => new SmsNotificationChannel()],
    ["PUSH", () => new PushNotificationChannel()],
  ]);

  /**
   * Open/Closed Principle: Dynamically register new channels without editing factory core
   */
  public static registerChannel(type: ChannelType, creator: () => NotificationChannel): void {
    NotificationFactory.registry.set(type, creator);
  }

  public static create(type: ChannelType): NotificationChannel {
    const creator = NotificationFactory.registry.get(type);
    if (!creator) {
      throw new Error(`Unsupported notification channel: ${type}. Register channel provider first.`);
    }
    return creator();
  }
}

// --- Usage ---
const channel = NotificationFactory.create("SMS");
channel.send({ recipient: "+15551234567", message: "Your OTP code is 482910" });
```

---

## 5. Edge Cases & Failure Handling
- **Unsupported Type Runtime Failure**: Passing an unrecognized enum string causes runtime exceptions. Always maintain a dynamic registry with fallback providers.\n- **Configuration Injection**: Concrete products often need distinct API keys (SendGrid key vs Twilio key). Use factory constructors or parameter factories to inject environment configs.\n- **Object Lifetime**: Determine if the factory should return fresh instances each time or cache reusable instances (Flyweight / Object Pool).

---

## 6. Trade-offs & Production Considerations
### When to Use:
- When the exact types and dependencies of objects cannot be known beforehand at compile time.\n- When you want to extend your library or framework by allowing users to plug in custom classes.\n- When consolidating scattered `new` operations into a centralized, auditable location.

### When NOT to Use / Anti-patterns:
- For simple, static class hierarchies where objects never vary at runtime (avoid unnecessary factory overhead).
