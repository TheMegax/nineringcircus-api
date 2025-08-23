from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, create_engine, Session, Relationship, select


def formatlog(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("[{0}]    {1}".format(timestamp, msg))


# <<< MODELS >>> #
class Badge(SQLModel, table=True):
    badge_id: int = Field(primary_key=True)
    badge_name: Optional[str] = Field(default="")
    uses: Optional[int] = Field(default=-1)
    cooldown_date: Optional[str] = Field(default="")
    player_id: Optional[int] = Field(default=None, foreign_key="dbplayer.player_id")
    player: Optional["DBPlayer"] = Relationship(back_populates="badges")


class Item(SQLModel, table=True):
    item_id: int = Field(primary_key=True)
    item_name: Optional[str] = Field(default="")
    item_type: Optional[str] = Field(default="")  # "unit", "weapon", "accessory", "mc_item"
    item_rarity: Optional[str] = Field(default="")  # "common", "uncommon", "rare", "legendary"
    item_uses: Optional[int] = Field(default=-1)
    player_id: Optional[int] = Field(default=None, foreign_key="dbplayer.player_id")
    player: Optional["DBPlayer"] = Relationship(back_populates="items")


class DBPlayer(SQLModel, table=True):
    player_id: int = Field(primary_key=True)
    itch_id: Optional[int] = Field(default="")
    mc_username: Optional[str] = Field(default="")
    pity: Optional[int] = Field(default=0)
    pull_tokens: Optional[int] = Field(default=0)
    total_pulls: Optional[int] = Field(default=0)
    seen_events: Optional[str] = Field(default="")  # Comma-separated event IDs
    candy_a: Optional[int] = Field(default=0)
    candy_b: Optional[int] = Field(default=0)
    candy_c: Optional[int] = Field(default=0)
    candy_d: Optional[int] = Field(default=0)
    coins: Optional[int] = Field(default=0)
    items: list["Item"] = Relationship(back_populates="player")
    badges: list["Badge"] = Relationship(back_populates="player")
    equipped_badge: Optional[int] = Field(default=None, foreign_key="badge.badge_id")


# <<< DATABASE CONNECTION >>> #
engine = create_engine("sqlite:///database.db")
session: Session = Session(engine)


# <<< PLAYERS >>> #
def create_db_player(itch_id: int) -> DBPlayer:
    db_player = DBPlayer(itch_id=itch_id)
    session.add(db_player)
    session.commit()
    formatlog(f'New player created with ID "{db_player.player_id}" and Itch ID "{itch_id}".')
    return db_player


def get_db_player_from_id(player_id: int) -> DBPlayer | None:
    db_player = session.get(DBPlayer, player_id)
    if not db_player:
        formatlog(f'Player with ID "{player_id}" not found in the database.')
    return db_player


def get_db_player_from_itch_id(itch_id: int) -> DBPlayer | None:
    statement = select(DBPlayer).where(DBPlayer.itch_id == itch_id)
    results = session.exec(statement)
    return results.first()


def get_db_player_from_mc_username(mc_username: str) -> DBPlayer | None:
    statement = select(DBPlayer).where(DBPlayer.mc_username == mc_username)
    results = session.exec(statement)
    return results.first()


# <<< DATABASE >>> #
def initialize_database() -> None:
    SQLModel.metadata.create_all(engine)


def update_db_player(db_player):
    session.add(db_player)
    session.commit()