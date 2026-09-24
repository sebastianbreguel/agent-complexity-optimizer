#!/usr/bin/env node

/**
 * Fallback installer for agents that don't support `npx skills add`.
 *
 * For Claude Code, Codex, and Pi use `npx skills add` instead:
 *   npx skills add sebastianbreguel/agent-complexity-optimizer -a claude-code -g -y
 *   npx skills add sebastianbreguel/agent-complexity-optimizer -a codex -g -y
 *
 * This installer handles: Cursor, Windsurf, Copilot, Gemini CLI,
 * Cline/Roo, Aider, OpenCode, Continue.dev, Amazon Q, Zed AI.
 * It also installs to Codex/Claude as a fallback if detected.
 */

const fs = require("fs");
const os = require("os");
const path = require("path");

const SKILL_NAME = "complexity-optimizer";
const args = new Set(process.argv.slice(2));
const silent = args.has("--silent");
const dryRun = args.has("--dry-run");

function log(message) {
  if (!silent) console.log(message);
}

function warn(message) {
  if (!silent) console.warn(`  [skip] ${message}`);
}

function copyDir(src, dest) {
  if (dryRun) {
    log(`  [dry-run] would copy ${src} → ${dest}`);
    return;
  }
  fs.rmSync(dest, { recursive: true, force: true });
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.cpSync(src, dest, {
    recursive: true,
    filter: (source) => !source.includes(`${path.sep}.DS_Store`) && !source.includes(`${path.sep}__pycache__`),
  });
}

function copyFile(src, dest) {
  if (dryRun) {
    log(`  [dry-run] would copy ${src} → ${dest}`);
    return;
  }
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.cpSync(src, dest);
}

// Files earlier versions installed in places this version no longer uses.
function removeStale(paths) {
  for (const stale of paths) {
    if (!fs.existsSync(stale)) continue;
    if (dryRun) log(`  [dry-run] would remove ${stale}`);
    else fs.rmSync(stale, { recursive: true, force: true });
  }
}

// The scanner is a package (analyze_complexity.py + complexity_scanner/) plus helper scripts
// such as measure_growth.py, so every agent gets the whole scripts directory.
function copyScripts(dest) {
  for (const entry of fs.readdirSync(skillScripts)) {
    if (entry === "__pycache__" || entry === ".DS_Store") continue;
    const source = path.join(skillScripts, entry);
    const target = path.join(dest, entry);
    if (fs.statSync(source).isDirectory()) copyDir(source, target);
    else copyFile(source, target);
  }
}

const HOME = os.homedir();
const packageRoot = path.resolve(__dirname, "..");
const skillDir = path.join(packageRoot, "skills", SKILL_NAME);
const skillScripts = path.join(skillDir, "scripts");
const skillRefs = path.join(skillDir, "references");
const agentsDir = path.join(packageRoot, "agents");
const analyzerScript = path.join(skillScripts, "analyze_complexity.py");

