# Lumora Development Agent

A personal AI coding partner for building Lumora Studio — Stage 1 with file tools.

## Stack

| Layer     | Technology                              |
|-----------|-----------------------------------------|
| Runtime   | Python 3.12                             |
| Agent     | LangGraph + LangChain                  |
| LLM       | OpenRouter (default: qwen/qwen3-coder:free) |
| UI        | Rich (terminal / console)              |

## How to run

```bash
python agent.py
```

The agent starts an interactive CLI session. Type your request and press Enter.  
Type `exit`, `quit`, or `q` to stop.

## Environment variables

| Variable           | Description                              |
|--------------------|------------------------------------------|
| `OPENROUTER_API_KEY` | Your OpenRouter API key (secret)        |
| `PROVIDER`           | Must be `openrouter` (default)          |
| `MODEL`              | Model to use (default: `qwen/qwen3-coder:free`) |

## Testing

```bash
python test_openrouter.py
```

Sends a single "Hello" message to the LLM and prints the response — confirms the API key and model are working.

## Project structure

```
lumora-agent/
├── agent.py              ← Main agent (LangGraph graph + CLI)
├── test_openrouter.py    ← Quick connectivity test
├── requirements.txt      ← Python dependencies
├── .env.example          ← Template for local .env
├── .gitignore
└── README.md
```

## User preferences

- Keep the Lumora Studio tech stack (Next.js, TypeScript, Tailwind, Supabase, OpenRouter).
- Do not change the project architecture unless absolutely necessary.
- Default model: `qwen/qwen3-coder:free`.
