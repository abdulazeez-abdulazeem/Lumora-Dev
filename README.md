# Lumora Development Agent

**Your personal AI coding partner for building Lumora Studio**

Stage 1 (with Stage 2 file tools already prepared)

---

### What it can do right now

- Generate clean Next.js + TypeScript + Tailwind code
- Explain any code clearly
- Help debug and fix errors
- **Read, write, list, and create real project files**
- Remember the full conversation in the current session
- Stay strictly focused on the Lumora Studio tech stack and vision

---

### Official Lumora Stack (the agent knows this deeply)

| Layer            | Technology                  |
|------------------|-----------------------------|
| Frontend         | Next.js (App Router)        |
| Language         | TypeScript                  |
| Styling          | Tailwind CSS                |
| UI               | React                       |
| Backend / Auth   | Supabase                    |
| Version Control  | GitHub                      |
| Deployment       | Vercel                      |
| AI               | Google Gemini API           |
| Future Agent     | LangGraph + Gemini          |

---

## Quick Start (Termux / Android or any computer)

```bash
# 1. Clone or copy this folder
cd lumora-agent

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate          # Termux / Linux / macOS
# venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your free Gemini API key
cp .env.example .env
# Edit .env and paste your key from → https://aistudio.google.com/app/apikey

# 5. Run the agent
python agent.py
```

---

## Example conversations

```
You: Create a modern landing page for Lumora Studio using Next.js App Router, TypeScript and Tailwind

You: List all files in the current directory

You: Read the file src/app/page.tsx and improve the hero section

You: I'm getting this error: [paste error]. Fix it.

You: Create a new component at src/components/ui/Button.tsx
```

The agent will use the file tools automatically when needed.

Type `exit` or `quit` to stop.

---

## Project Structure

```
lumora-agent/
├── agent.py              ← Main agent (Stage 1 + file tools)
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── LICENSE (optional)
```

---

## Push this agent to GitHub (recommended)

1. Create a new repository on GitHub (e.g. `lumora-agent`)
2. In this folder run:

```bash
git init
git add .
git commit -m "Initial commit: Lumora Development Agent Stage 1"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/lumora-agent.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your real GitHub username.

**Important**: Never commit your real `.env` file. The `.gitignore` already protects it.

---

## Roadmap

| Stage | Focus                                      | Status          |
|-------|--------------------------------------------|-----------------|
| 1     | Basic coding + memory + file tools         | ✅ You are here |
| 2     | Deep project awareness + multi-file edits  | Next            |
| 3     | Planning, refactoring, tests, documentation| Later           |
| 4     | Autonomous (PRs, deploy, monitor)          | Long-term       |

---

## Tips for Android / Termux

- Keep the same terminal session open so conversation memory stays alive
- Run the agent **inside** your Lumora Studio project folder if you want it to edit real files
- Use `gemini-2.0-flash` (already set) to stay within free limits
- Later you can add GitHub / Vercel / Supabase tools

---

Built free-first • Android-first • Memory-first  
Part of the Lumora journey.
