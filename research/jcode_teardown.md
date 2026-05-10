# jcode Teardown (Phase 1 — Discovery)

> Source: ChatGPT analysis of `github.com/1jehuang/jcode` (5.5k stars, Rust CLI agent harness).
> Generated via `chatgpt_send` (conversation `6a0090d0-5a0c-83ab-a29c-047385d69145`) on 2026-05-10.
> ChatGPT confidence: 0.87. Key caveat: GitHub UI shows 5.4k stars; we use 5.5k per pre-flight reading.

## 1. README structure

- `# jcode` — Establishes product name, badges, tagline, and navigation.
- `## Installation` — Gives the primary macOS/Linux install path.
- `## Performance & Resource Efficiency` — Frames speed/RAM as the core product wedge.
  - `### RAM comparison` — Benchmarks PSS across one and ten active sessions.
  - `### Time to first frame` — Measures launch-to-first-render latency.
  - `### Time to first input` — Measures launch-to-visible-typed-input latency.
  - `### Additional clients / memory scaling` — Shows marginal RAM cost per extra session.
- `## Memory (Agent memory)` — Explains semantic memory, graph retrieval, extraction, consolidation, and session search.
- `## UI: Side panels, Diagrams, Info Widgets, rendering, scrolling, alignment` — Sells TUI differentiation.
- `## Swarm` — Multi-agent repo coordination, conflict awareness, messaging, autonomous worker spawning.
- `## OAuth and Providers` — Subscription-backed OAuth plus direct/API-key provider fallback.
  - `### Supported built-in login flows`
  - `### Config-file setup for self-hosted endpoints and MCP`
  - `### Supported provider`
- `## Customizability / Self-Dev` — Positions self-modification as the deepest customization layer.
- `## Misc.` — Small differentiators: cache warnings, browser automation, agent grep, interleaved input, session resume, skills.
- `## iOS Application / Native OpenClaw` — Mobile/Tailscale teaser.
- `## Other planned features` — Roadmap thoughts.
- `## Quick Start` — Basic TUI, run, resume, serve/connect, dictate.
- `## Browser Automation` — Built-in `browser` tool, Firefox Agent Bridge.
- `## Further Reading` — Architecture/safety/platform docs.
- `## Detailed Installation` — Agent-assisted setup + platform-specific install paths.

## 2. Hero / visual elements

- **Hero**: animated `jcode_demo_jaguar.avif` is the primary visual at the top of the README.
- **Supplementary visuals**: `jcode_replay_jaguar_20260220_115340.mp4`, `screenshot.png`.
- **Embedded demos**: performance demo, memory demo, swarm demo, workflow demo, plus screenshots for provider login and `/Resume`.
- **Badges (just under H1)**: Latest Release, License, Platforms, Commit Activity, GitHub Stars.

## 3. Install one-liners

```bash
# macOS & Linux
curl -fsSL https://raw.githubusercontent.com/1jehuang/jcode/master/scripts/install.sh | bash
```

```powershell
# Windows PowerShell
irm https://raw.githubusercontent.com/1jehuang/jcode/master/scripts/install.ps1 | iex
```

```bash
# macOS via Homebrew
brew tap 1jehuang/jcode
brew install jcode
```

```bash
# From source
git clone https://github.com/1jehuang/jcode.git
cd jcode
cargo build --release
scripts/install_release.sh
```

## 4. Performance / benchmark patterns

They benchmark **harness UX, not model quality**:

- PSS memory across 1 active session and 10 active sessions.
- Launch latency (time to first frame, time to first input) over 10 interactive PTY launches.
- Marginal PSS per additional session.
- Versions tested are listed in a footer for reproducibility.

Tables always have columns `Tool / Metric / Range / Comparison` with multiplicative ratios (`6.0x more RAM`, `42.2x slower`).

## 5. Provider / auth model

- "Bring the provider you already pay for": built-in login for Claude, OpenAI/ChatGPT/Codex, Gemini, Copilot, Azure, Alibaba, Fireworks, MiniMax, LM Studio, Ollama, OpenAI-compatible.
- Headless / scriptable login: `--no-browser`, `--print-auth-url`, `--callback-url`, `--auth-code`.
- Pending state under `~/.jcode/pending-login/`.
- Config lives in `~/.jcode/config.toml` with `[provider]` and `[providers.<name>]`. Secrets in jcode's private app config dir.
- MCP config: `~/.jcode/mcp.json` (global), `.jcode/mcp.json` (project), `.claude/mcp.json` fallback.
- `OAUTH.md` adds a trust model: jcode asks before reading other CLIs' auth files, remembers approval, never mutates originals.

## 6. Repo conventions

| File | Purpose |
|---|---|
| `AGENTS.md` | Agent operating rules: commit small, push when done, fast iteration, rebuild on completion, stable/current build channels. |
| `CONTRIBUTING.md` | Issues preferred for reproducible bugs; PRs welcome but treated as proposals (LLM-generated code is risky). |
| `RELEASING.md` | Quick local hotfix releases, CI release flow, package-manager updates, cross-compilation. |
| `TELEMETRY.md` | Anonymous, minimal usage telemetry. Prompts/code never collected. |
| `OAUTH.md` | Deep auth spec: credential discovery, OAuth/API-key flows, provider quirks, troubleshooting. |
| `terminal-capabilities.md` | Terminal matrix and TUI rendering guidance: truecolor, Unicode, mouse, alt screen, tmux, resize, cleanup edge cases. |

## 7. Anti-patterns we should NOT copy for kairos

1. **Don't bury crisp product positioning under a sprawling README.** Split deep architecture into `docs/` earlier; keep README scannable in 30 seconds.
2. **Don't rely on benchmark claims without a reproducible benchmark harness.** If we publish numbers, ship the benchmark script.
3. **Don't ship typos in flagship copy.** Infrastructure-heavy tools lose trust fast on small polish failures.
4. **Don't make "self-dev" a headline feature unless rollback, review, and safety rails are solid.** kairos's lint/self-improvement loop must always require user review in v0.1.
5. **Don't over-expand provider/runner lists** before onboarding, defaults, and failure recovery are simple.

## What kairos imports from jcode

- jcode-style hero (animated, full-bleed, dark)
- Banner badges (release, license, platforms, commit activity, stars)
- Quick-Install code blocks for mac/linux + windows + from source
- "Further Reading" deep-link section to `docs/`
- `AGENTS.md` at repo root as the schema source of truth (Karpathy alignment)
- `CONTRIBUTING.md`, `RELEASING.md`, `TELEMETRY.md` as separate first-class files

## What kairos consciously does NOT import

- `.cargo` Rust toolchain, `crates/`, `Cargo.toml/lock` (kairos is Python)
- `ios/`, `mockups/jcode-mobile/`, `figma/`, `codemagic.yaml` (no mobile in v0.1)
- `telemetry-worker/` (no telemetry in v0.1; possibly v0.2 with explicit opt-in)
- `swarm` surface (out of scope for v0.1)
- Custom mermaid/terminal renderer (we lean on Markdown + Rich; renderers are a v0.3+ concern)
