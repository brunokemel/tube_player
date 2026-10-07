"""Algoritmo local de recomendacao da Radio TubeGrab.

O YouTube fornece candidatos de busca, mas toda a pontuacao acontece aqui. Assim o
comportamento e explicavel, funciona sem login e pode evoluir sem depender de um
algoritmo privado da plataforma.
"""

import json
import os
import re
from pathlib import Path


STOP_WORDS = {
    "a", "ao", "as", "com", "da", "das", "de", "do", "dos", "e", "em",
    "feat", "ft", "music", "official", "oficial", "the", "video", "with",
    "audio", "lyrics", "lyric", "clipe", "hd", "4k",
}


def _preference_path() -> Path:
    """Escolhe uma pasta de configuracao adequada ao sistema operacional."""
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "TubeGrab" / "radio_preferences.json"


def music_tokens(item: dict) -> set[str]:
    """Extrai palavras relevantes do titulo e do canal de uma musica."""
    text = f"{item.get('title', '')} {item.get('uploader', '')}".casefold()
    words = re.findall(r"[a-zA-Z0-9\u00c0-\u00ff]+", text)
    return {word for word in words if len(word) > 2 and word not in STOP_WORDS}


class RadioEngine:
    """Mantem preferencias locais e classifica candidatos da radio."""

    def __init__(self, preference_path: Path | None = None):
        self.preference_path = preference_path or _preference_path()
        self.preferences = {"likes": [], "dislikes": []}
        self._load()

    def _load(self):
        """Le preferencias existentes; arquivo corrompido nao impede o app de abrir."""
        try:
            data = json.loads(self.preference_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self.preferences["likes"] = list(data.get("likes", []))[-100:]
                self.preferences["dislikes"] = list(data.get("dislikes", []))[-100:]
        except (OSError, ValueError, TypeError):
            pass

    def _save(self):
        """Persiste somente metadados pequenos; nenhum audio ou credencial e salvo."""
        self.preference_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.preference_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(self.preferences, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.preference_path)

    def record_feedback(self, item: dict, liked: bool):
        """Registra a avaliacao, removendo uma avaliacao oposta anterior."""
        record = {
            "url": item.get("url", ""),
            "title": item.get("title", ""),
            "uploader": item.get("uploader", ""),
        }
        target = "likes" if liked else "dislikes"
        opposite = "dislikes" if liked else "likes"
        url = record["url"]
        self.preferences[opposite] = [
            saved for saved in self.preferences[opposite] if saved.get("url") != url
        ]
        self.preferences[target] = [
            saved for saved in self.preferences[target] if saved.get("url") != url
        ]
        self.preferences[target].append(record)
        self.preferences[target] = self.preferences[target][-100:]
        self._save()

    def reset_preferences(self):
        """Apaga curtidas e rejeicoes sem afetar outras configuracoes do app."""
        self.preferences = {"likes": [], "dislikes": []}
        self._save()

    def preference_counts(self) -> tuple[int, int]:
        return len(self.preferences["likes"]), len(self.preferences["dislikes"])

    def build_queries(self, seed: dict) -> list[str]:
        """Monta buscas curtas usando a faixa atual e gostos ja aprendidos."""
        title_tokens = sorted(music_tokens({"title": seed.get("title", "")}))[:4]
        uploader = seed.get("uploader", "").strip()
        base = " ".join(([uploader] if uploader else []) + title_tokens).strip()
        queries = [f"{base} music".strip(), f"{uploader} songs".strip()]

        likes = self.preferences["likes"][-5:]
        if likes:
            favorite = likes[-1]
            queries.append(
                f"{favorite.get('uploader', '')} {favorite.get('title', '')} music"
            )
        # Remove buscas vazias ou repetidas preservando a ordem.
        return list(dict.fromkeys(query for query in queries if len(query) > 5))

    def rank(
        self,
        seed: dict,
        candidates: list[dict],
        existing_urls: set[str],
        limit=6,
        diversity=50,
        allow_lives=False,
        allow_covers=True,
        allow_remixes=True,
    ):
        """Pontua semelhanca, preferencias e variedade de forma deterministica."""
        seed_tokens = music_tokens(seed)
        liked_tokens = set().union(
            *(music_tokens(item) for item in self.preferences["likes"][-30:])
        ) if self.preferences["likes"] else set()
        disliked_tokens = set().union(
            *(music_tokens(item) for item in self.preferences["dislikes"][-30:])
        ) if self.preferences["dislikes"] else set()
        seed_uploader = seed.get("uploader", "").casefold().strip()
        disliked_urls = {item.get("url") for item in self.preferences["dislikes"]}

        ranked = []
        seen = set(existing_urls)
        similarity_weight = max(1.0, (100 - int(diversity)) / 20)
        for candidate in candidates:
            url = candidate.get("url")
            if not url or url in seen or url in disliked_urls:
                continue
            try:
                duration = float(candidate.get("duration") or 0)
            except (TypeError, ValueError):
                duration = 0
            # Evita Shorts muito curtos e mixes/lives excessivamente longos.
            if duration and not 75 <= duration <= 900:
                continue
            title = candidate.get("title", "").casefold()
            if not allow_lives and any(word in title for word in (" live", "ao vivo", "concert")):
                continue
            if not allow_covers and "cover" in title:
                continue
            if not allow_remixes and any(word in title for word in ("remix", "mix ")):
                continue

            tokens = music_tokens(candidate)
            uploader = candidate.get("uploader", "").casefold().strip()
            score = len(tokens & seed_tokens) * similarity_weight
            score += len(tokens & liked_tokens) * 3
            score -= len(tokens & disliked_tokens) * 4
            if seed_uploader and uploader == seed_uploader:
                score += 7 * (1 - int(diversity) / 125)
            elif uploader:
                score += int(diversity) / 25
            # Um pequeno bonus para duracoes tipicas de musica.
            if 120 <= duration <= 420:
                score += 2
            ranked.append((score, candidate))
            seen.add(url)

        ranked.sort(key=lambda pair: pair[0], reverse=True)
        return [candidate for _score, candidate in ranked[:limit]]
