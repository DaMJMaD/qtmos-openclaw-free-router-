def print_help():
    print("""
=== COMMAND REFERENCE ===
learn <text>                - Add new episodic memory
define <term>               - Search memories for related concepts
recall                      - View memories
state                       - Show system status
load-core <name>            - Load a core memory pack (identity)
load-pack <name>            - Switch episodic pack (e.g. 'quantum', 'base')
pack-list [epi|profiles]    - List episodic packs or profile packs
live                        - (Alias: stay in this shell)
whoami                      - Show which core/episodic pack is active
duel <p1> <p2> <q>          - Let two persona packs alternate responses on a question
ingest-url <url>            - Ingest page text into memory
crawl                       - crawls webpage and store collected data as json
ingest-api <term>           - Ingest Wikipedia summary into memory
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
genesis-review              - Perform a self-reflection sequence
qtm / qtm-shell [cmd]       - Launch QTMoS (QTM OS); optional custom command override
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
