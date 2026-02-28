from langchain_core.tools import tool


@tool
def start_cleaning() -> str:
    """Inicia a limpeza do robô aspirador. Use quando o usuário pedir para limpar, aspirar, começar, iniciar limpeza."""
    return "Limpeza iniciada."


@tool
def stop_cleaning() -> str:
    """Para a limpeza do robô. Use quando o usuário pedir para parar, pausar, interromper."""
    return "Limpeza pausada."


@tool
def return_to_base() -> str:
    """Envia o robô de volta para a base de carregamento. Use quando o usuário pedir para voltar, retornar à base, encostar, carregar."""
    return "Robô retornando à base."


@tool
def locate_robot() -> str:
    """Faz o robô emitir um som ou sinal para localização. Use quando o usuário pedir para encontrar, localizar, onde está o robô."""
    return "Comando de localização enviado."


@tool
def clean_specific_room(room_name: str) -> str:
    """Limpa um cômodo específico da casa. room_name: nome do cômodo (ex: cozinha, sala, quarto, banheiro)."""
    return f"Limpando o cômodo: {room_name}."
