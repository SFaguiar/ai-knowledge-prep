"""Testes do serviço de transcrição (interface fixada; implementação na Etapa 6)."""

from __future__ import annotations

import pytest

from app.backends.transcription.faster_whisper_backend import FasterWhisperBackend
from app.backends.transcription.whisper_cpp_backend import WhisperCppBackend
from app.services import transcription_service


def test_backend_availability_is_bool() -> None:
    assert isinstance(FasterWhisperBackend().is_available(), bool)
    assert isinstance(WhisperCppBackend().is_available(), bool)


def test_transcribe_fails_clearly_before_etapa6() -> None:
    # Sem backend: RuntimeError com mensagem amigável.
    # Com backend instalado: NotImplementedError até a Etapa 6.
    with pytest.raises((RuntimeError, NotImplementedError)):
        transcription_service.transcribe_file("aula.mp4")
