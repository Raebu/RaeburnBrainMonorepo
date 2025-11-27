# AI Code Assistant

This repository contains a local, API-driven code assistant inspired by RooCoder.
It features a Node.js/Express backend and a React/Tailwind frontend with a
Monaco-based editor. Additional prototype scripts live alongside the main app for
crypto, deployment, and security experiments.

## Directory Overview

| Path | Description |
| ---- | ----------- |
| `code-assistant/` | Main application source code. Contains the backend and frontend. |
| `src/` | Small Python demos for model usage (Gradio interface and API generation). |
| `crypto/` | Example scripts for crypto listings and NFT deployment. |
| `deployment/` | Automation script for mobile app deployment. |
| `marketplace/` | Marketing helper for generating promotional content. |
| `monetization/` | Example Stripe integration. |
| `security/` | Utilities for watermarking and copyright protection. |
| `self_improvement/` | Prototype self-improving model updater. |
| `docs/` | Documentation assets such as screenshots. |
| `.github/workflows/` | Continuous integration workflow. |
| `Dockerfile` | Container build instructions. |
| `.env.example` | Example environment variables. |

### `code-assistant/`

```
code-assistant/
  backend/
    server.js         # Express server wiring routes and middleware
    router.js         # AI model router (OpenRouter/HuggingFace)
    fsController.js   # Local file system & git helpers
    auth.js           # JWT auth middleware
    package.json      # Backend dependencies and scripts
    jest.config.js    # Jest test config
    test/             # Backend unit tests
  frontend/
    src/
      components/     # React UI pieces (Editor, FileTree, etc.)
      utils/          # Frontend utilities
      main.tsx        # Vite entry point
      App.tsx         # Root component
    index.html        # Vite HTML shell
    package.json      # Frontend dependencies and scripts
    tailwind.config.js
    vitest.setup.ts   # Vitest config
```

The backend exposes REST endpoints for file management, AI completions, session
handling and basic git operations. The frontend provides a tabbed Monaco editor,
file browser, chat/prompt panel and quota bar.

## Setup

1. **Clone and configure**
   ```bash
   git clone <repo-url>
   cd AI_Auto_Developer
   cp .env.example .env            # provide your API keys and auth credentials
   ```

2. **Install backend dependencies**
   ```bash
   cd code-assistant/backend
   npm install
   ```

3. **Install frontend dependencies**
   ```bash
   cd ../frontend
   npm install
   ```

4. **Run in development**
   ```bash
   # terminal 1
   cd code-assistant/backend && npm start

   # terminal 2
   cd code-assistant/frontend && npm run dev
   ```
   The frontend dev server runs on [http://localhost:5173](http://localhost:5173)
and proxies API requests to the backend on port `3001`.

5. **Docker (optional)**
   ```bash
   docker build -t code-assistant .
   docker run --env-file .env -p 3001:3001 code-assistant
   ```
   The Express server serves the compiled frontend at
   [http://localhost:3001](http://localhost:3001).

## Tests and Linting

Both packages use ESLint and have unit tests (`Jest` for the backend,
`Vitest` for the frontend).

```bash
# backend
cd code-assistant/backend && npm run lint && npm test

# frontend
cd ../frontend && npm run lint && npm test
```

> Note: the sandbox environment may not allow installing dependencies. Locally,
> ensure `npm install` succeeds before running these commands.

## Usage

- **File browser** in the left sidebar lists local files. Double-click to open in
  a new tab. Unsaved changes are indicated with an asterisk. Autosave occurs
  every three seconds.
- **Prompt panel** under the editor lets you choose a role and send freeform
  prompts or run code-improvement actions. The assistant response shows which
  model was used and token counts.
- **Git integration** allows staging files and committing directly from the UI
  using the backend git endpoints.
- **Sessions** can be saved and loaded via `/api/session/fullsave` and
  `/api/session/fullload`. Projects can be exported as a ZIP via `/api/export`.

## Environment Variables

```
OPENROUTER_API_KEY=your-openrouter-key
HUGGINGFACE_API_KEY=your-huggingface-key
PORT=3001
QUOTA_LIMIT=50000
AUTH_USER=admin
AUTH_PASS=changeme
AUTH_SECRET=supersecret
```

Store them in a local `.env` file; never commit your actual keys.

## License

See [Licence.md](Licence.md) for the proprietary license terms.
