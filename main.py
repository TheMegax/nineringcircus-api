import yaml
import api
import dbmanager
from pydantic import BaseModel


# Linear interpolation function
def lerp(a, b, weight):
    """
    Returns the linear interpolation between a and b with the given weight (0 to 1).
    """
    return a + (b - a) * weight


class GachaPullRequest(BaseModel):
    pulls: int
    chosen_unit: str = ""


class GachaTokensRequest(BaseModel):
    amount: int


async def validate_and_get_player(token: str) -> dbmanager.DBPlayer | None:
    itch_id = await get_itch_id_from_token(token)
    if itch_id is None:
        return None
    db_player = dbmanager.get_db_player_from_itch_id(itch_id)
    if not db_player:
        db_player = dbmanager.create_db_player(itch_id)
    return db_player


async def get_itch_id_from_token(token: str) -> int | None:
    # This function will call the API endpoint defined in api.py
    from api import itch_user
    response = await itch_user(token)
    if response.get("error"):
        return None
    return response.get("user").get("id")


async def is_admin(player: dbmanager.DBPlayer) -> bool:
    itch_id = player.itch_id
    if itch_id is None:
        return False
    return itch_id in [7258425]


async def trigger_event_internal(event_id: str, player: dbmanager.DBPlayer) -> int:
    with open("objects.yaml") as f:
        objects = yaml.safe_load(f)
        events: dict = objects['events']
        if not events.__contains__(event_id):
            print(f"Unknown event ID: {event_id}")
            return 1

        print(f"Event {event_id} triggered for player {player.mc_username}")
        return 0


async def add_tokens_internal(player: dbmanager.DBPlayer, amount: int) -> None:
    if amount <= 0:
        return
    player.pull_tokens = (player.pull_tokens or 0) + amount
    dbmanager.update_model(player)


if __name__ == "__main__":
    api.start()
