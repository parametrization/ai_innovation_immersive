#!/usr/bin/env bash
#
# sdlc-agent.sh - SDLC Agent Squad Runner
#
# Multi-agent system for automating Software Development Lifecycle workflows
#

set -euo pipefail

# Script metadata
readonly SCRIPT_NAME="sdlc-agent.sh"
readonly SCRIPT_VERSION="0.1.0"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PACKAGE_DIR="${SCRIPT_DIR}/agent_squad_sdlc"

# Default values
RUN_MODE=""
COMMAND="interactive"
DEBUG=false
PORT=8080
HOST="0.0.0.0"
VENV_DIR="${SCRIPT_DIR}/venv"

# Colors for output
if [[ -t 1 ]]; then
    readonly RED='\033[0;31m'
    readonly GREEN='\033[0;32m'
    readonly YELLOW='\033[0;33m'
    readonly BLUE='\033[0;34m'
    readonly BOLD='\033[1m'
    readonly NC='\033[0m' # No Color
else
    readonly RED=''
    readonly GREEN=''
    readonly YELLOW=''
    readonly BLUE=''
    readonly BOLD=''
    readonly NC=''
fi

#######################################
# Display manpage-style help
#######################################
show_help() {
    cat << 'EOF'
NAME
       sdlc-agent.sh - SDLC Agent Squad Runner

SYNOPSIS
       sdlc-agent.sh [OPTIONS] [COMMAND] [COMMAND_ARGS]

DESCRIPTION
       Run the SDLC Agent Squad multi-agent system for automating Software
       Development Lifecycle workflows. Supports multiple execution modes
       and commands for interacting with the agent squad.

OPTIONS
   Run Mode (required, choose one):
       -i, --installed
              Run using the installed package CLI (requires pip install -e .).
              This is the recommended mode for regular usage.

       -m, --module
              Run as a Python module without installation.
              Useful for development and testing.

       -M, --main
              Run the main.py entry point directly.
              Simple interactive mode without CLI features.

   General Options:
       -h, --help
              Display this help message and exit.

       -V, --version
              Display version information and exit.

       -d, --debug
              Enable debug mode with verbose logging.

       -s, --setup
              Set up the virtual environment and install dependencies.
              Run this before first use.

   Server Options (for 'serve' command):
       -p, --port PORT
              Server port (default: 8080).

       -H, --host HOST
              Server host (default: 0.0.0.0).

   Environment Options:
       -e, --env FILE
              Load environment variables from FILE (default: .env).

       -v, --venv DIR
              Path to virtual environment (default: ./venv).

COMMANDS
       interactive
              Start an interactive CLI session with the agent squad.
              This is the default command if none is specified.

       ask MESSAGE
              Send a single message to the agent squad and exit.

       analyze-issue NUMBER
              Analyze a specific GitHub issue by number.

       review-pr NUMBER
              Review a specific GitHub pull request by number.

       serve
              Start the webhook server for GitHub integration.

       verify
              Verify configuration and GitHub App setup.

ENVIRONMENT
       The following environment variables must be set (or provided via .env):

       ANTHROPIC_API_KEY
              Anthropic API key for Claude access.

       GITHUB_APP_ID
              GitHub App ID for authentication.

       GITHUB_APP_PRIVATE_KEY
              GitHub App private key (PEM format).

       GITHUB_WEBHOOK_SECRET
              Secret for verifying GitHub webhooks.

       GITHUB_OWNER
              GitHub repository owner/organization.

       GITHUB_REPO
              GitHub repository name.

       Optional variables:

       CLAUDE_MODEL_ID
              Claude model to use (default: claude-sonnet-4-20250514).

       ENVIRONMENT
              Deployment environment: local, development, staging, production.

       STORAGE_TYPE
              Storage backend: memory or dynamodb (default: memory).

       DEBUG
              Enable debug logging (true/false).

EXAMPLES
       Set up the environment (first time):
              ./sdlc-agent.sh --setup

       Start interactive session (installed mode):
              ./sdlc-agent.sh -i interactive

       Start interactive session (module mode):
              ./sdlc-agent.sh -m interactive

       Run with debug logging:
              ./sdlc-agent.sh -i -d interactive

       Analyze a GitHub issue:
              ./sdlc-agent.sh -i analyze-issue 42

       Review a pull request:
              ./sdlc-agent.sh -i review-pr 10

       Start webhook server on custom port:
              ./sdlc-agent.sh -i -p 9000 serve

       Send a single message:
              ./sdlc-agent.sh -m ask "What issues need attention?"

       Verify configuration:
              ./sdlc-agent.sh -i verify

       Use custom .env file:
              ./sdlc-agent.sh -i -e production.env interactive

FILES
       .env
              Default environment configuration file.

       venv/
              Python virtual environment directory.

       agent_squad_sdlc/
              Main application package directory.

EXIT STATUS
       0      Success
       1      General error
       2      Invalid arguments
       3      Missing dependencies
       4      Configuration error

SEE ALSO
       Full documentation: https://github.com/parametrization/ai_innovation_immersive

VERSION
       sdlc-agent.sh version 0.1.0

AUTHORS
       Generated with Claude Code (https://claude.com/claude-code)
EOF
}

#######################################
# Display version information
#######################################
show_version() {
    echo "${SCRIPT_NAME} version ${SCRIPT_VERSION}"
}

#######################################
# Print colored message
#######################################
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

#######################################
# Check if command exists
#######################################
command_exists() {
    command -v "$1" &> /dev/null
}

#######################################
# Set up virtual environment
#######################################
setup_environment() {
    log_info "Setting up SDLC Agent Squad environment..."

    # Check Python version
    if ! command_exists python3; then
        log_error "Python 3 is required but not installed."
        exit 3
    fi

    local python_version
    python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    log_info "Python version: ${python_version}"

    # Create virtual environment
    if [[ ! -d "${VENV_DIR}" ]]; then
        log_info "Creating virtual environment at ${VENV_DIR}..."
        python3 -m venv "${VENV_DIR}"
    else
        log_info "Virtual environment already exists at ${VENV_DIR}"
    fi

    # Activate and install
    log_info "Installing dependencies..."
    # shellcheck source=/dev/null
    source "${VENV_DIR}/bin/activate"

    pip install --upgrade pip --quiet
    pip install -e "${PACKAGE_DIR}[dev]" --quiet

    log_success "Setup complete!"
    log_info "To activate manually: source ${VENV_DIR}/bin/activate"
    log_info "Run with: ./sdlc-agent.sh -i interactive"
}

#######################################
# Activate virtual environment
#######################################
activate_venv() {
    if [[ -d "${VENV_DIR}" ]]; then
        # shellcheck source=/dev/null
        source "${VENV_DIR}/bin/activate"
    else
        log_warn "Virtual environment not found. Run with --setup first."
        log_warn "Attempting to run with system Python..."
    fi
}

#######################################
# Load environment file
#######################################
load_env_file() {
    local env_file="$1"

    if [[ -f "${env_file}" ]]; then
        log_info "Loading environment from ${env_file}"
        set -a
        # shellcheck source=/dev/null
        source "${env_file}"
        set +a
    elif [[ "${env_file}" != ".env" ]]; then
        log_error "Environment file not found: ${env_file}"
        exit 4
    fi
}

#######################################
# Validate required environment
#######################################
validate_environment() {
    local missing=()

    [[ -z "${ANTHROPIC_API_KEY:-}" ]] && missing+=("ANTHROPIC_API_KEY")
    [[ -z "${GITHUB_APP_ID:-}" ]] && missing+=("GITHUB_APP_ID")
    [[ -z "${GITHUB_APP_PRIVATE_KEY:-}" ]] && missing+=("GITHUB_APP_PRIVATE_KEY")
    [[ -z "${GITHUB_WEBHOOK_SECRET:-}" ]] && missing+=("GITHUB_WEBHOOK_SECRET")
    [[ -z "${GITHUB_OWNER:-}" ]] && missing+=("GITHUB_OWNER")
    [[ -z "${GITHUB_REPO:-}" ]] && missing+=("GITHUB_REPO")

    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Missing required environment variables:"
        for var in "${missing[@]}"; do
            echo "  - ${var}"
        done
        echo ""
        log_info "Set these in a .env file or export them."
        exit 4
    fi
}

#######################################
# Run with installed CLI
#######################################
run_installed() {
    local cmd="$1"
    shift
    local args=("$@")

    activate_venv

    if ! command_exists sdlc-agent; then
        log_error "sdlc-agent command not found. Run with --setup first."
        exit 3
    fi

    local cli_args=()
    ${DEBUG} && cli_args+=("--debug")

    case "${cmd}" in
        interactive|ask|analyze-issue|review-pr|verify)
            sdlc-agent "${cli_args[@]}" "${cmd}" "${args[@]}"
            ;;
        serve)
            sdlc-agent "${cli_args[@]}" serve --host "${HOST}" --port "${PORT}"
            ;;
        *)
            log_error "Unknown command: ${cmd}"
            exit 2
            ;;
    esac
}

