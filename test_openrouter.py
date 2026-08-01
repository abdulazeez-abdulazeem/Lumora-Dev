import os

from langchain_core.messages import HumanMessage

from agent import get_llm


def main() -> None:
    if not os.getenv("OPENROUTER_API_KEY"):
        print("OPENROUTER_API_KEY is not set. Skipping model request.")
        return

    llm = get_llm()
    response = llm.invoke([HumanMessage(content="Hello")])
    print(response.content)


if __name__ == "__main__":
    main()
