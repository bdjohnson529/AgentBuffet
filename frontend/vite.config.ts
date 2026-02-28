import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const _here = path.dirname(fileURLToPath(import.meta.url));
const _repoRoot = path.resolve(_here, "..");
const _stocksDir = path.join(_repoRoot, "stocks");
const _stocksTxt = path.join(_repoRoot, "stocks.txt");
const _thesisMd = path.join(_repoRoot, "thesis.md");

function loadRepoDotEnv() {
  // Minimal .env loader so `npm run dev` in frontend
  // can still pick up repo-root secrets (OPENAI_API_KEY, etc).
  const envPath = path.join(_repoRoot, ".env");
  try {
    if (!fs.existsSync(envPath)) return;
    const raw = fs.readFileSync(envPath, "utf-8");
    for (const lineRaw of raw.split(/\r?\n/)) {
      const line = lineRaw.trim();
      if (!line || line.startsWith("#")) continue;
      const eq = line.indexOf("=");
      if (eq === -1) continue;
      const key = line.slice(0, eq).trim();
      let val = line.slice(eq + 1).trim();
      if (!key) continue;
      if (
        (val.startsWith('"') && val.endsWith('"')) ||
        (val.startsWith("'") && val.endsWith("'"))
      ) {
        val = val.slice(1, -1);
      }
      if (process.env[key] === undefined) process.env[key] = val;
    }
  } catch {
    // ignore
  }
}

loadRepoDotEnv();

function contentTypeFor(filePath: string): string {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === ".json") return "application/json; charset=utf-8";
  if (ext === ".md") return "text/markdown; charset=utf-8";
  if (ext === ".txt") return "text/plain; charset=utf-8";
  return "application/octet-stream";
}

function sendFile(res: any, filePath: string) {
  res.statusCode = 200;
  res.setHeader("Content-Type", contentTypeFor(filePath));
  res.setHeader("Cache-Control", "no-store");
  fs.createReadStream(filePath).pipe(res);
}

function serveRepoStocks(): Plugin {
  const serveStocksMount = (req: any, res: any, next: any) => {
    const rawUrl = typeof req.url === "string" ? req.url : "/";
    const pathname = rawUrl.split("?")[0] ?? "/";
    let rel = "/";
    try {
      rel = decodeURIComponent(pathname);
    } catch {
      res.statusCode = 400;
      res.end("Bad Request");
      return;
    }

    const relPath = rel.replace(/^\/+/, "");
    const candidate = path.normalize(path.join(_stocksDir, relPath));
    const stocksRoot = path.normalize(_stocksDir + path.sep);
    if (!candidate.startsWith(stocksRoot)) {
      res.statusCode = 403;
      res.end("Forbidden");
      return;
    }

    fs.stat(candidate, (err, st) => {
      if (err || !st.isFile()) return next();
      sendFile(res, candidate);
    });
  };

  const serveStocksTxtMount = (_req: any, res: any, next: any) => {
    fs.stat(_stocksTxt, (err, st) => {
      if (err || !st.isFile()) return next();
      sendFile(res, _stocksTxt);
    });
  };

  const serveThesisMount = (_req: any, res: any, next: any) => {
    fs.stat(_thesisMd, (err, st) => {
      if (err || !st.isFile()) return next();
      sendFile(res, _thesisMd);
    });
  };

  return {
    name: "serve-repo-stocks",
    configureServer(server) {
      server.middlewares.use("/stocks.txt", serveStocksTxtMount);
      server.middlewares.use("/stocks", serveStocksMount);
      server.middlewares.use("/thesis.md", serveThesisMount);
    },
    configurePreviewServer(server) {
      server.middlewares.use("/stocks.txt", serveStocksTxtMount);
      server.middlewares.use("/stocks", serveStocksMount);
      server.middlewares.use("/thesis.md", serveThesisMount);
    },
  };
}

