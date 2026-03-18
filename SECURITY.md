# Sovereign Workforce — Security Policy

## 1. Security Architecture Overview

The Sovereign Workforce operates on a **Zero-Trust, Layered Isolation** model.
No AI Specialist ever has direct access to credentials, file systems, or network endpoints.
All sensitive operations are mediated by the **IronClaw Enclave** (Rust on mobile, Python `core/security.py` on server).

```
┌─────────────────────────────────────────────────┐
│  LAYER 0: User Interface (React Native / Web)   │
│  ─ Untrusted. Display only. No credential state │
├─────────────────────────────────────────────────┤
│  LAYER 1: The HR Manager (Rust JSI / Python)    │
│  ─ Credential Vault (Fernet / Ed25519)          │
│  ─ Scope Guard (IP/Domain Whitelist)            │
│  ─ Signature Gate (User approval for actions)   │
├─────────────────────────────────────────────────┤
│  LAYER 2: Specialist Pool (LLM Inference)       │
│  ─ Sandboxed. Tool calls are REQUESTS, not      │
│    EXECUTIONS. All routed through Layer 1.      │
├─────────────────────────────────────────────────┤
│  LAYER 3: Knowledge Vault (SQLite/Supabase)     │
│  ─ RLS-enforced. Encrypted at rest.             │
│  ─ Forensic audit trail on all writes.          │
└─────────────────────────────────────────────────┘
```

---

## 2. Credential Management

### 2.1 Server-Side (Existing: `core/security.py`)
- **Encryption**: Fernet symmetric encryption via `ENCRYPTION_KEY` env var.
- **Key Rotation**: `core/key_manager.py` provides a singleton `KeyManager` with round-robin rotation across up to 20 Gemini API keys.
- **Trade Signing**: Double SHA-256 hash with `SOVEREIGN_ROOT_KEY` salt for financial operations.

### 2.2 Mobile-Side (Planned: Rust Enclave)
- **Boundary Injection**: API keys stored in Rust memory. Never cross the JSI bridge.
- **Ed25519 Sovereign Key**: Generated at "Incorporation" (onboarding). Stored in platform Keychain (iOS Keychain / Android Keystore).
- **Session Tokens**: Short-lived JWTs signed by the Sovereign Key, used to authenticate tool calls.

### 2.3 Credentials That NEVER Touch JavaScript
| Secret | Storage Layer | Access Method |
|:---|:---|:---|
| Gemini/Tavily API Keys | Rust `SecureVault` | Injected at HTTP request time |
| Bank SMS Tokens | Rust Notification Listener | Piped directly to Bookkeeper context |
| SSH Credentials (Pentest) | Rust `ScopeGuard` | Executed within whitelisted IP range |
| Sovereign Ed25519 Private Key | OS Keychain | Sign-only via `signAction()` |

---

## 3. Tool Execution Security

### 3.1 The Signature Gate
Every tool call classified as **Sensitive** requires explicit user authorization:

| Sensitivity | Tools | Approval |
|:---|:---|:---|
| **Low** | `search_tax_law`, `google_search`, `get_insider_trades_tool` | Auto-approved |
| **Medium** | `fetch_market_news_tool`, `prepare_trade_order_tool` | Notification + 5s delay |
| **High** | `send_email`, `write_file`, `exec_ssh`, `execute_trade` | Biometric/PIN required |

### 3.2 Scope Guard (Pentest Agent)
The Security Sentinel operates under a **deterministic whitelist**:
- Approved IP ranges and domains are configured at Rust level.
- Even if the LLM generates a command targeting `0.0.0.0/0`, Rust rejects it.
- Every rejected attempt is logged with full forensic trace.

---

## 4. Audit Trail

### 4.1 Forensic Trace Signing (Existing: `sign_forensic_trace()`)
Every AI reasoning chain is signed with SHA-256:
```
signature = SHA256({timestamp, user_input, reasoning_chain})
```
This creates a **tamper-proof audit log** for premium compliance verification.

### 4.2 Trade Execution Signing (Existing: `sign_trade_execution()`)
Financial operations use double-hashing with a root key:
```
primary = SHA256({ticket_id, asset, action, quantity, price, conviction})
final   = SHA256(primary + "SOVEREIGN_ROOT_KEY")
```

### 4.3 Mobile Audit (Planned)
On mobile, the Rust Enclave signs every action with the device's Ed25519 key before writing to the local SQLite audit table. This provides **non-repudiation**: the user provably authorized each action.

---

## 5. Data Classification

| Category | Examples | Encryption | TTL |
|:---|:---|:---|:---|
| **PII** | Names, emails, phone | Fernet (AES-128) | Until deletion |
| **Financial** | Trade orders, tax calcs | Double SHA-256 signed | 7 years |
| **Operational** | Chat logs, sandbox logs | At-rest (Supabase) | 90 days |
| **Volatile Intelligence** | Stock data, war updates | None (ephemeral) | 6 hours |
| **Knowledge** | Tax law, science | Vector embeddings | 3 months |

---

## 6. Supported Versions

| Version | Supported |
|:---|:---|
| 2.x (Sovereign Workforce) | ✅ Active |
| 1.x (Legacy Chat) | ⚠️ Security patches only |
| < 1.0 | ❌ Unsupported |

## 7. Reporting a Vulnerability

- **Email**: security@kusmus.org
- **Response SLA**: 48 hours for acknowledgment, 7 days for triage.
- **Scope**: All code in `core/`, `services/`, `database/`, and the mobile `rust-enclave/`.
- **Out of Scope**: Third-party dependencies (report upstream), demo/sandbox environments.
