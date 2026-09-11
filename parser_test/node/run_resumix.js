#!/usr/bin/env node
/**
 * Runner for the npm `resumix` package (github.com/ozmanghani/resumix).
 * Installs and runs cleanly out of the box, no workarounds needed.
 */
const fs = require("fs");
const { Resumix } = require("resumix");

const [, , inputPdf, outFile] = process.argv;
if (!inputPdf || !outFile) {
  console.error("usage: node run_resumix.js <input.pdf> <out.json>");
  process.exit(2);
}

Resumix.parse(inputPdf)
  .then((result) => {
    fs.writeFileSync(outFile, JSON.stringify(result, null, 2));
    console.log("SAVED:" + outFile);
    process.exit(0);
  })
  .catch((err) => {
    console.error("PARSE_ERROR:", err);
    process.exit(1);
  });
