"""
Lumora Development Agent – Stage 1 (+ Stage 2 preparation)

Basic Coding Assistant with:
- Strong Lumora Studio knowledge
- Conversation memory
- Basic file system tools (read / write / list) so it can work on real project files
"""

import os
from pathlib import Path
from typing import Annotated, TypedDict, Literal
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode

load_dotenv()

# ------------------------------------------------------------
# Project root (the folder where the agent is running)
# ------------------------------------------------------------
PROJECT_ROOT = Path.cwd()


# ------------------------------------------------------------
# 1. Tools – basic file operations (Stage 2 preparation)
# ------------------------------------------------------------
@tool
def list_files(directory: str = ".") -> str:
    """List files and folders in a directory (relative to current working directory).
    Use this to understand the project structure.
    Example: list_files(".") or list_files("src/app")
    """
    try:
        path = (PROJECT_ROOT / directory).resolve()
        if not str(path).startswith(str(PROJECT_ROOT.resolve())):
            return "Error: Access outside project root is not allowed."
        if not path.exists():
            return f"Directory not found: {directory}"
        if not path.is_dir():
            return f"Not a directory: {directory}"

        items = []
        for item in sorted(path.iterdir()):
            prefix = "📁 " if item.is_dir() else "📄 "
            items.append(f"{prefix}{item.name}")
        return "\n".join(items) if items else "(empty directory)"
    except Exception as e:
        return f"Error listing files: {str(e)}"


@tool
def read_file(filepath: str) -> str:
    """Read the contents of a file.
    Use this to examine existing code before editing or explaining it.
    Example: read_file("src/app/page.tsx")
    """
    try:
        path = (PROJECT_ROOT / filepath).resolve()
        if not str(path).startswith(str(PROJECT_ROOT.resolve())):
            return "Error: Access outside project root is not allowed."
        if not path.exists():
            return f"File not found: {filepath}"
        if not path.is_file():
            return f"Not a file: {filepath}"

        content = path.read_text(encoding="utf-8")
        # Limit very large files
        if len(content) > 15000:
            return content[:15000] + "\n\n... [file truncated – too large]"
        return content
    except Exception as e:
        return f"Error reading file: {str(e)}"


@tool
def write_file(filepath: str, content: str) -> str:
    """Create or overwrite a file with the given content.
    Always confirm with the user before overwriting important files.
    Example: write_file("src/components/Button.tsx", "export function Button() { ... }")
    """
    try:
        path = (PROJECT_ROOT / filepath).resolve()
        if not str(path).startswith(str(PROJECT_ROOT.resolve())):
            return "Error: Access outside project root is not allowed."

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} characters to {filepath}"
    except Exception as e:
        return f"Error writing file: {str(e)}"


@tool
def create_directory(directory: str) -> str:
    """Create a new directory (and parent directories if needed).
    Example: create_directory("src/components/ui")
    """
    try:
        path = (PROJECT_ROOT / directory).resolve()
        if not str(path).startswith(str(PROJECT_ROOT.resolve())):
            return "Error: Access outside project root is not allowed."
        path.mkdir(parents=True, exist_ok=True)
        return f"Directory created (or already exists): {directory}"
    except Exception as e:
        return f"Error creating directory: {str(e)}"


TOOLS = [list_files, read_file, write_file, create_directory]