#######################################
# Run as Python module
#######################################
run_module() {
    local cmd="$1"
    shift
    local args=("$@")

    activate_venv

    export PYTHONPATH="${PACKAGE_DIR}:${PYTHONPATH:-}"

    local cli_args=()
    ${DEBUG} && cli_args+=("--debug")

    case "${cmd}" in
        interactive|ask|analyze-issue|review-pr|verify)
            python -m agent_squad_sdlc.handlers.cli_handler "${cli_args[@]}" "${cmd}" "${args[@]}"
            ;;
        serve)
            python -m agent_squad_sdlc.handlers.cli_handler "${cli_args[@]}" serve --host "${HOST}" --port "${PORT}"
            ;;
        *)
            log_error "Unknown command: ${cmd}"
            exit 2
            ;;
    esac
}

#######################################
# Run main.py directly
#######################################
run_main() {
    activate_venv

    export PYTHONPATH="${PACKAGE_DIR}:${PYTHONPATH:-}"
    ${DEBUG} && export DEBUG=true

    python -m agent_squad_sdlc.main
}

#######################################
# Main entry point
#######################################
main() {
    local env_file=".env"
    local do_setup=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                show_help
                exit 0
                ;;
            -V|--version)
                show_version
                exit 0
                ;;
            -i|--installed)
                RUN_MODE="installed"
                shift
                ;;
            -m|--module)
                RUN_MODE="module"
                shift
                ;;
            -M|--main)
                RUN_MODE="main"
                shift
                ;;
            -d|--debug)
                DEBUG=true
                shift
                ;;
            -s|--setup)
                do_setup=true
                shift
                ;;
            -p|--port)
                PORT="$2"
                shift 2
                ;;
            -H|--host)
                HOST="$2"
                shift 2
                ;;
            -e|--env)
                env_file="$2"
                shift 2
                ;;
            -v|--venv)
                VENV_DIR="$2"
                shift 2
                ;;
            -*)
                log_error "Unknown option: $1"
                echo "Use --help for usage information."
                exit 2
                ;;
            *)
                # First non-option argument is the command
                COMMAND="$1"
                shift
                break
                ;;
        esac
    done

    # Remaining arguments are command arguments
    local cmd_args=("$@")

    # Handle setup
    if ${do_setup}; then
        setup_environment
        exit 0
    fi

    # Check if run mode was specified
    if [[ -z "${RUN_MODE}" ]]; then
        echo -e "${BOLD}SDLC Agent Squad${NC} - No run mode specified\n"
        echo "Usage: ${SCRIPT_NAME} <-i|-m|-M> [OPTIONS] [COMMAND]"
        echo ""
        echo "Run Modes (required):"
        echo "  -i, --installed    Run using installed CLI (recommended)"
        echo "  -m, --module       Run as Python module"
        echo "  -M, --main         Run main.py directly"
        echo ""
        echo "Quick Start:"
        echo "  ${SCRIPT_NAME} --setup           # First time setup"
        echo "  ${SCRIPT_NAME} -i interactive    # Start interactive session"
        echo ""
        echo "Use --help for full documentation."
        exit 2
    fi

    # Change to script directory
    cd "${SCRIPT_DIR}"

    # Load environment
    load_env_file "${env_file}"

    # Validate environment (skip for verify command)
    if [[ "${COMMAND}" != "verify" ]]; then
        validate_environment
    fi

    # Execute based on run mode
    case "${RUN_MODE}" in
        installed)
            run_installed "${COMMAND}" "${cmd_args[@]}"
            ;;
        module)
            run_module "${COMMAND}" "${cmd_args[@]}"
            ;;
        main)
            run_main
            ;;
    esac
}

# Run main function
main "$@"
