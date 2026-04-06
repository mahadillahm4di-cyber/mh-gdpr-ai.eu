/**
 * Exception hierarchy for the AI Infrastructure SDK.
 *
 * Every error carries a `statusCode` and `requestId` for debugging
 * without ever leaking secrets or PII.
 */

/** Base error for all AI Infrastructure SDK errors. */
export class AIInfraError extends Error {
  readonly statusCode: number | null;
  readonly requestId: string | null;

  constructor(
    message: string,
    options?: { statusCode?: number; requestId?: string },
  ) {
    super(message);
    this.name = "AIInfraError";
    this.statusCode = options?.statusCode ?? null;
    this.requestId = options?.requestId ?? null;

    // Maintain proper prototype chain for instanceof checks
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

/** 401 — Invalid or missing API key. */
export class AuthenticationError extends AIInfraError {
  constructor(message: string, options?: { requestId?: string }) {
    super(message, { statusCode: 401, ...options });
    this.name = "AuthenticationError";
  }
}

/** 403 — Request blocked by security screening or insufficient permissions. */
export class SecurityBlockedError extends AIInfraError {
  constructor(message: string, options?: { requestId?: string }) {
    super(message, { statusCode: 403, ...options });
    this.name = "SecurityBlockedError";
  }
}

/** 403 — Tenant lacks required scope. */
export class PermissionError extends AIInfraError {
  constructor(message: string, options?: { requestId?: string }) {
    super(message, { statusCode: 403, ...options });
    this.name = "PermissionError";
  }
}

/** 429 — Too many requests. Includes retry-after hint. */
export class RateLimitError extends AIInfraError {
  readonly retryAfter: number;

  constructor(
    message: string,
    options?: { requestId?: string; retryAfter?: number },
  ) {
    super(message, { statusCode: 429, ...options });
    this.name = "RateLimitError";
    this.retryAfter = options?.retryAfter ?? 60;
  }
}

/** 402 — Monthly budget exhausted. */
export class BudgetExceededError extends AIInfraError {
  constructor(message: string, options?: { requestId?: string }) {
    super(message, { statusCode: 402, ...options });
    this.name = "BudgetExceededError";
  }
}

/** 400 — Client-side validation failed (bad messages, invalid params). */
export class ValidationError extends AIInfraError {
  constructor(message: string, options?: { requestId?: string }) {
    super(message, { statusCode: 400, ...options });
    this.name = "ValidationError";
  }
}

/** 502 — Upstream GPU provider returned an error. */
export class ProviderError extends AIInfraError {
  readonly provider: string;

  constructor(
    message: string,
    options?: { requestId?: string; provider?: string },
  ) {
    super(message, { statusCode: 502, ...options });
    this.name = "ProviderError";
    this.provider = options?.provider ?? "unknown";
  }
}

/** 503 — All providers are down. */
export class NoProviderAvailableError extends AIInfraError {
  constructor(message: string, options?: { requestId?: string }) {
    super(message, { statusCode: 503, ...options });
    this.name = "NoProviderAvailableError";
  }
}

/** Network-level failure (DNS, TCP, TLS). */
export class ConnectionError extends AIInfraError {
  constructor(message: string, options?: { requestId?: string }) {
    super(message, { requestId: options?.requestId });
    this.name = "ConnectionError";
  }
}

/** Request timeout exceeded. */
export class TimeoutError extends AIInfraError {
  readonly timeoutSeconds: number;

  constructor(
    message: string,
    options?: { requestId?: string; timeoutSeconds?: number },
  ) {
    super(message, { requestId: options?.requestId });
    this.name = "TimeoutError";
    this.timeoutSeconds = options?.timeoutSeconds ?? 60;
  }
}

/** Map HTTP status codes to error classes. */
const STATUS_MAP: Record<
  number,
  new (
    message: string,
    options?: { requestId?: string },
  ) => AIInfraError
> = {
  401: AuthenticationError,
  402: BudgetExceededError,
  403: SecurityBlockedError,
  429: RateLimitError,
  502: ProviderError,
  503: NoProviderAvailableError,
};

const MAX_ERROR_BODY_LENGTH = 500;

/** Generic messages for auth errors — never echo server body for 401/403. */
const SAFE_MESSAGES: Record<number, string> = {
  401: "Authentication failed — check your API key",
  403: "Request blocked — insufficient permissions",
};

/**
 * Create the correct error type from an HTTP status code and response body.
 * Auth error bodies are replaced with generic messages to prevent
 * accidental leakage of API keys through error logging.
 */
export function fromStatusCode(
  statusCode: number,
  body: string,
  requestId?: string,
): AIInfraError {
  const safeBody = SAFE_MESSAGES[statusCode] ?? body.slice(0, MAX_ERROR_BODY_LENGTH);
  const ErrorClass = STATUS_MAP[statusCode];
  if (ErrorClass) {
    return new ErrorClass(safeBody, { requestId });
  }
  return new AIInfraError(safeBody, { statusCode, requestId });
}

/** Check if an error is retryable (server errors and rate limits). */
export function isRetryable(error: AIInfraError): boolean {
  if (
    error instanceof AuthenticationError ||
    error instanceof BudgetExceededError ||
    error instanceof ValidationError ||
    error instanceof SecurityBlockedError ||
    error instanceof PermissionError
  ) {
    return false;
  }
  if (
    error instanceof RateLimitError ||
    error instanceof ConnectionError ||
    error instanceof TimeoutError ||
    error instanceof NoProviderAvailableError
  ) {
    return true;
  }
  const code = error.statusCode;
  return code !== null && (code === 429 || code >= 500);
}
