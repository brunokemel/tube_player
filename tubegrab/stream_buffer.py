"""Cache temporario dos streams que provavelmente serao tocados em seguida."""

import random
import threading
import time
from collections.abc import Callable

from .models import Track


Resolver = Callable[[str], dict]
Logger = Callable[[str], None]


class StreamBuffer:
    """Prepara metadados de streams sem baixar arquivos de audio."""

    MAX_AGE_SECONDS = 30 * 60

    def __init__(self):
        self.cache: dict[int, dict] = {}
        self.prefetching: set[int] = set()
        self.events: dict[int, threading.Event] = {}
        self.lock = threading.Lock()

    def clear(self):
        """Invalida o conteudo ao trocar de playlist."""
        with self.lock:
            self.cache.clear()
            self.prefetching.clear()
            self.events.clear()

    def cached_indices(self, excluded_index: int) -> list[int]:
        """Lista faixas ainda validas, usada especialmente pelo modo aleatorio."""
        now = time.monotonic()
        with self.lock:
            return [
                index
                for index, value in self.cache.items()
                if index != excluded_index
                and now - value["cached_at"] < self.MAX_AGE_SECONDS
            ]

    def get(
        self,
        index: int,
        item: Track,
        queue_generation: int,
        current_generation: Callable[[], int],
        resolver: Resolver,
        log: Logger,
    ) -> dict:
        """Entrega um stream em cache, aguarda a pre-carga ou resolve diretamente."""
        with self.lock:
            cached = self.cache.get(index)
            event = self.events.get(index)

        if self._is_valid(cached):
            log(f"Faixa {index + 1} pronta no buffer.")
            return cached["info"]

        if event is not None:
            event.wait(timeout=15)
            with self.lock:
                cached = self.cache.get(index)
            if self._is_valid(cached):
                log(f"Faixa {index + 1} recebida do buffer.")
                return cached["info"]

        info = resolver(item["url"])
        if queue_generation == current_generation():
            with self.lock:
                self.cache[index] = {"info": info, "cached_at": time.monotonic()}
        return info

    def prefetch(
        self,
        playlist: list[Track],
        current_index: int,
        shuffle: bool,
        queue_generation: int,
        current_generation: Callable[[], int],
        resolver: Resolver,
        log: Logger,
    ):
        """Inicia um worker sequencial para ate duas faixas provaveis."""
        if len(playlist) < 2:
            return
        if shuffle:
            available = [i for i in range(len(playlist)) if i != current_index]
            indices = random.sample(available, min(2, len(available)))
        else:
            indices = list(range(current_index + 1, min(current_index + 3, len(playlist))))

        threading.Thread(
            target=self._worker,
            args=(playlist, indices, queue_generation, current_generation, resolver, log),
            daemon=True,
        ).start()

    def _worker(
        self,
        playlist: list[Track],
        indices: list[int],
        queue_generation: int,
        current_generation: Callable[[], int],
        resolver: Resolver,
        log: Logger,
    ):
        """Resolve candidatos um de cada vez para limitar CPU e rede."""
        for index in indices:
            with self.lock:
                if self._is_valid(self.cache.get(index)) or index in self.prefetching:
                    continue
                event = threading.Event()
                self.prefetching.add(index)
                self.events[index] = event
            try:
                info = resolver(playlist[index]["url"])
                if queue_generation == current_generation():
                    with self.lock:
                        self.cache[index] = {
                            "info": info,
                            "cached_at": time.monotonic(),
                        }
                    log(f"Buffer pronto: faixa {index + 1}.")
            except Exception as exc:
                if queue_generation == current_generation():
                    log(f"Nao foi possivel preparar a faixa {index + 1}: {exc}")
            finally:
                with self.lock:
                    if self.events.get(index) is event:
                        self.prefetching.discard(index)
                        self.events.pop(index, None)
                    event.set()

    def _is_valid(self, cached: dict | None) -> bool:
        return bool(
            cached
            and time.monotonic() - cached["cached_at"] < self.MAX_AGE_SECONDS
        )
