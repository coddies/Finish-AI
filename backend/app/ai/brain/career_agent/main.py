"""
main.py — Entry Point CLI for BURHAN_ADVISOR Career Agent.

Usage:
    python main.py
    python main.py pdf path/to/resume.pdf   (one-shot PDF analysis)

Commands inside the interactive loop:
    pdf <path>  — Parse and analyze a CV/PDF file
    clear       — Clear conversation history and start fresh
    quit/exit   — Exit the agent
    <text>      — Chat with BURHAN_ADVISOR
"""
from __future__ import annotations

import logging
import sys
import pathlib

from dotenv import load_dotenv

# Load .env before any other imports that touch API keys
load_dotenv(dotenv_path=pathlib.Path(__file__).parent / ".env")

# ---------------------------------------------------------------------------
# LOGGING CONFIGURATION
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stderr),   # Logs go to stderr
    ],
)
# Silence overly verbose third-party loggers
for _noisy in ("httpx", "httpcore", "groq", "openai", "google"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PROJECT IMPORTS (after dotenv)
# ---------------------------------------------------------------------------
from career_agent.state_adapter import NeutralHistory, append_user
from career_agent.agent import run_react_loop
from career_agent.pdf_parser import extract_pdf_text, SCANNED_PDF_MSG


# ---------------------------------------------------------------------------
# BANNER
# ---------------------------------------------------------------------------
BANNER = """
╔══════════════════════════════════════════════════════════════════╗
║       BURHAN_ADVISOR — AI Career & Skills Strategist             ║
║       Multi-Model ReAct Agent  |  4-Tier Failover Engine         ║
╠══════════════════════════════════════════════════════════════════╣
║  TIERS: Gemini 2.5 Flash → Groq 70B → Groq 8B → NVIDIA → Ollama ║
╠══════════════════════════════════════════════════════════════════╣
║  Commands:                                                       ║
║    pdf <path>   Upload & analyze a CV/PDF file                   ║
║    clear        Clear conversation history                       ║
║    quit / exit  Exit the agent                                   ║
╚══════════════════════════════════════════════════════════════════╝
"""

WELCOME = (
    "BURHAN_ADVISOR: Hello! I am your AI Career Strategist. "
    "Tell me your skills, paste your CV text, or type `pdf <path>` to upload your resume.\n"
)


# ---------------------------------------------------------------------------
# PDF HANDLER
# ---------------------------------------------------------------------------

def handle_pdf_command(pdf_path_str: str) -> str | None:
    """
    Parse a PDF and return its text content as a user message string.
    Prints error/warning messages directly and returns None on failure.

    Args:
        pdf_path_str: Raw path string from user input.

    Returns:
        Formatted user message string, or None if parsing failed.
    """
    clean_path = pdf_path_str.strip().strip('"').strip("'")
    print(f"  [Parsing PDF: {clean_path}]")

    try:
        pdf_text = extract_pdf_text(clean_path)
    except FileNotFoundError as exc:
        print(f"\nBURHAN_ADVISOR: {exc}\n")
        return None
    except ValueError as exc:
        print(f"\nBURHAN_ADVISOR: {exc}\n")
        return None

    if pdf_text == SCANNED_PDF_MSG:
        print(f"\nBURHAN_ADVISOR: {SCANNED_PDF_MSG}\n")
        return None

    print(f"  [PDF parsed successfully — {len(pdf_text):,} characters]\n")
    return f"Here is my CV/Resume text:\n\n{pdf_text}"


# ---------------------------------------------------------------------------
# ONE-SHOT PDF MODE
# ---------------------------------------------------------------------------

def run_oneshot_pdf(pdf_path: str) -> None:
    """
    Non-interactive mode: analyze a single PDF file and print the result.

    Args:
        pdf_path: Path to the PDF file to analyze.
    """
    print(BANNER)
    history: NeutralHistory = []

    user_msg = handle_pdf_command(pdf_path)
    if user_msg is None:
        sys.exit(1)

    append_user(history, user_msg)
    print("BURHAN_ADVISOR: Analyzing your CV...\n")

    try:
        response = run_react_loop(history)
        print(f"BURHAN_ADVISOR:\n{response}\n")
    except Exception as exc:
        logger.exception(f"Unexpected error during one-shot analysis: {exc}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# INTERACTIVE LOOP
# ---------------------------------------------------------------------------

def run_interactive() -> None:
    """Run the main interactive CLI loop."""
    print(BANNER)
    print(WELCOME)

    history: NeutralHistory = []

    while True:
        # ── PROMPT ────────────────────────────────────────────────────────
        try:
            raw = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nBURHAN_ADVISOR: Goodbye! Best of luck on your career journey. 🚀\n")
            sys.exit(0)

        if not raw:
            continue

        user_lower = raw.lower()

        # ── BUILT-IN COMMANDS ─────────────────────────────────────────────
        if user_lower in ("quit", "exit"):
            print("BURHAN_ADVISOR: Goodbye! Best of luck on your career journey. 🚀\n")
            sys.exit(0)

        if user_lower == "clear":
            history.clear()
            print("BURHAN_ADVISOR: Conversation cleared. Fresh start!\n")
            continue

        if user_lower.startswith("pdf "):
            pdf_arg = raw[4:]
            user_msg = handle_pdf_command(pdf_arg)
            if user_msg is None:
                continue
            raw = user_msg   # Replace raw with enriched PDF content

        # ── SEND TO AGENT ─────────────────────────────────────────────────
        append_user(history, raw)

        print("BURHAN_ADVISOR: ", end="", flush=True)
        try:
            response = run_react_loop(history)
            print(response)
        except Exception as exc:
            logger.exception(f"Unexpected agent error: {exc}")
            print(
                f"\n[Error] An unexpected error occurred: {exc}\n"
                "Please try again or check the logs for details."
            )

        print()   # Blank line between turns


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI entry point. Supports both interactive and one-shot PDF modes."""
    args = sys.argv[1:]

    if len(args) >= 2 and args[0].lower() == "pdf":
        # One-shot mode: python main.py pdf path/to/resume.pdf
        run_oneshot_pdf(args[1])
    else:
        # Default: interactive loop
        run_interactive()


if __name__ == "__main__":
    main()
