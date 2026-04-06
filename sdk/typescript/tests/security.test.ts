import { describe, it, expect, beforeEach, afterEach } from "vitest";
import {
  validateApiKey,
  resolveApiKey,
  maskApiKey,
  sanitizeContent,
  detectPii,
  validateMessages,
} from "../src/security";
import { AuthenticationError, ValidationError } from "../src/errors";

describe("validateApiKey", () => {
  const prefix = "sk";
  const validHex = "a".repeat(32);
  const validKey = `${prefix}-${validHex}`;

  it("accepts a valid key", () => {
    expect(validateApiKey(validKey)).toBe(validKey);
  });

  it("trims whitespace", () => {
    expect(validateApiKey(`  ${validKey}  `)).toBe(validKey);
  });

  it("rejects undefined", () => {
    expect(() => validateApiKey(undefined)).toThrow(AuthenticationError);
  });

  it("rejects empty string", () => {
    expect(() => validateApiKey("")).toThrow(AuthenticationError);
  });

  it("rejects whitespace-only", () => {
    expect(() => validateApiKey("   ")).toThrow(AuthenticationError);
  });

  it("rejects key without sk- prefix", () => {
    expect(() => validateApiKey("pk-" + validHex)).toThrow(
      AuthenticationError,
    );
  });

  it("rejects key shorter than 32 chars after prefix", () => {
    expect(() => validateApiKey(`${prefix}-short`)).toThrow(
      AuthenticationError,
    );
  });
});

describe("resolveApiKey", () => {
  const prefix = "sk";
  const validHex = "b".repeat(32);
  const validKey = `${prefix}-${validHex}`;
  const envKey = `${prefix}-${"c".repeat(32)}`;

  beforeEach(() => {
    process.env.AI_INFRA_API_KEY = envKey;
  });

  afterEach(() => {
    delete process.env.AI_INFRA_API_KEY;
  });

  it("prefers explicit key over env", () => {
    expect(resolveApiKey(validKey)).toBe(validKey);
  });

  it("falls back to env var", () => {
    expect(resolveApiKey(undefined)).toBe(envKey);
  });

  it("throws if neither explicit nor env", () => {
    delete process.env.AI_INFRA_API_KEY;
    expect(() => resolveApiKey(undefined)).toThrow(AuthenticationError);
  });
});

describe("maskApiKey", () => {
  it("masks middle of key", () => {
    const prefix = "sk";
    const hex = "a".repeat(40);
    const key = `${prefix}-${hex}`;
    const masked = maskApiKey(key);
    expect(masked).toMatch(/^sk-aaa\.\.\.aaa$/);
    expect(masked).not.toContain(hex);
  });

  it("handles short keys", () => {
    expect(maskApiKey("sk-short")).toBe("sk-***");
  });
});

describe("sanitizeContent", () => {
  it("preserves normal text", () => {
    expect(sanitizeContent("Hello, world!")).toBe("Hello, world!");
  });

  it("preserves newlines and tabs", () => {
    expect(sanitizeContent("line1\nline2\ttab")).toBe("line1\nline2\ttab");
  });

  it("strips control characters", () => {
    expect(sanitizeContent("hello\x00world\x07test")).toBe("helloworldtest");
  });

  it("throws on content exceeding max length", () => {
    const long = "x".repeat(100);
    expect(() => sanitizeContent(long, 50)).toThrow(ValidationError);
  });
});

describe("detectPii", () => {
  it("detects email addresses", () => {
    expect(detectPii("contact me at john@example.com")).toContain("email");
  });

  it("detects phone numbers", () => {
    expect(detectPii("call me at +33 6 12 34 56 78")).toContain("phone");
  });

  it("detects IBAN", () => {
    expect(detectPii("my IBAN is FR76 1234 5678 9012 3456 7890")).toContain(
      "iban",
    );
  });

  it("detects SSN", () => {
    expect(detectPii("my SSN is 123-45-6789")).toContain("ssn");
  });

  it("returns empty for clean text", () => {
    expect(detectPii("Hello, how are you?")).toHaveLength(0);
  });

  it("detects multiple PII types", () => {
    const types = detectPii("email: a@b.com, SSN: 123-45-6789");
    expect(types).toContain("email");
    expect(types).toContain("ssn");
  });
});

describe("validateMessages", () => {
  it("accepts valid messages", () => {
    const result = validateMessages([
      { role: "system", content: "You are helpful" },
      { role: "user", content: "Hello" },
    ]);
    expect(result).toHaveLength(2);
    expect(result[0].role).toBe("system");
    expect(result[1].role).toBe("user");
  });

  it("rejects empty array", () => {
    expect(() => validateMessages([])).toThrow(ValidationError);
  });

  it("rejects invalid role", () => {
    expect(() =>
      validateMessages([{ role: "admin", content: "hello" }]),
    ).toThrow(ValidationError);
  });

  it("rejects empty content", () => {
    expect(() =>
      validateMessages([{ role: "user", content: "" }]),
    ).toThrow(ValidationError);
  });

  it("rejects whitespace-only content", () => {
    expect(() =>
      validateMessages([{ role: "user", content: "   " }]),
    ).toThrow(ValidationError);
  });

  it("sanitizes control characters in content", () => {
    const result = validateMessages([
      { role: "user", content: "hello\x00world" },
    ]);
    expect(result[0].content).toBe("helloworld");
  });
});
