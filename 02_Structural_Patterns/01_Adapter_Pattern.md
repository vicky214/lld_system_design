# Adapter Pattern

## Category: Structural Pattern

---

## 1. Core Intent & Definition
Convert the interface of a class into another interface clients expect. Adapter lets classes work together that couldn't otherwise because of incompatible interfaces.

---

## 2. Real-Life Problem & Industry Scenario
### The Problem:
Modern cloud services consume RESTful JSON interfaces, but legacy banking partners and mainframe systems only expose XML/SOAP protocols with archaic parameter conventions. Rewriting core business logic to accommodate third-party quirks couples the domain model to external vendors.

### Real-World Industry Example:
Modern Fintech Payment Gateway integrating with a Legacy Core Banking Host. The internal checkout engine uses standardized PaymentProcessor interfaces ({ amountInCents, currency, token }), while the legacy host expects raw XML strings with merchant terminal IDs and date-formatted payloads.

---

## 3. Architecture & Visual Flow Diagram
```
+-------------------------------------------------------+
|                    PaymentProcessor                   | (Target Interface)
+-------------------------------------------------------+
| + charge(amount: number, token: string): Promise<res> |
+-------------------------------------------------------+
                           ▲
                           │
+-------------------------------------------------------+
|                LegacyBankSoapAdapter                  | (Adapter)
+-------------------------------------------------------+
| - legacySoapClient: LegacyBankSoapHost               |
+-------------------------------------------------------+
| + charge(amount, token): Promise<res>                 |
|   1. Transform JSON -> XML                            |
|   2. Call legacySoapClient.executeIsoWireTransfer()   |
|   3. Transform XML response -> Standardized JSON      |
+-------------------------------------------------------+
                           │
                           ▼
+-------------------------------------------------------+
|                 LegacyBankSoapHost                    | (Adaptee)
+-------------------------------------------------------+
| + executeIsoWireTransfer(xmlPayload: string): string  |
+-------------------------------------------------------+
```

---

## 4. Practical Implementation (TypeScript)
```typescript
export interface PaymentResult {
  transactionId: string;
  status: "SUCCESS" | "DECLINED" | "ERROR";
  amountProcessed: number;
}

// 1. Target Interface expected by modern microservices
export interface PaymentProcessor {
  charge(amountCents: number, currency: string, paymentToken: string): Promise<PaymentResult>;
}

// 2. Adaptee: Legacy Banking Host (Incompatible XML/SOAP Interface)
export class LegacyBankSoapHost {
  public executeIsoWireTransfer(xmlPayload: string): string {
    console.log("[Legacy SOAP Host] Received raw XML wire message:");
    console.log(xmlPayload);
    // Returns simulated XML response
    return `
      <TransferResponse>
        <Status>00_APPROVED</Status>
        <ReferenceNum>TXN-LEGACY-98214</ReferenceNum>
        <SettledMinorUnits>5000</SettledMinorUnits>
      </TransferResponse>
    `;
  }
}

// 3. Adapter: Bridges modern PaymentProcessor to LegacyBankSoapHost
export class LegacyBankSoapAdapter implements PaymentProcessor {
  private soapHost: LegacyBankSoapHost;

  constructor(soapHost: LegacyBankSoapHost) {
    this.soapHost = soapHost;
  }

  async charge(amountCents: number, currency: string, paymentToken: string): Promise<PaymentResult> {
    // A. Translate JSON domain parameters to SOAP XML payload
    const xmlPayload = `
      <PaymentRequest>
        <TerminalId>TERM_NY_01</TerminalId>
        <AccountToken>${paymentToken}</AccountToken>
        <Currency>${currency}</Currency>
        <AmountUnits>${amountCents}</AmountUnits>
        <Timestamp>${new Date().toISOString()}</Timestamp>
      </PaymentRequest>
    `.trim();

    // B. Invoke incompatible third-party system
    const rawXmlResponse = this.soapHost.executeIsoWireTransfer(xmlPayload);

    // C. Parse raw response back to standardized modern interface
    const isApproved = rawXmlResponse.includes("<Status>00_APPROVED</Status>");
    const refMatch = rawXmlResponse.match(/<ReferenceNum>(.*?)<\/ReferenceNum>/);
    const transactionId = refMatch ? refMatch[1] : `TXN-UNKNOWN-${Date.now()}`;

    return {
      transactionId,
      status: isApproved ? "SUCCESS" : "DECLINED",
      amountProcessed: amountCents / 100,
    };
  }
}

// --- Usage ---
const legacyHost = new LegacyBankSoapHost();
const paymentGateway: PaymentProcessor = new LegacyBankSoapAdapter(legacyHost);

// Domain layer calls standardized interface with zero knowledge of SOAP/XML
paymentGateway.charge(5000, "USD", "tok_visa_4242").then((result) => {
  console.log("[Checkout Service] Charge processed:", result);
});
```

---

## 5. Edge Cases & Failure Handling
- **Data Truncation & Type Incompatibilities**: The modern interface may support 64-bit precision numbers while the legacy host truncates to 32-bit floats. The adapter must validate numeric bounds before passing payloads.\n- **Error Code Misinterpretation**: Legacy hosts often return HTTP 200 OK containing an embedded `<ErrorCode>14_INSUFFICIENT_FUNDS</ErrorCode>`. The adapter must parse embedded error structures and throw domain exceptions.\n- **Two-Way Adapters**: When both systems need to invoke each other interchangeably, two-way adapter patterns must be implemented.

---

## 6. Trade-offs & Production Considerations
### When to Use:
- When integrating third-party libraries or legacy services whose interface does not match your internal standards.\n- When creating a reusable SDK that must support multiple vendor implementations without altering client code.

### When NOT to Use / Anti-patterns:
- When you have full control over both codebases (refactoring the target class directly is cleaner than introducing adapter layers).
