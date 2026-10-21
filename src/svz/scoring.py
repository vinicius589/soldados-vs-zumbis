"""Pontuação, ranking local e loja de consumíveis, armazenados em SQLite."""
from __future__ import annotations

from contextlib import closing
import sqlite3
import unicodedata
from pathlib import Path

from .config import SAVE_PATH
from .content import REGION_ENEMIES, REGION_SUBBOSSES, REGION_BOSSES

SCORE_TABLE = {
    region: {
        key: (index + 1) * 10
        for index, key in enumerate(
            (*REGION_ENEMIES[region], *REGION_SUBBOSSES[region], *REGION_BOSSES[region])
        )
    }
    for region in REGION_ENEMIES
}

# Créditos são uma moeda de loja; não alteram a pontuação que define o ranking.
SHOP_ITEMS = {
    "medkit": {"column": "medkits", "price": 60, "label": "Kit médico"},
    "tactical_ammo": {
        "column": "tactical_ammo",
        "price": 80,
        "label": "Munição tática",
    },
}
CREDITS_PER_POINT_BLOCK = 10


def normalize_player_name(value: object) -> str:
    """Valida e normaliza o nome local exibido no ranking."""
    if not isinstance(value, str):
        raise ValueError("Digite um nome para jogar.")
    name = unicodedata.normalize("NFC", value).strip()
    if not name:
        raise ValueError("Digite um nome para jogar.")
    if len(name) > 20:
        raise ValueError("O nome pode ter no máximo 20 caracteres.")
    if not any(character.isalnum() for character in name):
        raise ValueError("O nome precisa ter pelo menos uma letra ou número.")
    if any(not character.isprintable() for character in name):
        raise ValueError("O nome contém caracteres inválidos.")
    return name


def points_for(region: str, key: str) -> int:
    # Criaturas auxiliares invocadas equivalem ao zumbi básico (10 pontos).
    return SCORE_TABLE.get(region, {}).get(key, 10)


