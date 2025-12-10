# SDLC Agent Squad

A multi-agent system for automating Software Development Lifecycle (SDLC) workflows using [AWS Agent Squad](https://awslabs.github.io/agent-squad) framework with Claude.

## Overview

This project implements a team of specialized AI agents that work together to automate common SDLC tasks:

```
                    ┌─────────────────────┐
                    │   SDLC Supervisor   │
                    │  (AnthropicAgent)   │
                    └──────────┬──────────┘
                               │
        ┌──────────┬───────────┼───────────┬──────────┐
        ▼          ▼           ▼           ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ Require- │ │  Story   │ │Implement-│ │    QA    │ │  Issue   │
│  ments   │ │  Writer  │ │   ation  │ │  Tester  │ │ Resolver │
│  Agent   │ │  Agent   │ │  Agent   │ │  Agent   │ │  Agent   │
└──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

### Agents

| Agent | Role | Responsibilities |
|-------|------|-----------------|
| **Requirements Agent** | Requirements Intake | Parse issues, ask clarifying questions, extract acceptance criteria |
| **Story Writer Agent** | User Story Creation | Create structured user stories, define acceptance criteria, break down epics |
| **Implementation Agent** | Code Suggestions | Analyze codebase, suggest implementations via PR comments |
| **QA Agent** | Testing & Validation | Create test checklists, review PRs, validate acceptance criteria |
| **Issue Resolver Agent** | Bug Triage | Analyze bugs, identify root causes, propose fixes |

## Features

- **Supervisor Pattern**: Hierarchical coordination with a lead agent managing workflow
- **GitHub App Integration**: Secure authentication with fine-grained permissions
- **Webhook-Driven**: Responds to GitHub events (issues, PRs, comments)
- **In-Memory or DynamoDB Storage**: Flexible conversation persistence
- **Local Development**: Docker + LocalStack for AWS emulation
- **AWS Deployment**: SAM templates for Lambda deployment

## Quick Start

### Prerequisites

- Python 3.10+
- Docker (for local development)
- Anthropic API key
- GitHub App (see [Setup](#github-app-setup))

### Installation

```bash
cd experiment/agent_squad_sdlc

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

### Configuration

Create a `.env` file:

```env
# Anthropic
ANTHROPIC_API_KEY=your-api-key
CLAUDE_MODEL_ID=claude-sonnet-4-20250514

# GitHub App
GITHUB_APP_ID=123456
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n..."
GITHUB_WEBHOOK_SECRET=your-webhook-secret
GITHUB_OWNER=your-org
GITHUB_REPO=your-repo

# Optional
ENVIRONMENT=local
STORAGE_TYPE=memory
DEBUG=true
```

### Running Locally

#### CLI Mode

```bash
# Interactive session
sdlc-agent interactive

# Single command
sdlc-agent ask "Analyze issue #42"

# Analyze specific issue
sdlc-agent analyze-issue 42

# Review a PR
sdlc-agent review-pr 10
```

#### Webhook Server

```bash
# Start webhook server
sdlc-agent serve --port 8080
```

#### Docker Compose (with LocalStack)

```bash
cd infrastructure/docker

# Start services
docker-compose up -d

# View logs
docker-compose logs -f agent-squad

# With ngrok tunnel (for GitHub webhooks)
docker-compose --profile tunnel up -d
```

### Verify Configuration

```bash
sdlc-agent verify
```

## GitHub App Setup

1. Go to **Settings > Developer settings > GitHub Apps**
2. Click **New GitHub App**
3. Configure:
   - **Name**: SDLC Automation Agent
   - **Homepage URL**: Your deployment URL
   - **Webhook URL**: `https://your-domain.com/webhook`
   - **Webhook secret**: Generate a secure secret

4. **Permissions**:
   | Permission | Access |
   |------------|--------|
   | Contents | Read & Write |
   | Issues | Read & Write |
   | Pull Requests | Read & Write |
   | Metadata | Read |
   | Checks | Read |

5. **Subscribe to events**:
   - Issues
   - Issue comment
   - Pull request
   - Pull request review
   - Check suite

6. Generate and download the private key

7. Install the app on your repository

## Usage Workflow

### 1. New Feature Request

```
Issue Created (#123)
    ↓
Requirements Agent: Analyzes issue, asks clarifying questions
    ↓
Issue Labeled "ready-for-stories"
    ↓
Story Writer Agent: Creates user stories
    ↓
PR Created with suggestions
    ↓
Implementation Agent: Provides code suggestions
    ↓
QA Agent: Creates test checklist, reviews changes
```

### 2. Bug Report

```
Bug Issue Created (#456)
    ↓
Issue Resolver Agent: Analyzes bug, searches codebase
    ↓
Root cause identified, fix suggested
    ↓
Implementation Agent: Provides fix suggestions
    ↓
QA Agent: Validates fix
```

### 3. PR Review

```
PR Opened (#789)
    ↓
QA Agent: Reviews against acceptance criteria
    ↓
Creates test checklist
    ↓
Implementation Agent: Suggests improvements
    ↓
QA Agent: Final approval
```

## AWS Deployment

### Deploy with SAM

```bash
cd infrastructure/aws

# Build
sam build

# Deploy (interactive)
sam deploy --guided

# Deploy to specific environment
sam deploy --config-env prod
```

### Required Secrets (in AWS Secrets Manager)

- `sdlc-agent/anthropic-api-key`
- `sdlc-agent/github-app-id`
- `sdlc-agent/github-app-private-key`
- `sdlc-agent/github-webhook-secret`

## Development

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=agent_squad_sdlc --cov-report=html

# Specific test file
pytest tests/test_agents.py -v
```

### Code Quality

```bash
# Linting
ruff check .

# Type checking
mypy agent_squad_sdlc
```

### Project Structure

```
experiment/
├── agent_squad_sdlc/
│   ├── agents/           # Agent implementations
│   ├── tools/            # GitHub API tools
│   ├── prompts/          # Agent system prompts
│   ├── github_app/       # GitHub App authentication
│   ├── handlers/         # CLI and webhook handlers
│   ├── config.py         # Configuration
│   └── main.py           # Entry point
├── infrastructure/
│   ├── docker/           # Docker and Compose files
│   ├── localstack/       # LocalStack init scripts
│   └── aws/              # SAM templates
├── tests/                # Test suite
└── README.md
```

## Configuration Reference

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key | Required |
| `CLAUDE_MODEL_ID` | Claude model to use | `claude-sonnet-4-20250514` |
| `GITHUB_APP_ID` | GitHub App ID | Required |
| `GITHUB_APP_PRIVATE_KEY` | GitHub App private key | Required |
| `GITHUB_WEBHOOK_SECRET` | Webhook secret | Required |
| `GITHUB_OWNER` | Repository owner | Required |
| `GITHUB_REPO` | Repository name | Required |
| `ENVIRONMENT` | Environment (local/dev/staging/prod) | `local` |
| `STORAGE_TYPE` | Storage backend (memory/dynamodb) | `memory` |
| `AWS_REGION` | AWS region | `us-east-1` |
| `AWS_ENDPOINT_URL` | AWS endpoint (for LocalStack) | None |
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8080` |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
