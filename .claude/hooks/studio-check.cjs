#!/usr/bin/env node
// The Studio protocol check, run by Claude Code as a Stop hook.
// When the latest commit finishes a slice ("feat(S#): ..."), Claude can't end
// its turn until docs/progress.md has an entry for that slice, docs/stories.md
// no longer shows it as to do, and both files are committed.
// Plain Node, no packages. Works on Windows, macOS and Linux.
"use strict";
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

let input = {};
try { input = JSON.parse(fs.readFileSync(0, "utf8") || "{}"); } catch (e) {}
if (input.stop_hook_active) process.exit(0); // already blocked once this turn: let Claude stop

const root = process.env.CLAUDE_PROJECT_DIR || input.cwd || process.cwd();
const git = args => execFileSync("git", args, { cwd: root, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
const read = file => { try { return fs.readFileSync(path.join(root, file), "utf8"); } catch (e) { return null; } };

let subject = "";
try { subject = git(["log", "-1", "--format=%s"]); } catch (e) { process.exit(0); } // not a repo, or no commits yet
const m = /^feat\((S\d+)\)/.exec(subject);
if (!m) process.exit(0);
const id = m[1];
const idRe = new RegExp("\\b" + id + "\\b");

const problems = [];
const progress = read("docs/progress.md");
if (progress === null) problems.push("docs/progress.md doesn't exist");
else {
  const newest = progress.split(/\r?\n/).find(line => /^##\s/.test(line)) || "";
  if (!idRe.test(newest)) problems.push("the newest entry in docs/progress.md isn't for " + id);
}
const stories = read("docs/stories.md");
if (stories !== null) {
  const line = stories.split(/\r?\n/).find(l => /^\s*[-*+]\s+\[[ ~xX]\]\s+S\d+/.test(l) && idRe.test(l));
  if (line && /\[ \]/.test(line)) problems.push(id + " is still [ ] in docs/stories.md");
}
if (!problems.length) {
  let dirty = "";
  try { dirty = git(["status", "--porcelain", "--", "docs/progress.md", "docs/stories.md"]); } catch (e) {}
  if (dirty) problems.push("docs/progress.md or docs/stories.md has changes that aren't committed");
}
if (!problems.length) process.exit(0);

process.stdout.write(JSON.stringify({
  decision: "block",
  reason: "Studio protocol: the last commit is \"" + subject + "\", but " + problems.join("; ") + ". " +
    "Before you finish: mark " + id + " as [~] in docs/stories.md; add an entry at the top of docs/progress.md " +
    "(## YYYY-MM-DD · " + id + " · Title, then Built, Tests, Check on your phone and Next lines); " +
    "commit both as \"docs(" + id + "): progress log\"; then end with the Studio update block from CLAUDE.md."
}));