# ------------------------------------------------------------
# 2. Improved System Prompt – deep Lumora knowledge
# ------------------------------------------------------------
SYSTEM_PROMPT = """You are **Lumora Development Agent** (Stage 1 + file tools).

You are a focused AI software engineer whose only mission is to help build, improve, and maintain **Lumora Studio**.

### About Lumora Studio
- Natural-language AI platform that lets people create websites, web apps, mobile apps, dashboards, AI agents, and automations using plain English.
- Name meaning: simple, modern, premium.
- Target: professional quality while staying free-tier friendly and usable from Android phones.

### Official Tech Stack (never drift from this unless asked)
- Frontend / Full-stack: Next.js (App Router) + TypeScript + Tailwind CSS + React
- Backend / Auth / Database: Supabase
- Version Control: GitHub
- Deployment: Vercel
- AI: OpenRouter (OpenAI-compatible)
- Future agent layer: LangGraph + OpenRouter

### Your Current Capabilities
1. Generate clean, modern, production-ready code
2. Explain code simply and clearly
3. Debug and fix errors
4. Read, write, and list real project files using tools
5. Suggest architecture and best practices for the Lumora stack
6. Remember conversation history and previous decisions

### How you work
- Always prefer the official Lumora stack.
- When writing code → use TypeScript + modern App Router patterns + Tailwind.
- Before editing existing files → read them first with the read_file tool.
- When creating new files → use write_file and create_directory tools.
- Be concise but complete. Prefer working code over long explanations.
- If the user is on Android/Termux, keep advice practical for that environment.
- Explain every important change you make.

### Long-term vision you are part of
You will eventually become a senior-level AI developer that can plan features, refactor, write tests, open PRs, and deploy Lumora Studio with minimal supervision — while remaining affordable enough to run from a phone.

You are Stage 1 (with file tools prepared for Stage 2). Act like a reliable coding partner.
"""


# ------------------------------------------------------------
# 3. State
# ------------------------------------------------------------
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# ------------------------------------------------------------
# 4. LLM + Tools
# ------------------------------------------------------------
def get_llm():
    provider = os.getenv("PROVIDER", "openrouter").strip().lower()
    if provider != "openrouter":
        raise ValueError(
            "Unsupported provider. Set PROVIDER=openrouter in your .env file."
        )

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY not found.\n"
            "Create a .env file and add your key from https://openrouter.ai/keys"
        )

    model = os.getenv("MODEL", "qwen/qwen3-coder:free")
    llm = ChatOpenAI(
        model=model,
        temperature=0.3,
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )
    return llm.bind_tools(TOOLS)


# ------------------------------------------------------------
# 5. Nodes
# ------------------------------------------------------------
def call_model(state: AgentState):
    llm = get_llm()
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}


def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "__end__"


# ------------------------------------------------------------
# 6. Build the agent graph
# ------------------------------------------------------------
def create_agent():
    workflow = StateGraph(AgentState)

    workflow.add_node("assistant", call_model)
    workflow.add_node("tools", ToolNode(TOOLS))

    workflow.add_edge(START, "assistant")
    workflow.add_conditional_edges("assistant", should_continue)
    workflow.add_edge("tools", "assistant")

    memory = MemorySaver()
    agent = workflow.compile(checkpointer=memory)
    return agent


# ------------------------------------------------------------
# 7. CLI (Termux-friendly)
# ------------------------------------------------------------
def main():
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel

    console = Console()
    agent = create_agent()
    config = {"configurable": {"thread_id": "lumora-dev-session"}}

    console.print(
        Panel.fit(
            "[bold cyan]Lumora Development Agent[/bold cyan]\n"
            "Stage 1 + File Tools\n"
            "Generate • Explain • Debug • Read/Write files\n\n"
            "Type your request  |  'exit' to quit",
            border_style="cyan",
        )
    )

    while True:
        try:
            user_input = console.input("\n[bold green]You:[/bold green] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Goodbye! Keep building Lumora.[/yellow]")
            break

        if user_input.lower() in {"exit", "quit", "q"}:
            console.print("[yellow]Goodbye! Keep building Lumora.[/yellow]")
            break

        if not user_input:
            continue

        result = agent.invoke(
            {"messages": [HumanMessage(content=user_input)]},
            config=config,
        )

        # Show only the final AI response (skip intermediate tool messages for clean UI)
        for msg in reversed(result["messages"]):
            if msg.type == "ai" and msg.content:
                console.print("\n[bold blue]Lumora Agent:[/bold blue]")
                console.print(Markdown(msg.content))
                break


if __name__ == "__main__":
    main()
