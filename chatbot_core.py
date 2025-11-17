# chatbot_core.py
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import List, Dict, Protocol, Optional


try:
    from openai import OpenAI  # SDK nuevo
except Exception:  # pragma: no cover
    OpenAI = None


# ==========================
# Strategy
# ==========================

class StrategyChatbot(Protocol):
    @property
    def nombre_modelo(self) -> str:
        ...


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
# Interfaz base
# ==========================

class IChat(Protocol):
    def enviarmensaje(self, texto: str) -> List[Dict[str, str]]:
        ...

    @property
    def modelo(self) -> str:
        ...

    def set_estrategia(self, estrategia: StrategyChatbot) -> None:
        ...

    def set_contexto(self, contexto: str) -> None:
        ...

    @property
    def historial(self) -> List[Dict[str, str]]:
        ...


# ==========================
# Helpers de saneo (encoding seguro)
# ==========================

def _ascii_safe(text: str) -> str:
    """
    Convierte cualquier string a una versión ASCII segura para evitar errores
    tipo: 'ascii' codec can't encode character ...
    Esto SOLO se usa para logs/mensajes de error, no afecta la lógica.
    """
    if not isinstance(text, str):
        text = str(text)
    return text.encode("ascii", "ignore").decode("ascii", "ignore")


def _sanitize_messages(msgs: List[Dict[str, str]]) -> List[Dict[str, str]]:
    safe: List[Dict[str, str]] = []
    for m in msgs:
        role = _ascii_safe(m.get("role", "user"))
        content = _ascii_safe(m.get("content", ""))
        safe.append({"role": role, "content": content})
    return safe


# ==========================
# Chatbot concreto
# ==========================

class Chatbot(IChat):
    """
    Llama al modelo de OpenAI, mantiene historial y contexto.
    Las métricas y aspectos AOP se agregan alrededor de este componente.
    """

    def __init__(
        self,
        estrategia: StrategyChatbot,
        contexto_inicial: str = "",
        api_key: Optional[str] = None,
    ):
        if OpenAI is None:
            raise RuntimeError(
                "No se pudo importar 'openai'. Instala/actualiza el SDK con: pip install --upgrade openai"
            )

        api_key_final = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key_final:
            raise RuntimeError(
                "OPENAI_API_KEY no encontrado. "
                "Configúralo en tu entorno o pásalo a ControladorChatbot(api_key=...)."
            )

        self._client = OpenAI(api_key=api_key_final)
        self._estrategia = estrategia
        self._contexto = (
            contexto_inicial
            or "Eres un asistente integrado al sistema de gestion de ordenes."
        )
        self._historial: List[Dict[str, str]] = []

    # --- IChat ---

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

    # --- Operación principal ---

    def enviarmensaje(self, texto: str) -> List[Dict[str, str]]:
        user_msg = {"role": "user", "content": texto}

        mensajes: List[Dict[str, str]] = []
        if self._contexto:
            mensajes.append({"role": "system", "content": self._contexto})
        if self._historial:
            mensajes.extend(self._historial)
        mensajes.append(user_msg)

        # Versión segura para evitar problemas de encoding en entornos raros
        safe_messages = _sanitize_messages(mensajes)

        try:
            resp = self._client.chat.completions.create(
                model=self._estrategia.nombre_modelo,
                messages=safe_messages,
                temperature=0.2,
            )
            assistant_text = (resp.choices[0].message.content or "").strip()
        except Exception as ex:
            # NO mostramos el traceback feo; damos un mensaje entendible y ascii-safe.
            detail = _ascii_safe(str(ex))
            assistant_text = (
                "No se pudo obtener respuesta del modelo en este momento. "
                "Revisa tu OPENAI_API_KEY, la version de la libreria 'openai' y tu conexion a internet. "
                f"(Detalle tecnico: {detail})"
            )

        assistant_msg = {"role": "assistant", "content": assistant_text}

        # Guardamos historial (user + assistant)
        self._historial.append(user_msg)
        self._historial.append(assistant_msg)

        return [user_msg, assistant_msg]


# ==========================
# AOP: Aspectos alrededor del chatbot
# ==========================

class AspectoBase(IChat):
    """
    Aspecto base para Programación Orientada a Aspectos (AOP).

    Envuelve un IChat y permite ejecutar lógica transversal
    antes / después de enviarmensaje() sin tocar la lógica interna
    del Chatbot.
    """

    def __init__(self, base: IChat):
        self._base = base

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



"""
Aspecto de MÉTRICAS: calcula un conteo aproximado de tokens
del turno actual (prompt + respuesta).
"""
class AspectoTokens(AspectoBase):
    """
    Aspecto de MÉTRICAS: calcula un conteo aproximado de tokens
    del turno actual (prompt + respuesta).
    """

    def __init__(self, base: IChat):
        super().__init__(base)
        self.last_tokens_aprox: int = 0

    def _approx_tokens(self, text: str) -> int:
        # Estimación sencilla (~4 caracteres por token)
        return max(1, int(len(text) / 4))

    def enviarmensaje(self, texto: str) -> List[Dict[str, str]]:
        turno = self._base.enviarmensaje(texto)
        total_text = " ".join(
            m.get("content", "") for m in turno if isinstance(m, dict)
        )
        self.last_tokens_aprox = self._approx_tokens(total_text)
        return turno


