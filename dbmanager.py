from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, create_engine, Session, Relationship, select


def formatlog(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("[{0}]    {1}".format(timestamp, msg))


# <<< MODELS >>> #
class Badge(SQLModel, table=True):
    badge_id: str = Field(primary_key=True)
    badge_name: str = Field(default="")
    uses: Optional[int] = Field(default=-1)
    cooldown_date: Optional[str] = Field(default="")
    player_id: Optional[int] = Field(default=None, foreign_key="dbplayer.player_id")
    player: Optional["DBPlayer"] = Relationship(
        back_populates="badges",
        sa_relationship_kwargs={"foreign_keys": "[Badge.player_id]"}
    )


class RPGItem(SQLModel, table=True):
    item_id: str = Field(primary_key=True)
    item_name: str = Field(default="")
    item_type: Optional[str] = Field(default="")  # "weapon", "accessory", "material"
    player_id: Optional[int] = Field(default=None, foreign_key="dbplayer.player_id")
    player: Optional["DBPlayer"] = Relationship(
        back_populates="rpg_items",
        sa_relationship_kwargs={"foreign_keys": "[RPGItem.player_id]"}
    )


class ValleyItem(SQLModel, table=True):
    item_id: str = Field(primary_key=True)
    item_name: str = Field(default="")
    item_uses: Optional[int] = Field(default=-1)
    cooldown_date: Optional[str] = Field(default="")
    player_id: Optional[int] = Field(default=None, foreign_key="dbplayer.player_id")
    player: Optional["DBPlayer"] = Relationship(
        back_populates="valley_items",
        sa_relationship_kwargs={"foreign_keys": "[ValleyItem.player_id]"}
    )


class Unit(SQLModel, table=True):
    unit_id: str = Field(primary_key=True)
    unit_name: str = Field(default="")
    unit_rarity: Optional[str] = Field(default="")  # "common", "uncommon", "rare", "legendary"
    player_id: Optional[int] = Field(default=None, foreign_key="dbplayer.player_id")
    player: Optional["DBPlayer"] = Relationship(
        back_populates="units",
        sa_relationship_kwargs={"foreign_keys": "[Unit.player_id]"}
    )


class DBPlayer(SQLModel, table=True):
    player_id: int = Field(primary_key=True)
    itch_id: Optional[int] = Field(default="")
    mc_username: Optional[str] = Field(default="")
    pity: Optional[int] = Field(default=0)
    up_rate: Optional[float] = Field(default=0.5)
    pull_tokens: Optional[int] = Field(default=0)
    total_pulls: Optional[int] = Field(default=0)
    seen_events: Optional[str] = Field(default="")  # Comma-separated event IDs
    candy_a: Optional[int] = Field(default=0)
    candy_b: Optional[int] = Field(default=0)
    candy_c: Optional[int] = Field(default=0)
    candy_d: Optional[int] = Field(default=0)
    candy_e: Optional[int] = Field(default=0)
    coins: Optional[int] = Field(default=0)
    tickets: Optional[int] = Field(default=0)
    rpg_items: list["RPGItem"] = Relationship(
        back_populates="player",
        sa_relationship_kwargs={"foreign_keys": "[RPGItem.player_id]"}
    )
    valley_items: list["ValleyItem"] = Relationship(
        back_populates="player",
        sa_relationship_kwargs={"foreign_keys": "[ValleyItem.player_id]"}
    )
    units: list["Unit"] = Relationship(
        back_populates="player",
        sa_relationship_kwargs={"foreign_keys": "[Unit.player_id]"}
    )
    badges: list["Badge"] = Relationship(
        back_populates="player",
        sa_relationship_kwargs={"foreign_keys": "[Badge.player_id]"}
    )
    equipped_badge: Optional[str] = Field(default=None, foreign_key="badge.badge_id")


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


# <<< BADGES >>> #
def create_badge(badge_name: str) -> Badge:
    badge = Badge(badge_name=badge_name)
    session.add(badge)
    session.commit()
    formatlog(f'New badge created with ID {badge.badge_id} and name "{badge_name}".')
    return badge


def get_badge_from_id(badge_int: int) -> Badge | None:
    badge = session.get(Badge, badge_int)
    if not badge:
        formatlog(f'Badge with ID "{badge_int}" not found in the database.')
    return badge


def get_badges_from_player(player_id: int) -> list[Badge]:
    statement = select(Badge).where(Badge.player_id == player_id)
    results = session.exec(statement)
    return list(results.all())


# <<< RPG Items >>>
def create_rpg_item(item_name: str) -> RPGItem:
    item = RPGItem(badge_name=item_name)
    session.add(item)
    session.commit()
    formatlog(f'New RPG Item created with ID {item.item_id} and name "{item_name}".')
    return item


def get_rpg_item_from_id(item_id: int) -> RPGItem | None:
    item = session.get(RPGItem, item_id)
    if not item:
        formatlog(f'RPG Item with ID "{item_id}" not found in the database.')
    return item


def get_rpg_items_from_player(player_id: int) -> list[RPGItem]:
    statement = select(RPGItem).where(RPGItem.player_id == player_id)
    results = session.exec(statement)
    return list(results.all())


# <<< Valley Items >>>
def create_valley_item(item_name: str) -> ValleyItem:
    item = ValleyItem(badge_name=item_name)
    session.add(item)
    session.commit()
    formatlog(f'New Valley Item created with name ID "{item_name}".')
    return item


def get_valley_item_from_id(item_id: int) -> ValleyItem | None:
    item = session.get(ValleyItem, item_id)
    if not item:
        formatlog(f'Valley Item with ID "{item_id}" not found in the database.')
    return item


def get_valley_items_from_player(player_id: int) -> list[ValleyItem]:
    statement = select(ValleyItem).where(ValleyItem.player_id == player_id)
    results = session.exec(statement)
    return list(results.all())


# <<< Units >>>
def create_unit(unit_name: str) -> Unit:
    unit = Unit(unit_name=unit_name)
    session.add(unit)
    session.commit()
    formatlog(f'New Unit created with ID {unit.unit_id} and name "{unit_name}".')
    return unit


def get_unit_from_id(unit_id: int) -> Unit | None:
    unit = session.get(Unit, unit_id)
    if not unit:
        formatlog(f'Unit with ID "{unit_id}" not found in the database.')
    return unit


def get_units_from_player(player_id: int) -> list[Unit]:
    statement = select(Unit).where(Unit.player_id == player_id)
    results = session.exec(statement)
    return list(results.all())


# <<< DATABASE >>> #
def initialize_database() -> None:
    SQLModel.metadata.create_all(engine)


def update_model(model) -> None:
    session.add(model)
    session.commit()