class ScoreStore:
    """Histórico de partidas, pontuação acumulada, perfil local e inventário.

    A migração de banco é aditiva: os históricos anteriores são preservados e
    ganham o nome genérico "Jogador" até que o jogador comece partidas novas.
    """

    def __init__(self, campaign_path: str | Path | None = None):
        self.path = Path(campaign_path or SAVE_PATH).with_suffix(".pontuacoes.sqlite3")
        self.error = ""

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=3)
        try:
            db.execute(
                """CREATE TABLE IF NOT EXISTS scores (
                    id TEXT PRIMARY KEY,
                    date TEXT NOT NULL,
                    region TEXT NOT NULL,
                    difficulty TEXT NOT NULL,
                    wave INTEGER NOT NULL,
                    victory INTEGER NOT NULL,
                    points INTEGER NOT NULL CHECK(points >= 0),
                    player_name TEXT NOT NULL DEFAULT 'Jogador'
                )"""
            )
            columns = {row[1] for row in db.execute("PRAGMA table_info(scores)")}
            if "player_name" not in columns:
                db.execute(
                    "ALTER TABLE scores ADD COLUMN player_name TEXT NOT NULL DEFAULT 'Jogador'"
                )
            db.execute(
                """CREATE TABLE IF NOT EXISTS player_profiles (
                    player_name TEXT PRIMARY KEY COLLATE NOCASE,
                    credits INTEGER NOT NULL DEFAULT 0 CHECK(credits >= 0),
                    medkits INTEGER NOT NULL DEFAULT 0 CHECK(medkits >= 0),
                    tactical_ammo INTEGER NOT NULL DEFAULT 0 CHECK(tactical_ammo >= 0)
                )"""
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_scores_player ON scores(player_name)"
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_scores_recent ON scores(date DESC)"
            )
            db.commit()
            return db
        except Exception:
            db.close()
            raise

    @staticmethod
    def _ensure_profile(db: sqlite3.Connection, player_name: str) -> None:
        db.execute(
            "INSERT OR IGNORE INTO player_profiles(player_name) VALUES (?)",
            (player_name,),
        )

    def ensure_profile(self, player_name: str) -> bool:
        try:
            name = normalize_player_name(player_name)
            with closing(self.connect()) as db, db:
                self._ensure_profile(db, name)
            self.error = ""
            return True
        except (OSError, sqlite3.Error, ValueError):
            self.error = "Não foi possível salvar o perfil local. Verifique a pasta de dados do jogo."
            return False

    def profile(self, player_name: str) -> dict[str, int | str]:
        """Retorna saldo e inventário do perfil, criando-o se for a primeira visita."""
        try:
            name = normalize_player_name(player_name)
            with closing(self.connect()) as db, db:
                self._ensure_profile(db, name)
                row = db.execute(
                    "SELECT player_name, credits, medkits, tactical_ammo "
                    "FROM player_profiles WHERE player_name = ? COLLATE NOCASE",
                    (name,),
                ).fetchone()
            if row is None:
                raise sqlite3.DatabaseError("O perfil não foi criado.")
            self.error = ""
            return {
                "player_name": row[0],
                "credits": int(row[1]),
                "medkits": int(row[2]),
                "tactical_ammo": int(row[3]),
            }
        except (OSError, sqlite3.Error, ValueError):
            self.error = "Não foi possível ler o perfil local."
            return {"player_name": player_name, "credits": 0, "medkits": 0, "tactical_ammo": 0}

    def record(self, battle, player_name: str | None = None) -> bool:
        """Registra um resultado uma única vez e converte pontos em créditos.

        Repetir o autosave ou fechar o resultado não duplica nem a pontuação nem
        os créditos: o ID da partida é a chave idempotente da transação.
        """
        if not battle.finished:
            return False
        try:
            name = normalize_player_name(
                player_name or getattr(battle, "player_name", "Jogador")
            )
            points = int(battle.score)
            if points < 0:
                raise ValueError("Pontuação negativa não é válida.")
            earned = points // CREDITS_PER_POINT_BLOCK
            with closing(self.connect()) as db, db:
                self._ensure_profile(db, name)
                cursor = db.execute(
                    """INSERT OR IGNORE INTO scores
                       (id, date, region, difficulty, wave, victory, points, player_name)
                       VALUES (?, strftime('%Y-%m-%d %H:%M:%S','now','localtime'), ?, ?, ?, ?, ?, ?)""",
                    (
                        battle.match_id,
                        battle.region,
                        battle.difficulty,
                        battle.wave,
                        int(battle.victory),
                        points,
                        name,
                    ),
                )
                if cursor.rowcount == 1 and earned:
                    db.execute(
                        "UPDATE player_profiles SET credits = credits + ? "
                        "WHERE player_name = ? COLLATE NOCASE",
                        (earned, name),
                    )
            self.error = ""
            return True
        except (OSError, sqlite3.Error, ValueError, TypeError, AttributeError):
            self.error = "Não foi possível salvar a pontuação. Tente voltar ao mapa novamente."
            return False

    def page(self, index: int = 0):
        """Página do histórico recente, incluindo o jogador da partida."""
        try:
            with closing(self.connect()) as db:
                total = db.execute("SELECT count(*) FROM scores").fetchone()[0]
                rows = db.execute(
                    """SELECT date, player_name, region, difficulty, wave, victory, points
                       FROM scores ORDER BY rowid DESC LIMIT 10 OFFSET ?""",
                    (max(0, int(index)) * 10,),
                ).fetchall()
            self.error = ""
            return rows, int(total)
        except (OSError, sqlite3.Error, ValueError, TypeError):
            self.error = "Não foi possível ler o histórico de pontuações."
            return [], 0

    def leaderboard(self, index: int = 0):
        """Ranking local por pontos de vida inteira; saldo de loja não entra no total."""
        try:
            with closing(self.connect()) as db:
                total = db.execute(
                    "SELECT count(DISTINCT player_name COLLATE NOCASE) FROM scores"
                ).fetchone()[0]
                rows = db.execute(
                    """SELECT player_name, SUM(points) AS total_points,
                              COUNT(*) AS matches, SUM(victory) AS wins,
                              MAX(points) AS best_score
                       FROM scores
                       GROUP BY player_name COLLATE NOCASE
                       ORDER BY total_points DESC, best_score DESC, wins DESC,
                                player_name COLLATE NOCASE ASC
                       LIMIT 10 OFFSET ?""",
                    (max(0, int(index)) * 10,),
                ).fetchall()
            offset = max(0, int(index)) * 10
            ranking = [
                (offset + place, name, int(points), int(matches), int(wins), int(best))
                for place, (name, points, matches, wins, best) in enumerate(rows, 1)
            ]
            self.error = ""
            return ranking, int(total)
        except (OSError, sqlite3.Error, ValueError, TypeError):
            self.error = "Não foi possível montar o ranking local."
            return [], 0

    def buy(self, player_name: str, item: str) -> bool:
        """Compra uma unidade do item sem permitir saldo ou inventário negativos."""
        details = SHOP_ITEMS.get(item)
        if details is None:
            self.error = "Esse item não existe na loja."
            return False
        try:
            name = normalize_player_name(player_name)
            column = details["column"]
            price = int(details["price"])
            with closing(self.connect()) as db, db:
                self._ensure_profile(db, name)
                cursor = db.execute(
                    f"UPDATE player_profiles SET credits = credits - ?, {column} = {column} + 1 "
                    "WHERE player_name = ? COLLATE NOCASE AND credits >= ?",
                    (price, name, price),
                )
                if cursor.rowcount != 1:
                    self.error = f"Créditos insuficientes para comprar {details['label'].lower()}."
                    return False
            self.error = ""
            return True
        except (OSError, sqlite3.Error, ValueError):
            self.error = "Não foi possível concluir a compra."
            return False

    def consume(self, player_name: str, item: str) -> bool:
        """Consome um item apenas quando existe estoque no perfil."""
        details = SHOP_ITEMS.get(item)
        if details is None:
            self.error = "Esse item não existe no inventário."
            return False
        try:
            name = normalize_player_name(player_name)
            column = details["column"]
            with closing(self.connect()) as db, db:
                cursor = db.execute(
                    f"UPDATE player_profiles SET {column} = {column} - 1 "
                    "WHERE player_name = ? COLLATE NOCASE AND " + column + " > 0",
                    (name,),
                )
                if cursor.rowcount != 1:
                    self.error = f"Você não tem {details['label'].lower()} disponível."
                    return False
            self.error = ""
            return True
        except (OSError, sqlite3.Error, ValueError):
            self.error = "Não foi possível usar esse item."
            return False
