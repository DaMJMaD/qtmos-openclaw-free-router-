"use strict";

let didFail = false;

function emit(payload) {
  console.log(JSON.stringify(payload));
}

function fail(error, extra = {}) {
  if (didFail) return;
  didFail = true;
  emit({ ok: false, error, ...extra });
}

function detail(err) {
  if (!err) return null;
  if (typeof err === "string") return err;
  if (typeof err.message === "string" && err.message) return err.message;
  try {
    return JSON.stringify(err);
  } catch (_err) {
    return String(err);
  }
}

function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === "--model" || a === "-m") {
      out.model = argv[i + 1];
      i += 1;
      continue;
    }
    if (a === "--prompt" || a === "-p") {
      out.prompt = argv[i + 1];
      i += 1;
      continue;
    }
    if (a === "--provider") {
      out.provider = argv[i + 1];
      i += 1;
      continue;
    }
  }
  return out;
}

function sanitizeToken(token) {
  return String(token || "").replace(/\s+/g, "");
}

function looksLikePlaceholder(token) {
  return /REAL_TOKEN|PASTE_TOKEN_ONE_LINE|YOUR_TOKEN|your_puter_auth_token_here/i.test(token);
}

function loadSdk() {
  const candidates = [
    "@heyputer/puter.js/src/init.cjs",
    process.env.PUTER_SDK_INIT_PATH || null,
    process.env.PUTER_SDK_PATH ? `${process.env.PUTER_SDK_PATH}/src/init.cjs` : null,
    "/mnt/c/Users/Dave/Desktop/QTMoSV1dev/systems modulation/node_modules/@heyputer/puter.js/src/init.cjs",
    "/home/dave/aa/Tenchin/systems modulation/node_modules/@heyputer/puter.js/src/init.cjs",
  ].filter(Boolean);

  for (const mod of candidates) {
    try {
      const loaded = require(mod);
      if (loaded && typeof loaded.init === "function") {
        return loaded;
      }
    } catch (_err) {}
  }
  return null;
}

function extractContent(resp) {
  if (!resp) return null;

  // plain string
  if (typeof resp === "string") {
    const s = resp.trim();
    if (!s) return null;
    try {
      const parsed = JSON.parse(s);
      const nested = extractContent(parsed);
      if (nested) return nested;
    } catch (_err) {}
    return s;
  }

  // common SDK helpers
  if (typeof resp.text === "string" && resp.text.trim()) return resp.text.trim();
  if (typeof resp.message === "string" && resp.message.trim()) return resp.message.trim();

  // object payloads
  if (typeof resp === "object") {
    if (resp.message && Array.isArray(resp.message.content)) {
      const text = resp.message.content
        .map((p) => (p && p.type === "text" ? String(p.text || "") : ""))
        .join("")
        .trim();
      if (text) return text;
    }

    if (typeof resp.content === "string" && resp.content.trim()) return resp.content.trim();

    if (Array.isArray(resp.content)) {
      const text = resp.content
        .map((x) => {
          if (typeof x === "string") return x;
          if (x && typeof x === "object") {
            if (typeof x.text === "string") return x.text;
            if (typeof x.content === "string") return x.content;
          }
          return "";
        })
        .join("")
        .trim();
      if (text) return text;
    }

    if (Array.isArray(resp.choices) && resp.choices.length) {
      const c0 = resp.choices[0] || {};
      if (typeof c0.text === "string" && c0.text.trim()) return c0.text.trim();
      const msg = c0.message || {};
      if (typeof msg.content === "string" && msg.content.trim()) return msg.content.trim();
      if (Array.isArray(msg.content)) {
        const text = msg.content
          .map((p) => (p && typeof p.text === "string" ? p.text : ""))
          .join("")
          .trim();
        if (text) return text;
      }
    }

    // last resort: stringify unknown response
    try {
      const s = JSON.stringify(resp);
      if (s && s !== "{}") return s;
    } catch {}
  }

  return null;
}

async function main() {
  const mode = process.argv[2];
  const args = parseArgs(process.argv.slice(3));
  const sdk = loadSdk();

  if (!mode) {
    fail("MISSING_MODE");
    return;
  }

  if (!sdk) {
    fail("MISSING_PUTER_SDK");
    return;
  }

  if (mode === "auth-token") {
    if (typeof sdk.getAuthToken !== "function") {
      fail("MISSING_GET_AUTH_TOKEN");
      return;
    }
    try {
      const token = sanitizeToken(await sdk.getAuthToken());
      if (!token) {
        fail("EMPTY_AUTH_TOKEN");
        return;
      }
      if (looksLikePlaceholder(token)) {
        fail("INVALID_TOKEN_PLACEHOLDER");
        return;
      }
      emit({ ok: true, token });
    } catch (err) {
      fail("AUTH_BOOTSTRAP_FAILED", { detail: detail(err) });
    }
    return;
  }

  const tokenRaw = process.env.puterAuthToken || process.env.PUTER_AUTH_TOKEN || "";
  const token = sanitizeToken(tokenRaw);
  if (!token) {
    fail("MISSING_AUTH_TOKEN");
    return;
  }
  if (looksLikePlaceholder(token)) {
    fail("INVALID_TOKEN_PLACEHOLDER");
    return;
  }

  let puter;
  try {
    puter = sdk.init(token);
  } catch (err) {
    fail("INIT_FAILED", { detail: detail(err) });
    return;
  }

  try {
    if (mode === "chat") {
      const model = args.model || "claude-opus-4-6";
      const prompt = args.prompt || "";
      if (!prompt) {
        fail("MISSING_PROMPT");
        return;
      }
      const resp = await puter.ai.chat(prompt, { model });
      const content = extractContent(resp);
      if (!content) {
        fail("EMPTY_CONTENT", { raw_type: typeof resp });
        return;
      }
      emit({ ok: true, content, model });
      return;
    }

    if (mode === "list-models") {
      const provider = args.provider || null;
      const models = await puter.ai.listModels(provider);
      emit({
        ok: Array.isArray(models),
        models: Array.isArray(models) ? models : [],
        provider,
      });
      return;
    }

    fail("UNKNOWN_MODE");
  } catch (err) {
    fail("RUNTIME_FAILED", { detail: detail(err) });
  }
}

process.on("unhandledRejection", (reason) => {
  fail("UNHANDLED_REJECTION", { detail: detail(reason) });
});

process.on("uncaughtException", (err) => {
  fail("UNCAUGHT_EXCEPTION", { detail: detail(err) });
});

main();