const AGENTS = [
  {
    name: "Codex (OpenAI)",
    detect: () => fs.existsSync(path.join(HOME, ".codex")),
    install: () => {
      const dest = path.join(
        process.env.CODEX_HOME || path.join(HOME, ".codex"),
        "skills",
        SKILL_NAME
      );
      copyDir(skillDir, dest);
      copyFile(
        path.join(agentsDir, "codex", "agents", "openai.yaml"),
        path.join(dest, "agents", "openai.yaml")
      );
    },
  },
  {
    name: "Claude Code",
    detect: () => fs.existsSync(path.join(HOME, ".claude")),
    install: () => {
      const cmdDir = path.join(HOME, ".claude", "commands", SKILL_NAME);
      // Tools and references live outside commands/: Claude Code turns every .md there into a slash command.
      const toolsDir = path.join(HOME, ".claude", SKILL_NAME);
      copyFile(
        path.join(agentsDir, "claude", "complexity-optimizer.md"),
        path.join(cmdDir, "complexity-optimizer.md")
      );
      removeStale([path.join(cmdDir, "references"), path.join(cmdDir, "analyze_complexity.py")]);
      copyScripts(toolsDir);
      copyDir(skillRefs, path.join(toolsDir, "references"));
    },
  },
  {
    name: "Cursor",
    detect: () =>
      fs.existsSync(path.join(HOME, ".cursor")) ||
      fs.existsSync(path.join(HOME, "Library", "Application Support", "Cursor")),
    install: () => {
      const rulesDir = path.join(HOME, ".cursor", "rules");
      fs.mkdirSync(rulesDir, { recursive: true });
      copyFile(
        path.join(agentsDir, "cursor", "complexity-optimizer.mdc"),
        path.join(rulesDir, "complexity-optimizer.mdc")
      );
      copyScripts(path.join(rulesDir, SKILL_NAME));
    },
  },
  {
    name: "Windsurf (Codeium)",
    detect: () =>
      fs.existsSync(path.join(HOME, ".codeium")) ||
      fs.existsSync(path.join(HOME, ".windsurf")),
    install: () => {
      const dest = path.join(HOME, ".codeium", "windsurf", SKILL_NAME);
      copyFile(
        path.join(agentsDir, "windsurf", ".windsurfrules"),
        path.join(dest, ".windsurfrules")
      );
      copyScripts(dest);
    },
  },
  {
    name: "GitHub Copilot",
    detect: () =>
      fs.existsSync(path.join(HOME, ".config", "github-copilot")) ||
      process.env.GITHUB_COPILOT_TOKEN !== undefined,
    // Copilot reads .github/copilot-instructions.md from each repository,
    // not from the home directory — a global install cannot reach it.
    manual:
      "Copilot reads instructions per-repository. Copy agents/copilot/copilot-instructions.md " +
      "into your repo's .github/ directory, and the contents of skills/complexity-optimizer/scripts/ " +
      "(analyze_complexity.py, measure_growth.py, complexity_scanner/) into .github/complexity-optimizer/.",
  },
  {
    name: "Gemini CLI",
    detect: () => fs.existsSync(path.join(HOME, ".gemini")),
    install: () => {
      const dest = path.join(HOME, ".gemini", SKILL_NAME);
      copyFile(
        path.join(agentsDir, "gemini", "GEMINI.md"),
        path.join(dest, "GEMINI.md")
      );
      copyScripts(dest);
    },
  },
  {
    name: "Cline / Roo Code",
    detect: () =>
      fs.existsSync(path.join(HOME, ".cline")) ||
      fs.existsSync(path.join(HOME, ".roo")),
    install: () => {
      const dest = path.join(HOME, ".cline", SKILL_NAME);
      copyFile(
        path.join(agentsDir, "cline", ".clinerules"),
        path.join(dest, ".clinerules")
      );
      copyScripts(dest);
    },
  },
  {
    name: "Aider",
    detect: () =>
      fs.existsSync(path.join(HOME, ".aider.conf.yml")) ||
      fs.existsSync(path.join(HOME, ".aider")),
    install: () => {
      const dest = path.join(HOME, ".aider", SKILL_NAME);
      copyFile(
        path.join(agentsDir, "aider", "CONVENTIONS.md"),
        path.join(dest, "CONVENTIONS.md")
      );
      copyScripts(dest);
    },
  },
  {
    name: "OpenCode",
    detect: () =>
      fs.existsSync(path.join(HOME, ".opencode")) ||
      fs.existsSync(path.join(HOME, ".config", "opencode")),
    install: () => {
      const dest = path.join(HOME, ".opencode", SKILL_NAME);
      copyFile(
        path.join(agentsDir, "opencode", "AGENTS.md"),
        path.join(dest, "AGENTS.md")
      );
      copyScripts(dest);
    },
  },
  {
    name: "Continue.dev",
    detect: () => fs.existsSync(path.join(HOME, ".continue")),
    install: () => {
      const dest = path.join(HOME, ".continue", SKILL_NAME);
      copyFile(
        path.join(agentsDir, "continue-dev", "config.yaml"),
        path.join(dest, "config.yaml")
      );
      copyScripts(dest);
    },
  },
  {
    name: "Amazon Q Developer",
    detect: () => fs.existsSync(path.join(HOME, ".amazonq")),
    install: () => {
      const dest = path.join(HOME, ".amazonq", SKILL_NAME);
      copyFile(
        path.join(agentsDir, "amazon-q", ".amazonq", "rules", "complexity-optimizer.md"),
        path.join(dest, "complexity-optimizer.md")
      );
      copyScripts(dest);
    },
  },
  {
    name: "Zed AI",
    detect: () => fs.existsSync(path.join(HOME, ".config", "zed")),
    install: () => {
      const dest = path.join(HOME, ".config", "zed", SKILL_NAME);
      copyFile(
        path.join(agentsDir, "zed", "complexity-optimizer.md"),
        path.join(dest, "complexity-optimizer.md")
      );
      copyScripts(dest);
    },
  },
];

function main() {
  if (!fs.existsSync(analyzerScript)) {
    fail(`Cannot find bundled scanner at ${analyzerScript}`);
  }

  log("complexity-optimizer — universal AI agent installer");
  log("");
  log("Tip: For Claude Code/Codex/Pi, prefer `npx skills add` instead.");
  log("");

  let installed = 0;
  let skipped = 0;

  for (const agent of AGENTS) {
    if (!agent.detect()) {
      warn(`${agent.name} not detected`);
      skipped++;
      continue;
    }
    if (agent.manual) {
      log(`  [manual] ${agent.name}: ${agent.manual}`);
      skipped++;
      continue;
    }
    log(`  [+] ${agent.name}`);
    try {
      agent.install();
      installed++;
    } catch (err) {
      warn(`${agent.name}: ${err.message}`);
      skipped++;
    }
  }

  log("");
  log(`Installed for ${installed} agent(s), skipped ${skipped}.`);

  if (installed === 0) {
    log("");
    log("No agents detected. You can install manually:");
    log("  1. Copy the contents of skills/complexity-optimizer/scripts/ to your agent's config dir");
    log("  2. Copy the matching file from agents/<agent-name>/ alongside it");
  }

  if (installed > 0) {
    log("");
    log("Usage varies by agent. Examples:");
    log('  Codex:  "Use $complexity-optimizer to analyze this codebase"');
    log('  Claude: "Analyze this codebase for complexity hotspots"');
    log('  Others: "Scan this repo for performance hotspots and give me a report"');
  }
}

function fail(message) {
  console.error(message);
  process.exit(1);
}

main();
