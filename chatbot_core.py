# chatbot_core.py
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import List, Dict, Protocol, Optional, Tuple

try:
    # SDK nuevo
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # El import puede fallar en análisis estático; en runtime te avisamos.


# ==========================
# Strategy
# ==========================
class StrategyChatbot(Protocol):
    """Protocolo de estrategia: define el modelo a usar."""
    @property
    def nombre_modelo(self) -> str: ...


@dataclass
class Modelo4oMini:
    @property
    def nombre_modelo(self) -> str:
        # Ajusta si usas otro alias en tu cuenta
        return "gpt-4o-mini"


@dataclass
class Modelo4o:
    @property
    def nombre_modelo(self) -> str:
        return "gpt-4o"


# ==========================
# Componente base del Decorator
# ==========================
class IChat(Protocol):
    def enviarmensaje(self, texto: str) -> List[Dict[str, str]]: ...
    @property
    def modelo(self) -> str: ...
    def set_estrategia(self, estrategia: StrategyChatbot) -> None: ...
    def set_contexto(self, contexto: str) -> None: ...
    @property
    def historial(self) -> List[Dict[str, str]]: ...


# ==========================
# Chatbot (Componente Concreto)
# ==========================
class Chatbot(IChat):
    """
    Envuelve la llamada a OpenAI. Mantiene historial y contexto.
    """
    def __init__(self, estrategia: StrategyChatbot, contexto_inicial: str = "", api_key: Optional[str] = None):
        if OpenAI is None:
            raise RuntimeError("No se pudo importar 'openai'. Instala el SDK: pip install openai")

        api_key_final = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key_final:
            raise RuntimeError(
                "OPENAI_API_KEY no encontrado. Pásalo al ControladorChatbot(api_key=...) "
                "o exporta la variable de entorno."
            )

        self._client = OpenAI(api_key=api_key_final)
        self._estrategia = estrategia
        self._contexto = contexto_inicial or ""
        self._historial: List[Dict[str, str]] = []  # mensajes estilo Chat: [{"role": "...", "content": "..."}]

    # IChat
    @property
    def modelo(self) -> str:
        return self._estrategia.nombre_modelo

    def set_estrategia(self, estrategia: StrategyChatbot) -> None:
        self._estrategia = estrategia

    def set_contexto(self, contexto: str) -> None:
        self._contexto = contexto or ""

    @property
    def historial(self) -> List[Dict[str, str]]:
        return self._historial

    # Llamada principal
    def enviarmensaje(self, texto: str) -> List[Dict[str, str]]:
        """
        Devuelve [msg_usuario, msg_asistente], y además agrega ambos al historial.
        """
        user_msg = {"role": "user", "content": texto}

        # Construye el prompt con system + historial + user
        mensajes = []
        if self._contexto:
            mensajes.append({"role": "system", "content": self._contexto})
        if self._historial:
            mensajes.extend(self._historial)
        mensajes.append(user_msg)

        # Llamada al endpoint de chat
        try:
            resp = self._client.chat.completions.create(
                model=self._estrategia.nombre_modelo,
                messages=mensajes,
                temperature=0.2,
            )
            assistant_text = (resp.choices[0].message.content or "").strip()
        except Exception as ex:
            # No rompas la UI: devuelve un mensaje de error como assistant
            assistant_text = f"[Error al llamar al modelo {self._estrategia.nombre_modelo}: {ex}]"

        assistant_msg = {"role": "assistant", "content": assistant_text}

        # Guarda solo user y assistant (omitimos el system para no duplicar)
        self._historial.append(user_msg)
        self._historial.append(assistant_msg)

        return [user_msg, assistant_msg]


# ==========================
# Decorators
# ==========================
class Decorator(IChat):
    def __init__(self, base: IChat):
        self._base = base

    # Delegaciones por defecto
    def enviarmensaje(self, texto: str) -> List[Dict[str, str]]:
        return self._base.enviarmensaje(texto)

    @property
    def modelo(self) -> str:
        return self._base.modelo

    def set_estrategia(self, estrategia: StrategyChatbot) -> None:
        self._base.set_estrategia(estrategia)

    def set_contexto(self, contexto: str) -> None:
        self._base.set_contexto(contexto)

    @property
    def historial(self) -> List[Dict[str, str]]:
        return self._base.historial


class Tokens(Decorator):
    """
    Calcula un conteo aproximado de tokens del turno actual.
    """
    def __init__(self, base: IChat):
        super().__init__(base)
        self.last_tokens_aprox: int = 0

    def _approx_tokens(self, text: str) -> int:
        # estimación muy simple; ajusta si quieres algo más preciso
        # (aprox 4 chars por token o 0.75 * palabras, etc.)
        return max(1, int(len(text) / 4))

    def enviarmensaje(self, texto: str) -> List[Dict[str, str]]:
        turno = self._base.enviarmensaje(texto)
        total_text = " ".join(m.get("content", "") for m in turno)
        self.last_tokens_aprox = self._approx_tokens(total_text)
        return turno


class Latencia(Decorator):
    """
    Mide la latencia de la llamada a enviarmensaje().
    """
    def __init__(self, base: IChat):
        super().__init__(base)
        self.last_latency_ms: int = 0

    def enviarmensaje(self, texto: str) -> List[Dict[str, str]]:
        t0 = time.perf_counter()
        turno = self._base.enviarmensaje(texto)
        t1 = time.perf_counter()
        self.last_latency_ms = int((t1 - t0) * 1000)
        return turno


# ==========================
# Controlador
# ==========================
class ControladorChatbot:
    """
    Orquesta el chatbot, mantiene contexto e historial,
    permite cambiar de modelo (estrategia) y expone métricas.
    """
    def __init__(self, estrategia: StrategyChatbot, contexto_inicial: str = "", api_key: Optional[str] = None):
        # Cadena de decorators: Latencia(Tokens(Chatbot)))
        base = Chatbot(estrategia=estrategia, contexto_inicial=contexto_inicial, api_key=api_key)
        d_tokens = Tokens(base)
        d_lat = Latencia(d_tokens)

        self._root: IChat = d_lat
        self._tokens: Tokens = d_tokens
        self._latencia: Latencia = d_lat

    # API pública usada por tu UI
    def enviarmensaje(self, texto: str) -> List[Dict[str, str]]:
        return self._root.enviarmensaje(texto)

    def cambiarmodelo(self, nueva: StrategyChatbot) -> None:
        self._root.set_estrategia(nueva)

    def actualizarContexto(self, contexto: str) -> None:
        self._root.set_contexto(contexto)

    @property
    def historial(self) -> List[Dict[str, str]]:
        return self._root.historial

    @property
    def metricas(self) -> Dict[str, int | str]:
        return {
            "modelo": self._root.modelo,
            "lat_ms": getattr(self._latencia, "last_latency_ms", 0),
            "tokens_aprox": getattr(self._tokens, "last_tokens_aprox", 0),
        }
    def preguntar(self, texto: str) -> str:
        """
        Alias cómodo para el UI. Devuelve solo el texto de la respuesta.
        Internamente usa enviarmensaje(...) que retorna el turno completo.
        """
        turn = self.enviarmensaje(texto)
        # turn debería ser una lista de mensajes estilo [{"role":"assistant","content":"..."}]
        if isinstance(turn, list) and turn:
            last = turn[-1]
            return last.get("content") if isinstance(last, dict) else str(last)
        # fallback
        return ""