function intelligenceApi(): Plugin {
  function readJsonBody(req: any): Promise<any> {
    return new Promise((resolve, reject) => {
      let buf = "";
      req.on("data", (c: any) => (buf += c));
      req.on("end", () => {
        try {
          resolve(buf ? JSON.parse(buf) : {});
        } catch (e) {
          reject(e);
        }
      });
      req.on("error", reject);
    });
  }

  function sendJson(res: any, code: number, obj: any) {
    res.statusCode = code;
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.setHeader("Cache-Control", "no-store");
    res.end(JSON.stringify(obj));
  }

  function sendText(res: any, code: number, text: string) {
    res.statusCode = code;
    res.setHeader("Content-Type", "text/plain; charset=utf-8");
    res.setHeader("Cache-Control", "no-store");
    res.end(text);
  }

  type Provider = "openai" | "anthropic";

  function detectProvider(requested: string | undefined | null): Provider {
    const req = (requested || "either").trim().toLowerCase();
    if (req === "openai" || req === "anthropic") return req as Provider;
    if (req !== "either") throw new Error(`Unknown provider: ${requested}`);

    const hasOpenAI = Boolean(process.env.OPENAI_API_KEY);
    const hasAnthropic = Boolean(process.env.ANTHROPIC_API_KEY);
    if (hasOpenAI && !hasAnthropic) return "openai";
    if (hasAnthropic && !hasOpenAI) return "anthropic";
    if (hasOpenAI && hasAnthropic) return "openai";
    throw new Error("No API key found. Set OPENAI_API_KEY and/or ANTHROPIC_API_KEY in repo-root .env.");
  }

  function extractOutputTextOpenAI(resp: any): string {
    if (resp && typeof resp.output_text === "string" && resp.output_text.trim()) return resp.output_text.trim();
    const parts: string[] = [];
    for (const item of resp?.output || []) {
      if (item?.type !== "message") continue;
      for (const c of item?.content || []) {
        if (c?.type === "output_text" || c?.type === "text") {
          if (typeof c?.text === "string") parts.push(c.text);
        }
      }
    }
    return parts.join("\n").trim();
  }

  async function openaiResponsesCreate(opts: {
    model: string;
    input: any;
    temperature: number;
    max_output_tokens: number;
  }): Promise<string> {
    const key = process.env.OPENAI_API_KEY;
    if (!key) throw new Error("OPENAI_API_KEY not set.");
    const r = await fetch("https://api.openai.com/v1/responses", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${key}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(opts),
    });
    const json = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(`OpenAI error (HTTP ${r.status}): ${JSON.stringify(json).slice(0, 800)}`);
    const text = extractOutputTextOpenAI(json);
    if (!text) throw new Error("OpenAI returned empty text.");
    return text;
  }

  async function anthropicMessagesCreate(opts: {
    model: string;
    system?: string;
    messages: Array<{ role: "user" | "assistant"; content: string }>;
    temperature: number;
    max_tokens: number;
  }): Promise<string> {
    const key = process.env.ANTHROPIC_API_KEY;
    if (!key) throw new Error("ANTHROPIC_API_KEY not set.");
    const r = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(opts),
    });
    const json = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(`Anthropic error (HTTP ${r.status}): ${JSON.stringify(json).slice(0, 800)}`);
    const parts: string[] = [];
    for (const block of json?.content || []) {
      if (block?.type === "text" && typeof block?.text === "string") parts.push(block.text);
    }
    const text = parts.join("\n").trim();
    if (!text) throw new Error("Anthropic returned empty text.");
    return text;
  }

  function safeTicker(ticker: string): string {
    const t = (ticker || "").trim().toUpperCase();
    if (!/^[A-Z]+$/.test(t)) throw new Error("Invalid ticker.");
    return t;
  }

  function safeJoinStocks(ticker: string, filename: string): string {
    const tdir = path.join(_stocksDir, ticker);
    const candidate = path.normalize(path.join(tdir, filename));
    const root = path.normalize(tdir + path.sep);
    if (!candidate.startsWith(root)) throw new Error("Forbidden path.");
    return candidate;
  }

  const mount = (req: any, res: any, next: any) => {
    const rawUrl = typeof req.url === "string" ? req.url : "/";
    const pathname = rawUrl.split("?")[0] ?? "/";
    if (req.method !== "POST") return next();

    (async () => {
      try {
        if (pathname === "/api/intelligence/complete-report") {
          const body = await readJsonBody(req);
          const settings = body?.settings || {};
          const prompt = typeof body?.prompt === "string" ? body.prompt : "";
          if (!prompt.trim()) throw new Error("Missing prompt.");

          const providerUsed = detectProvider(settings?.provider);
          const temperature = typeof settings?.temperature === "number" ? settings.temperature : 0.2;
          const maxOut = typeof settings?.maxOutputTokens === "number" ? settings.maxOutputTokens : 900;

          if (providerUsed === "openai") {
            const model = (settings?.model || process.env.OPENAI_MODEL || "gpt-4.1-mini").toString();
            const text = await openaiResponsesCreate({
              model,
              input: prompt,
              temperature,
              max_output_tokens: maxOut,
            });
            return sendJson(res, 200, { text, providerUsed, modelUsed: model });
          } else {
            const model = (settings?.model || process.env.ANTHROPIC_MODEL || "claude-3-5-sonnet-latest").toString();
            const text = await anthropicMessagesCreate({
              model,
              messages: [{ role: "user", content: prompt }],
              temperature,
              max_tokens: maxOut,
            });
            return sendJson(res, 200, { text, providerUsed, modelUsed: model });
          }
        }

        if (pathname === "/api/intelligence/chat") {
          const body = await readJsonBody(req);
          const settings = body?.settings || {};
          const system = typeof body?.system === "string" ? body.system : "";
          const messagesIn = Array.isArray(body?.messages) ? body.messages : [];
          const messages = messagesIn
            .filter((m: any) => m && (m.role === "user" || m.role === "assistant") && typeof m.content === "string")
            .map((m: any) => ({ role: m.role, content: m.content })) as Array<{ role: "user" | "assistant"; content: string }>;

          if (!system.trim()) throw new Error("Missing system prompt.");
          if (!messages.length) throw new Error("Missing messages.");

          const providerUsed = detectProvider(settings?.provider);
          const temperature = typeof settings?.temperature === "number" ? settings.temperature : 0.2;
          const maxOut = typeof settings?.maxOutputTokens === "number" ? settings.maxOutputTokens : 700;

          if (providerUsed === "openai") {
            const model = (settings?.model || process.env.OPENAI_MODEL || "gpt-4.1-mini").toString();
            const input = [
              { role: "system", content: system },
              ...messages,
            ];
            const text = await openaiResponsesCreate({
              model,
              input,
              temperature,
              max_output_tokens: maxOut,
            });
            return sendJson(res, 200, { text, providerUsed, modelUsed: model });
          } else {
            const model = (settings?.model || process.env.ANTHROPIC_MODEL || "claude-3-5-sonnet-latest").toString();
            const text = await anthropicMessagesCreate({
              model,
              system,
              messages,
              temperature,
              max_tokens: maxOut,
            });
            return sendJson(res, 200, { text, providerUsed, modelUsed: model });
          }
        }

        if (pathname === "/api/intelligence/write-report") {
          const body = await readJsonBody(req);
          const ticker = safeTicker(body?.ticker);
          const reportMarkdown = typeof body?.reportMarkdown === "string" ? body.reportMarkdown : "";
          const reportJson = body?.reportJson;
          if (!reportMarkdown.trim()) throw new Error("Missing reportMarkdown.");
          if (!reportJson) throw new Error("Missing reportJson.");

          const dir = path.join(_stocksDir, ticker);
          fs.mkdirSync(dir, { recursive: true });
          const jsonPath = safeJoinStocks(ticker, "report.json");
          const mdPath = safeJoinStocks(ticker, "report.md");

          fs.writeFileSync(jsonPath, JSON.stringify(reportJson, null, 2) + "\n", "utf-8");
          fs.writeFileSync(mdPath, reportMarkdown, "utf-8");
          return sendJson(res, 200, { ok: true });
        }

        return next();
      } catch (e: any) {
        return sendText(res, 400, e?.message ? String(e.message) : String(e));
      }
    })();
  };

  return {
    name: "intelligence-api",
    configureServer(server) {
      server.middlewares.use(mount);
    },
    configurePreviewServer(server) {
      server.middlewares.use(mount);
    },
  };
}

export default defineConfig({
  plugins: [react(), serveRepoStocks(), intelligenceApi()],
  server: {
    fs: {
      allow: [_repoRoot],
    },
  },
});

