"""
Script para fazer pull de prompts do LangSmith Prompt Hub.
"""

import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv
from langsmith import Client


load_dotenv()

PROMPT_NAME = "leonanluppi/bug_to_user_story_v1"
OUTPUT_PATH = Path("prompts/bug_to_user_story_v1.yml")


def prompt_to_dict(prompt):
    data = {
        "name": "bug_to_user_story_v1",
        "version": "1.0",
        "description": "Prompt inicial de baixa qualidade para converter bug reports em user stories.",
        "source": PROMPT_NAME,
        "prompt_type": prompt.__class__.__name__,
        "input_variables": getattr(prompt, "input_variables", []),
    }

    if hasattr(prompt, "messages"):
        messages = []

        for message in prompt.messages:
            message_type = message.__class__.__name__

            if hasattr(message, "prompt"):
                content = getattr(message.prompt, "template", str(message.prompt))
            else:
                content = getattr(message, "template", str(message))

            messages.append({
                "type": message_type,
                "content": content
            })

        data["messages"] = messages
    else:
        data["template"] = getattr(prompt, "template", str(prompt))

    return data


def pull_prompts_from_langsmith():
    print("=" * 60)
    print("PULL DO PROMPT INICIAL")
    print("=" * 60)

    client = Client()

    print(f"Baixando prompt: {PROMPT_NAME}")

    prompt = client.pull_prompt(PROMPT_NAME)

    prompt_data = prompt_to_dict(prompt)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
        yaml.dump(
            prompt_data,
            file,
            allow_unicode=True,
            sort_keys=False
        )

    print(f"Prompt salvo em: {OUTPUT_PATH}")
    print("Pull finalizado com sucesso!")

    return prompt_data


def main():
    try:
        pull_prompts_from_langsmith()
        return 0
    except Exception as error:
        print(f"Erro ao fazer pull do prompt: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())