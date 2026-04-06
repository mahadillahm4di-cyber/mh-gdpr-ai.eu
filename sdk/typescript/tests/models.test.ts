import { describe, it, expect } from "vitest";
import {
  AVAILABLE_MODELS,
  listModels,
  getModel,
  parseChatCompletion,
  parseChatCompletionChunk,
} from "../src/models";

describe("AVAILABLE_MODELS", () => {
  it("contains 24 models", () => {
    expect(AVAILABLE_MODELS).toHaveLength(24);
  });

  it("all models have required fields", () => {
    for (const model of AVAILABLE_MODELS) {
      expect(model.id).toBeTruthy();
      expect(model.object).toBe("model");
      expect(model.owned_by).toBeTruthy();
      expect(Array.isArray(model.capabilities)).toBe(true);
      expect(model.capabilities.length).toBeGreaterThan(0);
      expect(typeof model.eu_safe).toBe("boolean");
    }
  });

  it("includes all Mistral models as EU-safe", () => {
    const mistral = AVAILABLE_MODELS.filter((m) => m.owned_by === "mistral");
    expect(mistral.length).toBeGreaterThanOrEqual(4);
    expect(mistral.every((m) => m.eu_safe)).toBe(true);
  });

  it("includes Llama models as EU-safe", () => {
    const llama = AVAILABLE_MODELS.filter((m) => m.owned_by === "meta");
    expect(llama.every((m) => m.eu_safe)).toBe(true);
  });

  it("marks OpenAI models as non-EU-safe", () => {
    const openai = AVAILABLE_MODELS.filter((m) => m.owned_by === "openai");
    expect(openai.every((m) => !m.eu_safe)).toBe(true);
  });

  it("has unique model IDs", () => {
    const ids = AVAILABLE_MODELS.map((m) => m.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
});

describe("listModels", () => {
  it("returns a ModelList with all models", () => {
    const list = listModels();
    expect(list.object).toBe("list");
    expect(list.data).toHaveLength(24);
  });
});

describe("getModel", () => {
  it("finds a model by ID", () => {
    const model = getModel("mistral-7b");
    expect(model).toBeDefined();
    expect(model!.id).toBe("mistral-7b");
    expect(model!.eu_safe).toBe(true);
  });

  it("returns undefined for unknown model", () => {
    expect(getModel("nonexistent-model")).toBeUndefined();
  });
});

describe("parseChatCompletion", () => {
  it("parses a full API response", () => {
    const raw = {
      id: "chatcmpl-abc123",
      object: "chat.completion",
      created: 1700000000,
      model: "mistral-7b",
      choices: [
        {
          index: 0,
          message: { role: "assistant", content: "Hello!" },
          finish_reason: "stop",
        },
      ],
      usage: { prompt_tokens: 10, completion_tokens: 5, total_tokens: 15 },
      savings: {
        cost_usd: 0.001,
        cost_saved_usd: 0.009,
        savings_percent: 90,
        model_used: "mistral-7b",
        provider_used: "scaleway",
        source: "inference",
        cache_hit: false,
        latency_ms: 150,
        rgpd_compliant: true,
        eu_routing: true,
        forced_eu_routing: false,
        pii_types_detected: [],
      },
      request_id: "req-456",
    };

    const completion = parseChatCompletion(raw);
    expect(completion.id).toBe("chatcmpl-abc123");
    expect(completion.model).toBe("mistral-7b");
    expect(completion.choices[0].message.content).toBe("Hello!");
    expect(completion.usage.total_tokens).toBe(15);
    expect(completion.savings.cost_usd).toBe(0.001);
    expect(completion.savings.savings_percent).toBe(90);
    expect(completion.savings.rgpd_compliant).toBe(true);
    expect(completion.request_id).toBe("req-456");
  });

  it("applies defaults for missing fields", () => {
    const completion = parseChatCompletion({});
    expect(completion.id).toBe("");
    expect(completion.object).toBe("chat.completion");
    expect(completion.choices).toHaveLength(0);
    expect(completion.usage.total_tokens).toBe(0);
    expect(completion.savings.cost_usd).toBe(0);
    expect(completion.savings.rgpd_compliant).toBe(true);
  });

  it("handles cache hit responses", () => {
    const raw = {
      id: "cache-hit-1",
      model: "mistral-7b",
      choices: [
        { message: { role: "assistant", content: "cached" } },
      ],
      savings: { source: "cache", cache_hit: true, cost_usd: 0 },
    };
    const completion = parseChatCompletion(raw);
    expect(completion.savings.cache_hit).toBe(true);
    expect(completion.savings.source).toBe("cache");
  });
});

describe("parseChatCompletionChunk", () => {
  it("parses a streaming chunk", () => {
    const raw = {
      id: "chatcmpl-abc",
      object: "chat.completion.chunk",
      created: 1700000000,
      model: "mistral-7b",
      choices: [
        {
          index: 0,
          delta: { content: "Hello" },
          finish_reason: null,
        },
      ],
    };

    const chunk = parseChatCompletionChunk(raw);
    expect(chunk.id).toBe("chatcmpl-abc");
    expect(chunk.model).toBe("mistral-7b");
    expect(chunk.choices[0].delta.content).toBe("Hello");
    expect(chunk.choices[0].finish_reason).toBeNull();
  });

  it("parses role-only delta (first chunk)", () => {
    const raw = {
      id: "chatcmpl-first",
      model: "mistral-7b",
      choices: [{ delta: { role: "assistant" }, finish_reason: null }],
    };
    const chunk = parseChatCompletionChunk(raw);
    expect(chunk.choices[0].delta.role).toBe("assistant");
    expect(chunk.choices[0].delta.content).toBeUndefined();
  });

  it("parses finish chunk", () => {
    const raw = {
      id: "chatcmpl-last",
      model: "mistral-7b",
      choices: [{ delta: {}, finish_reason: "stop" }],
    };
    const chunk = parseChatCompletionChunk(raw);
    expect(chunk.choices[0].finish_reason).toBe("stop");
  });
});
