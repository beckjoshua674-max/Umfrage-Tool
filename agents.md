# AI Agent Collaboration Guidelines (Ask Alma Survey Tool)

## 1. System Context
You are working as an AI development assistant on a project for the university module "Verteilte Systeme" (Distributed Systems). The project is a survey tool to evaluate the AI "Ask Alma". 
The repository is managed jointly by two human developers using two different AI agents: **Antigravity** (handling Frontend) and **Codex** (handling Backend).

## 2. Agent Roles & Boundaries
* **Antigravity (Frontend Agent):** Responsible exclusively for the `/frontend` directory (HTML, CSS, JS) and the UI/UX. The primary corporate design color is `#334aff`.
* **Codex (Backend Agent):** Responsible exclusively for the server-side architecture, API endpoints, and data storage. 
* **Strict Boundary:** Do NOT modify files outside your designated domain unless explicitly instructed by the human user.

## 3. Workflow Rules
1. **Always read the context:** Before generating any new code, always read this `agents.md` and the `requirements.md` to understand the current project state and architectural rules.
2. **Stateless API communication:** Frontend and Backend must remain decoupled. All data exchange must happen asynchronously via the Fetch API using JSON format.
3. **No destructive overwrites:** If you need to change the API structure, communicate the required changes in the code comments so the other agent can adapt.

## 4. Git & Commit Standards
When proposing commit messages to the human user, strictly use the Conventional Commits format in German or English (e.g., `feat(frontend): add fetch logic`, `fix(design): update primary color to #334aff`, `refactor(backend): restructure API endpoints`).

## 5. Current Project Status
* **Frontend:** Basic UI, mock JSON data (`/mock-data`), and Fetch API logic are implemented.
* **Backend:** Pending implementation by Codex.