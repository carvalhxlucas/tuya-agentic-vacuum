import os
import re
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from agent.tools import (
    clean_specific_room,
    locate_robot,
    return_to_base,
    start_cleaning,
    stop_cleaning,
)

ROBOT_TOOLS = [start_cleaning, stop_cleaning, return_to_base, locate_robot, clean_specific_room]

def _friendly_message(action: str, params: dict) -> str:
    if action == "start_cleaning":
        return "Entendido, iniciando a limpeza agora."
    if action == "stop_cleaning":
        return "Entendido, pausando o robô."
    if action == "return_to_base":
        return "Entendido, mandando o robô voltar para a base."
    if action == "locate_robot":
        return "Entendido, enviando comando para o robô se localizar."
    if action == "clean_specific_room":
        room = (params or {}).get("room_name") if isinstance(params, dict) else None
        if isinstance(room, str):
            return f"Entendido, mandando o robô limpar {room} agora."
    return "Comando executado."


SYSTEM_PROMPT = """Você é o assistente de controle de um robô aspirador. O usuário dá comandos em linguagem natural.
Sua tarefa é interpretar a intenção e usar EXATAMENTE uma das ferramentas disponíveis.
Responda em português, de forma breve e amigável, confirmando a ação executada.
Use apenas as ferramentas fornecidas; não invente outras ações."""


def _fallback_intent(message: str) -> tuple[str, Optional[str], Optional[dict]]:
    text = message.lower().strip()
    if any(w in text for w in ["limpar", "limpe", "aspirar", "começar", "iniciar", "liga", "start"]):
        if "cozinha" in text:
            return ("Entendido, mandando o robô limpar a cozinha agora.", "clean_specific_room", {"room_name": "cozinha"})
        if "sala" in text:
            return ("Entendido, mandando o robô limpar a sala agora.", "clean_specific_room", {"room_name": "sala"})
        if "quarto" in text:
            return ("Entendido, mandando o robô limpar o quarto agora.", "clean_specific_room", {"room_name": "quarto"})
        if "banheiro" in text:
            return ("Entendido, mandando o robô limpar o banheiro agora.", "clean_specific_room", {"room_name": "banheiro"})
        return ("Entendido, iniciando a limpeza agora.", "start_cleaning", None)
    if any(w in text for w in ["parar", "pause", "pausar", "interromper", "para"]):
        return ("Entendido, pausando o robô.", "stop_cleaning", None)
    if any(w in text for w in ["voltar", "base", "encostar", "retornar", "carregar", "volta"]):
        return ("Entendido, mandando o robô voltar para a base.", "return_to_base", None)
    if any(w in text for w in ["localizar", "encontrar", "onde está", "achar"]):
        return ("Entendido, enviando comando para o robô se localizar.", "locate_robot", None)
    room_match = re.search(r"limpar\s+(?:a\s+|o\s+)?(\w+)", text)
    if room_match:
        room = room_match.group(1)
        return (f"Entendido, mandando o robô limpar {room} agora.", "clean_specific_room", {"room_name": room})
    return ("Não identifiquei um comando válido. Você pode pedir para iniciar ou pausar a limpeza, voltar à base, localizar o robô ou limpar um cômodo específico.", None, None)


def create_agent() -> Any:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
            llm_with_tools = llm.bind_tools(ROBOT_TOOLS)
            return {"type": "langchain", "llm": llm_with_tools}
        except Exception:
            pass
    return {"type": "fallback"}


def execute_agent(agent: Any, message: str) -> tuple[str, Optional[str], Optional[dict]]:
    if agent.get("type") == "fallback":
        return _fallback_intent(message)
    llm = agent.get("llm")
    if not llm:
        return _fallback_intent(message)
    try:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=message),
        ]
        response = llm.invoke(messages)
        if hasattr(response, "tool_calls") and response.tool_calls:
            tc = response.tool_calls[0]
            name = tc.get("name") or (getattr(tc, "name", None))
            args = tc.get("args") or {}
            if hasattr(tc, "args"):
                args = tc.args or args
            tool_map = {t.name: t for t in ROBOT_TOOLS}
            if name in tool_map:
                tool_map[name].invoke(args)
                friendly = _friendly_message(name, args)
                return (friendly, name, args if isinstance(args, dict) else None)
        return (response.content or "Comando processado.", None, None)
    except Exception:
        return _fallback_intent(message)
