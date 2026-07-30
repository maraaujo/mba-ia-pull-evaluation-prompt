"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Lê o prompt otimizado de prompts/bug_to_user_story_v2.yml
2. Valida a estrutura básica do prompt
3. Cria um ChatPromptTemplate
4. Faz push para o LangSmith Hub
5. Tenta marcar o prompt como público
"""

import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv
from langsmith import Client
from langchain_core.prompts import ChatPromptTemplate


load_dotenv()


PROMPT_FILE = Path("prompts/bug_to_user_story_v2.yml")
DEFAULT_PROMPT_NAME = "bug_to_user_story_v2"


def load_prompt_yaml(path: Path) -> dict:
    """Carrega o arquivo YAML do prompt otimizado."""
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    with open(path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida estrutura básica do prompt otimizado.

    Returns:
        (is_valid, errors)
    """
    errors = []

    if not prompt_data:
        errors.append("O arquivo YAML está vazio.")
        return False, errors

    if not prompt_data.get("name"):
        errors.append("Campo obrigatório ausente: name")

    if not prompt_data.get("description"):
        errors.append("Campo obrigatório ausente: description")

    if not prompt_data.get("system_prompt"):
        errors.append("Campo obrigatório ausente: system_prompt")

    if not prompt_data.get("user_prompt"):
        errors.append("Campo obrigatório ausente: user_prompt")

    input_variables = prompt_data.get("input_variables", [])
    if "bug_report" not in input_variables:
        errors.append("input_variables deve conter bug_report")

    metadata = prompt_data.get("metadata", {})
    techniques = metadata.get("techniques", [])

    if len(techniques) < 2:
        errors.append("metadata.techniques deve conter pelo menos 2 técnicas")

    full_text = yaml.dump(prompt_data, allow_unicode=True)

    if "[TODO]" in full_text or "TODO" in full_text:
        errors.append("O prompt ainda contém TODO ou [TODO].")

    return len(errors) == 0, errors


def build_chat_prompt(prompt_data: dict) -> ChatPromptTemplate:
    """
    Constrói um ChatPromptTemplate a partir do YAML.
    """
    system_prompt = prompt_data["system_prompt"]
    user_prompt = prompt_data["user_prompt"]

    return ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", user_prompt),
        ]
    )


def get_prompt_identifier(prompt_data: dict) -> str:
    """
    Monta o nome do prompt para push.

    Se USERNAME_LANGSMITH_HUB existir, usa:
    {username}/bug_to_user_story_v2

    Caso contrário, usa apenas:
    bug_to_user_story_v2
    """
    username = os.getenv("USERNAME_LANGSMITH_HUB") or os.getenv("LANGSMITH_USERNAME")
    prompt_name = prompt_data.get("name", DEFAULT_PROMPT_NAME)

    if username:
        return f"{username}/{prompt_name}"

    return prompt_name
    """
    Monta o nome do prompt para push.

    Se LANGSMITH_USERNAME existir, usa:
    {username}/bug_to_user_story_v2

    Caso contrário, usa apenas:
    bug_to_user_story_v2
    """
    username = os.getenv("LANGSMITH_USERNAME")
    prompt_name = prompt_data.get("name", DEFAULT_PROMPT_NAME)

    if username:
        return f"{username}/{prompt_name}"

    return prompt_name
def get_prompt_identifier(prompt_data: dict) -> str:
    username = os.getenv("USERNAME_LANGSMITH_HUB") or os.getenv("LANGSMITH_USERNAME")
    prompt_name = prompt_data.get("name", DEFAULT_PROMPT_NAME)

    if username and "@" in username:
        raise ValueError(
            "USERNAME_LANGSMITH_HUB não pode ser e-mail. Use o handle público do LangSmith Hub."
        )

    if username:
        return f"{username}/{prompt_name}"

    return prompt_name

def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub.

    Args:
        prompt_name: Nome/identificador do prompt
        prompt_data: Dados do prompt em dict

    Returns:
        True se sucesso, False caso contrário
    """
    client = Client()

    prompt = build_chat_prompt(prompt_data)

    description = prompt_data.get("description", "")
    metadata = prompt_data.get("metadata", {})
    tags = metadata.get("tags", [])

    print("=" * 60)
    print("PUSH DO PROMPT OTIMIZADO")
    print("=" * 60)
    print(f"Prompt: {prompt_name}")
    print(f"Descrição: {description}")
    print(f"Técnicas: {', '.join(metadata.get('techniques', []))}")

    try:
        url = client.push_prompt(
            prompt_name,
            object=prompt,
            description=description,
            tags=tags,
        )

        print(f"Prompt enviado com sucesso!")
        print(f"URL: {url}")

        # Tenta deixar público. Em algumas versões do SDK isso pode variar.
        try:
            client.update_prompt(
                prompt_name,
                is_public=True
            )
            print("Prompt marcado como público.")
        except Exception as public_error:
            print("Não foi possível marcar como público automaticamente.")
            print(f"Detalhe: {public_error}")
            print("Se necessário, abra o prompt no LangSmith e marque como Public manualmente.")

        return True

    except TypeError:
        # Fallback para versões do SDK que não aceitam description/tags no push_prompt.
        try:
            url = client.push_prompt(
                prompt_name,
                object=prompt,
            )

            print(f"Prompt enviado com sucesso!")
            print(f"URL: {url}")

            try:
                client.update_prompt(
                    prompt_name,
                    description=description,
                    is_public=True
                )
                print("Metadados atualizados e prompt marcado como público.")
            except Exception as update_error:
                print("Prompt enviado, mas não foi possível atualizar metadados/publicação automaticamente.")
                print(f"Detalhe: {update_error}")
                print("Se necessário, ajuste descrição/tags/public manualmente no LangSmith.")

            return True

        except Exception as error:
            print(f"Erro ao fazer push do prompt: {error}")
            return False

    except Exception as error:
        print(f"Erro ao fazer push do prompt: {error}")
        return False


def main():
    """Função principal."""
    try:
        if not os.getenv("LANGSMITH_API_KEY"):
            print("Erro: LANGSMITH_API_KEY não encontrada no .env")
            return 1

        prompt_data = load_prompt_yaml(PROMPT_FILE)

        is_valid, errors = validate_prompt(prompt_data)

        if not is_valid:
            print("Prompt inválido. Corrija os erros abaixo:")
            for error in errors:
                print(f"- {error}")
            return 1

        prompt_name = get_prompt_identifier(prompt_data)

        success = push_prompt_to_langsmith(
            prompt_name=prompt_name,
            prompt_data=prompt_data
        )

        return 0 if success else 1

    except Exception as error:
        print(f"Erro inesperado: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())