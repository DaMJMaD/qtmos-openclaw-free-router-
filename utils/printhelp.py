def print_help():
    print("""
=== COMMAND REFERENCE ===
learn <text>                - Add new episodic memory
define <term>               - Search memories for related concepts
recall                      - View memories
state                       - Show system status
load-core <name>            - Load a core memory pack (identity)
load-pack <name>            - Switch episodic pack (e.g. 'quantum', 'base')
create-profile <name>       - Create matching core+episodic packs for a new profile
pack-list [epi|core|profiles] - List episodic/core/profile packs
core-list                   - Shortcut for `pack-list core`
live                        - Launch claw_live_bridge.py (live bridge TUI)
whoami                      - Show which core/episodic pack is active
duel <p1> <p2> <q>          - [disabled] compatibility shim (legacy behavior blocked)
ingest-url <url>            - [disabled] compatibility shim (legacy behavior blocked)
crawl                       - [disabled] compatibility shim (legacy behavior blocked)
ingest-api <term>           - [disabled] compatibility shim (legacy behavior blocked)
ingest-ollama <text>        - Summarize text via local LLM into episodic memory
chat <text>                 - Send a question or message to external ChatGPT 
ollama <text>               - same as chat
synthesize                  - Force immediate synthesis (also logs)
pulse-now                   - Trigger one autonomous pulse
health                      - Show system health / memory / tones
wander                      - Trigger safe curiosity / idle synthesis
pulse-stop / pulse-start    - Pause or resume pulse
promote <text>              - Promote episodic to core memory
run-script <file>           - Execute command script
scan                        - Run security scan
qtm / qtm-shell [cmd]       - Launch QTMoS (QTM OS); optional custom command override
qtm-status                  - Compatibility shim -> `claw status`
qtm-mode / rails / qhace    - [legacy-only] not migrated in modular core
forget                      - [legacy-only] not migrated in modular core
genesis-review              - [disabled] compatibility shim (legacy behavior blocked)
puter-chat <text> [--model <id>] - Puter chat (default claude-opus-4-6)
puter-models [provider]     - List available Puter models
puter-login [url|token]     - Reuse saved token/API key; --no-sdk to skip browser SDK auth
wslmenu                     - WSL GPU/env/dir/server quick menu
exit                        - Shutdown system
========================================
""")

def run_cli():
    system = CognitiveSystem()   # ✅ create instance
    print_help()
    while True:
        try:
            line = input("> ").strip()
            if not line:
                continue
            if line in ("exit", "quit"):
                break

            system.handle_command(line)  # ✅ use instance

        except KeyboardInterrupt:
            print("\n[EXIT]")
            break
