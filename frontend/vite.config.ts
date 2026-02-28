import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const _here = path.dirname(fileURLToPath(import.meta.url));
const _repoRoot = path.resolve(_here, "..");
const _stocksDir = path.join(_repoRoot, "stocks");
const _stocksTxt = path.join(_repoRoot, "stocks.txt");

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

  return {
    name: "serve-repo-stocks",
    configureServer(server) {
      server.middlewares.use("/stocks.txt", serveStocksTxtMount);
      server.middlewares.use("/stocks", serveStocksMount);
    },
    configurePreviewServer(server) {
      server.middlewares.use("/stocks.txt", serveStocksTxtMount);
      server.middlewares.use("/stocks", serveStocksMount);
    },
  };
}

export default defineConfig({
  plugins: [react(), serveRepoStocks()],
  server: {
    fs: {
      allow: [_repoRoot],
    },
  },
});

