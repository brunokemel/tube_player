"""Integracao entre o algoritmo de radio, a fila e os controles da interface."""

import threading
from tkinter import messagebox

from .config import ACCENT, MUTED, OK, WARN
from .downloader import search_music_candidates


class RadioController:
    """Mixin com o fluxo da Radio TubeGrab; a janela fornece UI e player."""

    def toggle_radio(self):
        self.radio_enabled = not self.radio_enabled
        if self.radio_enabled:
            messagebox.showinfo(
                "Rádio TubeGrab em desenvolvimento",
                "A Rádio TubeGrab ainda está em desenvolvimento.\n\n"
                "As recomendações usam um algoritmo local que aprende com suas "
                "curtidas e faixas puladas, mas ainda podem não ter a mesma precisão "
                "de grandes aplicativos do mercado.\n\n"
                "Seu feedback durante o uso ajudará a melhorar as próximas escolhas.\n\n"
                "Envie sugestões para: br.kemel@gmail.com",
            )
        self.radio_btn.configure(
            text="Radio ligada" if self.radio_enabled else "Radio TubeGrab",
            fg_color=ACCENT if self.radio_enabled else "#242936",
        )
        state = "ligada" if self.radio_enabled else "desligada"
        self.set_status(f"Radio TubeGrab {state}.", OK if self.radio_enabled else MUTED)
        if self.radio_enabled:
            self._ensure_radio_queue(force=True)

    def rate_current_track(self, liked: bool):
        """Salva a preferencia local; rejeitar tambem avanca a reproducao."""
        if not 0 <= self.playlist_index < len(self.playlist):
            return
        item = self.playlist[self.playlist_index]
        try:
            self.radio.record_feedback(item, liked)
        except OSError as exc:
            self.log(f"Nao foi possivel salvar a preferencia: {exc}")
            return

        if liked:
            self.set_status("Curtida salva. A radio vai aprender com essa escolha.", OK)
            self.like_btn.configure(fg_color="#26704d")
            self.after(900, lambda: self.like_btn.configure(fg_color="#242936"))
            self._ensure_radio_queue(force=True)
            return

        self.set_status("Faixa rejeitada e removida das proximas sugestoes.", WARN)
        next_index = self._next_track_index()
        if next_index is not None:
            self.playlist_index = next_index
            self._start_current_track()
        else:
            self.radio_skip_pending = True
            if self.player is not None:
                self.player.stop()
            self._ensure_radio_queue(force=True)

    def _ensure_radio_queue(self, force: bool = False):
        """Solicita recomendacoes antes de a fila chegar ao final."""
        if not self.radio_enabled or not self.playlist:
            return
        if self.radio_loading_generation == self.queue_generation:
            return
        remaining = len(self.playlist) - self.playlist_index - 1
        if not force and remaining > 3:
            return

        seed = self.playlist[self.playlist_index]
        self.radio_loading = True
        queue_generation = self.queue_generation
        self.radio_loading_generation = queue_generation
        self.set_status("Radio TubeGrab procurando as proximas musicas...", WARN)
        threading.Thread(
            target=self._radio_recommendation_worker,
            args=(seed.copy(), queue_generation),
            daemon=True,
        ).start()

    def _radio_recommendation_worker(self, seed: dict, queue_generation: int):
        """Busca e classifica candidatos sem bloquear a interface."""
        try:
            queries = self.radio.build_queries(seed)
            candidates = search_music_candidates(queries)
            existing_urls = {item.get("url") for item in self.playlist}
            recommendations = self.radio.rank(seed, candidates, existing_urls, limit=6)
            self.after(
                0,
                lambda: self._apply_radio_recommendations(
                    recommendations,
                    queue_generation,
                ),
            )
        except Exception as exc:
            self.after(0, lambda: self._radio_failed(str(exc), queue_generation))

    def _radio_failed(self, error: str, queue_generation: int):
        """Finaliza uma busca com erro somente se ela ainda pertencer a fila atual."""
        if self.radio_loading_generation == queue_generation:
            self.radio_loading = False
            self.radio_loading_generation = None
        if queue_generation == self.queue_generation:
            self.log(f"Radio indisponivel: {error}")
            self.set_status("Nao foi possivel buscar recomendacoes agora.", ACCENT)

    def _apply_radio_recommendations(self, recommendations, queue_generation: int):
        """Acrescenta sugestoes validas e atualiza a fila visivel."""
        if self.radio_loading_generation == queue_generation:
            self.radio_loading = False
            self.radio_loading_generation = None
        if queue_generation != self.queue_generation or not self.radio_enabled:
            return
        if not recommendations:
            self.set_status("A radio nao encontrou novas sugestoes para esta faixa.", WARN)
            return

        existing_urls = {item.get("url") for item in self.playlist}
        additions = [item for item in recommendations if item.get("url") not in existing_urls]
        if not additions:
            self.set_status("A radio nao encontrou novas sugestoes para esta faixa.", WARN)
            return
        self.playlist.extend(additions)
        self._populate_playlist()
        self.log(f"Radio adicionou {len(additions)} nova(s) faixa(s) a fila.")
        self.set_status("Radio TubeGrab pronta com novas sugestoes.", OK)
        self._schedule_stream_prefetch(self.playlist_index)
        if self.radio_skip_pending:
            self.radio_skip_pending = False
            self.playlist_index += 1
            self._start_current_track()
