/**
 * Security utilities — API key validation, content sanitization, PII detection.
 *
 * Mirrors the Python SDK security module exactly.
 * PII detection is client-side only (warnings, not blocking).
 */

import { AuthenticationError, ValidationError } from "./errors";

const API_KEY_PATTERN = /^sk-[a-zA-Z0-9-]{32,128}$/;

const VALID_ROLES = new Set(["system", "user", "assistant"]);

const MAX_CONTENT_LENGTH = 1_000_000;

/** Regex patterns for client-side PII detection. */
const PII_PATTERNS: Record<string, RegExp> = {
  email: /[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}/,
  phone: /(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{1,4}\)?[\s.-]?){2,5}\d{2,4}/,
  iban: /\b[A-Z]{2}\d{2}\s?[\dA-Z]{4}\s?[\dA-Z]{4}\s?[\dA-Z]{4}\s?[\dA-Z]{0,4}\b/,
  credit_card: /\b(?:\d[ -]*?){13,19}\b/,
  ssn: /\b\d{3}-\d{2}-\d{4}\b/,
};

/**
 * Validate an API key format.
 *
 * @throws AuthenticationError if the key is missing or malformed.
 */
export function validateApiKey(apiKey: string | undefined): string {
  if (!apiKey || apiKey.trim() === "") {
    throw new AuthenticationError(
      "API key is required. Set AI_INFRA_API_KEY environment variable or pass apiKey to Client.",
    );
  }
  const trimmed = apiKey.trim();
  if (!API_KEY_PATTERN.test(trimmed)) {
    throw new AuthenticationError(
      "Invalid API key format. Expected: sk-<32-128 alphanumeric characters>.",
    );
  }
  return trimmed;
}

/**
 * Resolve an API key from explicit param or environment variable.
 *
 * Priority: explicit param > AI_INFRA_API_KEY env var.
 * @throws AuthenticationError if no key is found.
 */
export function resolveApiKey(
  explicit?: string,
  envVar: string = "AI_INFRA_API_KEY",
): string {
  const key = explicit ?? process.env[envVar];
  return validateApiKey(key);
}

/**
 * Mask an API key for safe logging.
 *
 * @returns "sk-abc...xyz" showing first 6 and last 3 characters.
 */
export function maskApiKey(apiKey: string): string {
  if (apiKey.length <= 9) {
    return "sk-***";
  }
  return `${apiKey.slice(0, 6)}...${apiKey.slice(-3)}`;
}

// Control characters to strip (preserve \n and \t)
const CONTROL_CHARS = /[\x00-\x08\x0b\x0c\x0e-\x1f]/g;

/**
 * Sanitize message content — strip control characters, enforce length limit.
 *
 * @throws ValidationError if content exceeds max length.
 */
export function sanitizeContent(
  text: string,
  maxLength: number = MAX_CONTENT_LENGTH,
): string {
  const cleaned = text.replace(CONTROL_CHARS, "");
  if (cleaned.length > maxLength) {
    throw new ValidationError(
      `Content too long: ${cleaned.length} chars (max: ${maxLength}).`,
    );
  }
  return cleaned;
}

/**
 * Detect potential PII in text (client-side, for warnings only).
 *
 * @returns Array of detected PII type names (e.g., ["email", "phone"]).
 */
export function detectPii(text: string): string[] {
  const detected: string[] = [];
  for (const [piiType, pattern] of Object.entries(PII_PATTERNS)) {
    if (pattern.test(text)) {
      detected.push(piiType);
    }
  }
  return detected;
}

/**
 * Validate and sanitize a message array.
 *
 * @throws ValidationError if messages are empty or contain invalid roles/content.
 */
export function validateMessages(
  messages: Array<{ role: string; content: string }>,
  maxContentLength: number = MAX_CONTENT_LENGTH,
): Array<{ role: string; content: string }> {
  if (!messages || messages.length === 0) {
    throw new ValidationError("Messages array must not be empty.");
  }

  return messages.map((msg, index) => {
    if (!VALID_ROLES.has(msg.role)) {
      throw new ValidationError(
        `Invalid role "${msg.role}" at message[${index}]. Must be: system, user, or assistant.`,
      );
    }
    if (!msg.content || msg.content.trim() === "") {
      throw new ValidationError(
        `Empty content at message[${index}]. Content must not be blank.`,
      );
    }
    return {
      role: msg.role,
      content: sanitizeContent(msg.content, maxContentLength),
    };
  });
}
