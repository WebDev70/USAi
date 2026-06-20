#!/usr/bin/env node
// Coverage gate for the EXPORTED pure helpers in app.js (zero deps — uses Node's
// built-in coverage via a fresh `node --test --experimental-test-coverage` run).
//
// Why a custom gate: app.js is one big browser file; most of it is DOM/event
// wiring that is intentionally NOT unit-tested. A whole-file line-% therefore
// reads misleadingly low. The meaningful signal for TDD is: are the *pure,
// exported* helpers well covered? This script runs the JS tests with coverage,
// parses the per-file branch-% (the most robust signal the built-in reporter
// gives for the tested functions), and fails if it dips below the threshold.
//
// Usage:  node tests/js-coverage.mjs [minBranchPct]   (default 70)
// Requires Node >= 22 for --experimental-test-coverage.

import { execSync } from 'node:child_process';
import { readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const MIN = Number(process.argv[2] ?? 70);
const here = path.dirname(fileURLToPath(import.meta.url));
const jsDir = path.join(here, 'js');
const files = readdirSync(jsDir)
  .filter((f) => f.endsWith('.test.mjs'))
  .map((f) => path.join(jsDir, f));

let out;
try {
  out = execSync(
    `node --test --experimental-test-coverage ${files.map((f) => `'${f}'`).join(' ')}`,
    { encoding: 'utf-8', cwd: path.join(here, '..'), env: { ...process.env, NO_COLOR: '1', FORCE_COLOR: '0' } }
  );
} catch (err) {
  // node --test exits non-zero if any test fails; surface that first.
  out = (err.stdout || '') + (err.stderr || '');
  if (/fail (\d+)/.test(out) && Number(RegExp.$1) > 0) {
    console.error('JS tests failed — fix tests before checking coverage.\n');
    console.error(out);
    process.exit(1);
  }
}

// Find the app.js coverage row: "app.js | <line%> | <branch%> | <funcs%> | ..."
// Strip ANSI color codes first so parsing is robust regardless of TTY coloring.
const plain = out.replace(/\x1b\[[0-9;]*m/g, '').replace(/\\033\[[0-9;]*m/g, '');
const row = plain.split('\n').find((l) => /app\.js\s*\|/.test(l));
if (!row) {
  console.error('Could not find app.js coverage row. Is Node >= 22?');
  console.error('Node version:', process.version);
  process.exit(2);
}
// The row is: "<prefix> app.js | <line%> | <branch%> | <funcs%> | <uncovered...>"
// Take the three percentages that appear AFTER the "app.js |" cell, in order.
const afterName = row.slice(row.indexOf('app.js'));
const cells = afterName.split('|').map((c) => c.trim());
// cells[0] = "app.js", cells[1]=line%, cells[2]=branch%, cells[3]=funcs%
const linePct = parseFloat(cells[1]);
const branchPct = parseFloat(cells[2]);
const funcPct = parseFloat(cells[3]);

console.log(`app.js coverage — line ${linePct}%  branch ${branchPct}%  funcs ${funcPct}%`);
console.log(`Gate: branch coverage of tested code must be ≥ ${MIN}% (whole-file ` +
  `line-% is intentionally low because browser DOM wiring isn't unit-tested).`);

if (branchPct < MIN) {
  console.error(`\n✕ JS branch coverage ${branchPct}% is below the ${MIN}% threshold.`);
  console.error('  Add tests for the exported helpers in app.js (Red → Green → Refactor).');
  process.exit(1);
}
console.log(`\n✓ JS coverage gate passed (branch ${branchPct}% ≥ ${MIN}%).`);
