import {
  AutoPrError,
  SAKURA_AI_DEFAULT_ENDPOINT,
  SAKURA_AI_DEFAULT_MODEL,
} from "./auto-pr-common.mjs";

function getApiEndpoint() {
  const configuredEndpoint = process.env.SAKURA_AI_ENDPOINT || SAKURA_AI_DEFAULT_ENDPOINT;
  if (configuredEndpoint.replace(/\/+$/u, "") !== SAKURA_AI_DEFAULT_ENDPOINT) {
    throw new AutoPrError("invalid-sakura-endpoint");
  }
  return configuredEndpoint.replace(/\/+$/u, "");
}

function getApiModel() {
  const configuredModel = process.env.SAKURA_AI_MODEL || SAKURA_AI_DEFAULT_MODEL;
  if (configuredModel !== SAKURA_AI_DEFAULT_MODEL) {
    throw new AutoPrError("invalid-sakura-model");
  }
  return configuredModel;
}

function getApiKey() {
  const apiKey = process.env.SAKURA_AI_API_KEY;
  if (typeof apiKey !== "string" || apiKey.length === 0) {
    throw new AutoPrError("sakura-api-key-missing");
  }
  return apiKey;
}

export async function requestSakuraCompletion({ messages, maxTokens }) {
  if (!Array.isArray(messages) || !Number.isSafeInteger(maxTokens) || maxTokens <= 0) {
    throw new AutoPrError("sakura-request-invalid");
  }

  const response = await fetch(`${getApiEndpoint()}/chat/completions`, {
    method: "POST",
    headers: {
      accept: "application/json",
      authorization: `Bearer ${getApiKey()}`,
      "content-type": "application/json",
    },
    body: JSON.stringify({
      model: getApiModel(),
      messages,
      max_tokens: maxTokens,
      temperature: 0,
      stream: false,
    }),
    signal: AbortSignal.timeout(120000),
  });

  if (!response.ok) {
    throw new AutoPrError("sakura-request-failed");
  }

  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new AutoPrError("sakura-response-invalid");
  }

  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new AutoPrError("sakura-response-invalid");
  }
  if (!Array.isArray(payload.choices) || payload.choices.length === 0) {
    throw new AutoPrError("sakura-response-invalid");
  }

  const firstChoice = payload.choices[0];
  if (
    !firstChoice ||
    typeof firstChoice !== "object" ||
    Array.isArray(firstChoice) ||
    !firstChoice.message ||
    typeof firstChoice.message !== "object" ||
    Array.isArray(firstChoice.message) ||
    typeof firstChoice.message.content !== "string"
  ) {
    throw new AutoPrError("sakura-response-invalid");
  }

  return firstChoice.message.content;
}
