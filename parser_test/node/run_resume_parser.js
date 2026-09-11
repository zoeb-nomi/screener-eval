#!/usr/bin/env node
/**
 * Runner for the npm `resume-parser` package (github.com/perminder-klair/resume-parser).
 *
 * WORKAROUND 1: the package's public API (index.js -> module.exports.parseResume)
 * calls `parseIt.parseResume(...)`, a function that does not exist in
 * src/utils/parseIt.js (it only exports `parseResumeFile` and `parseResumeUrl`).
 * Calling the public API throws "parseIt.parseResume is not a function" immediately.
 * We work around this by requiring the internal module directly and calling the
 * function that actually exists.
 *
 * WORKAROUND 2: a transitive dependency (`mime`, pulled in via `textract`) resolves
 * to a modern major version whose API dropped `.lookup()`, which this ~2016-era
 * codebase calls directly (`processing.js`: `this.mime = mime.lookup(file)`).
 * package.json pins mime@1.6.0 (last 1.x, has `.lookup()`) via a direct dependency
 * + npm "overrides" to force every transitive resolution to that version too.
 *
 * The library also attempts to scrape social-profile URLs found in the résumé
 * (LinkedIn/GitHub) over the network for enrichment; in a network-restricted
 * environment this throws an unhandled rejection AFTER the parse result is
 * already written to disk. We swallow that so the script still exits 0.
 */
process.on("unhandledRejection", () => {});
process.on("uncaughtException", (err) => {
  // only swallow the known post-parse network enrichment failure
  if (String(err).includes("ECONNRESET") || String(err).includes("tunneling socket")) return;
  console.error("FATAL:", err);
  process.exit(1);
});

const path = require("path");
const fs = require("fs");
const parseIt = require("resume-parser/src/utils/parseIt");

const [, , inputPdf, outDir] = process.argv;
if (!inputPdf || !outDir) {
  console.error("usage: node run_resume_parser.js <input.pdf> <out_dir>");
  process.exit(2);
}
fs.mkdirSync(outDir, { recursive: true });

parseIt.parseResumeFile(inputPdf, outDir, (savedFileName, error) => {
  if (error) {
    console.error("PARSE_ERROR:", error);
    process.exit(1);
  }
  const savedPath = path.join(outDir, savedFileName);
  console.log("SAVED:" + savedPath);
  // give the background network-enrichment attempt a moment to fail harmlessly,
  // then exit clean rather than hang on an open socket.
  setTimeout(() => process.exit(0), 1500);
});