class AspectoLatencia(AspectoBase):
    """
    Aspecto de MÉTRICAS: mide el tiempo (ms) que tarda
    en completarse la llamada a enviarmensaje().
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


"""
Aspecto de LATENCIA: mide el tiempo (ms) que tarda
en completarse la llamada a enviarmensaje().
"""

class AspectoSeguridad(AspectoBase):
    """
    Aspecto de SEGURIDAD: filtra contenido sensible antes de llamar
    al modelo (tarjetas, contraseñas, cuentas bancarias, etc.).

    Si detecta algo prohibido:
      - NO llama al modelo.
      - Devuelve una respuesta fija del asistente.
    """

    PALABRAS_BLOQUEADAS = [
        "tarjeta de credito",
        "numero de tarjeta",
        "cvv",
        "password",
        "contraseña",
        "contrasena",
        "cuenta bancaria",
        "base de datos",
        "CURP",
        "RFC",
        "numero de seguridad social",
        "SSN",
        "registro",
        "orden de compra",
        "bd",
        "banco",
        "clave",
        "pin",
    ]

    def enviarmensaje(self, texto: str) -> List[Dict[str, str]]:
        contenido = (texto or "").lower()

        if any(p in contenido for p in self.PALABRAS_BLOQUEADAS):
            user_msg = {"role": "user", "content": texto}
            assistant_msg = {
                "role": "assistant",
                "content": (
                    "Por seguridad no puedo procesar este tipo de informacion sensible. "
                    "Evita compartir datos como tarjetas, contraseñas o cuentas bancarias."
                ),
            }
            # Aquí se ve el comportamiento AOP: interceptamos el 'join point'
            # y cambiamos el flujo sin tocar la clase Chatbot.
            return [user_msg, assistant_msg]

        # Si pasa el filtro, delega al siguiente aspecto / chatbot real
        return self._base.enviarmensaje(texto)


# ==========================
# Métricas para la UI (ChatbotFAB, etc.)
# ==========================

@dataclass
class ChatMetrics:
    modelo: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float


# ==========================
# Controlador de alto nivel
# ==========================

class ControladorChatbot:
    """
    Punto de entrada para la UI:

    - Aplica Strategy (elección de modelo).
    - Aplica Aspectos AOP (Tokens, Latencia, Seguridad).
    - Expone historial y métricas del último turno.
    """

    def __init__(
        self,
        estrategia: StrategyChatbot | None = None,
        contexto_inicial: str = "",
        api_key: Optional[str] = None,
    ):
        # Estrategia por defecto si no se pasa una
        estrategia = estrategia or Modelo4oMini()

        # Cadena de ASPECTOS (AOP):
        #   Chatbot -> AspectoTokens -> AspectoLatencia -> AspectoSeguridad
        base = Chatbot(
            estrategia=estrategia,
            contexto_inicial=contexto_inicial,
            api_key=api_key,
        )
        asp_tokens = AspectoTokens(base)
        asp_lat = AspectoLatencia(asp_tokens)
        asp_seg = AspectoSeguridad(asp_lat)

        self._root: IChat = asp_seg
        self._tokens: AspectoTokens = asp_tokens
        self._latencia: AspectoLatencia = asp_lat

    # --- API usada por la UI ---

    def enviarmensaje(self, texto: str) -> List[Dict[str, str]]:
        return self._root.enviarmensaje(texto)

    def preguntar(self, texto: str) -> str:
        """
        Versión simple: devuelve solo el texto de la respuesta.
        """
        turno = self.enviarmensaje(texto)
        if isinstance(turno, list) and turno:
            last = turno[-1]
            if isinstance(last, dict):
                return last.get("content", "")
            return str(last)
        return ""

    def ask(self, texto: str) -> tuple[str, ChatMetrics]:
        """
        Versión pensada para el ChatbotFAB:
        devuelve (respuesta_texto, ChatMetrics).
        """
        # Ejecuta el turno completo (pasa por Seguridad, Latencia, Tokens, Chatbot)
        turno = self.enviarmensaje(texto)

        # Último mensaje debería ser del asistente
        respuesta = ""
        if isinstance(turno, list) and turno:
            last = turno[-1]
            if isinstance(last, dict):
                respuesta = last.get("content", "")
            else:
                respuesta = str(last)

        # Aproximación simple: usamos last_tokens_aprox como total;
        # si quieres, podrías partirlo en prompt/response.
        total_tokens = getattr(self._tokens, "last_tokens_aprox", 0)
        # Heurística sencilla: la mitad prompt, mitad respuesta
        prompt_tokens = total_tokens // 2
        completion_tokens = total_tokens - prompt_tokens

        metrics = ChatMetrics(
            modelo=self._root.modelo,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=float(getattr(self._latencia, "last_latency_ms", 0)),
        )
        return respuesta, metrics

    # --- Configuración / propiedades ---

    def cambiarmodelo(self, nueva: StrategyChatbot) -> None:
        self._root.set_estrategia(nueva)

    def actualizarContexto(self, contexto: str) -> None:
        self._root.set_contexto(contexto)

    @property
    def historial(self) -> List[Dict[str, str]]:
        return self._root.historial

    @property
    def metricas(self) -> Dict[str, int | str | float]:
        """
        Métricas en formato dict (por si quieres usarlas en otro lado).
        """
        total_tokens = getattr(self._tokens, "last_tokens_aprox", 0)
        prompt_tokens = total_tokens // 2
        completion_tokens = total_tokens - prompt_tokens

        return {
            "modelo": self._root.modelo,
            "lat_ms": getattr(self._latencia, "last_latency_ms", 0),
            "tokens_total": total_tokens,
            "tokens_prompt": prompt_tokens,
            "tokens_respuesta": completion_tokens,
        }