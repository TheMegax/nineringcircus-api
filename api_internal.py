import random

import yaml
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


async def gacha_pull_internal(player: dbmanager.DBPlayer, pulls: int) -> dict:
    up_rate = player.up_rate
    pity = player.pity
    soft_pity = 40
    hard_pity = 60
    pull_result = {}

    for i in range(pulls):
        prizes = {"material": 60, "candy": 15, "ticket": 15, "coin": 7, "unit": 3}
        unit_rarities = {"common": 40, "uncommon": 30, "rare": 20, "legendary": 10}

        got_unit = False
        if pity >= soft_pity:
            pity_lp = lerp(1, 0, (pity - soft_pity) / (hard_pity - soft_pity))
            for k, v in prizes.items():
                if k == "unit":
                    continue
                prizes[k] = v * pity_lp

        for j in range(random.randint(2, 3)):
            if up_rate > 0.5:
                rares_lp = lerp(1, 0, (up_rate - 0.5) / 0.5)
                for k, v in unit_rarities.items():
                    if k in ["rare", "legendary"]:
                        continue
                    unit_rarities[k] = v * rares_lp
            else:
                commons_lp = lerp(1, 0, (0.5 - up_rate) / 0.5)
                for k, v in unit_rarities.items():
                    if k in ["common", "uncommon"]:
                        continue
                    unit_rarities[k] = v * commons_lp

            prize = random.choices(list(prizes.keys()), weights=list(prizes.values()))[0]
            match prize:
                case "material":
                    material_name = f"material_{random.randint(1, 25)}"
                    pull_result.setdefault(material_name, 0)
                    pull_result[material_name] += 1
                case "candy":
                    candy_type = random.choice(["A", "B", "C", "D", "E"])
                    candy_name = f"candy_{candy_type}"
                    candy_amount = random.randint(3, 5)
                    pull_result.setdefault(candy_name, 0)
                    pull_result[candy_name] += candy_amount
                case "coin":
                    coin_amount = random.randint(1, 1)
                    pull_result.setdefault("coins", 0)
                    pull_result["coins"] += coin_amount
                case "ticket":
                    ticket_amount = random.randint(3, 15)
                    pull_result.setdefault("tickets", 0)
                    pull_result["tickets"] += ticket_amount
                case "unit":
                    got_unit = True
                    unit_rarity = random.choices(list(unit_rarities.keys()), weights=list(unit_rarities.values()))[0]
                    common_num = 10
                    uncommon_num = 6
                    rare_num = 5
                    legendary_num = 4
                    max_range: int = 1
                    match unit_rarity:
                        case "common":
                            max_range = common_num
                            up_rate += 0.03
                        case "uncommon":
                            max_range = uncommon_num
                            up_rate += 0.02
                        case "rare":
                            max_range = rare_num
                            up_rate -= 0.10
                        case "legendary":
                            max_range = legendary_num
                            up_rate -= 0.20
                        case _:
                            max_range = 1
                    up_rate = max(0.0, min(1.0, up_rate))
                    unit_name = f"{unit_rarity}_{random.randint(1, max_range)}"
                    pull_result.setdefault(unit_name, 0)
                    pull_result[unit_name] += 1
        if not got_unit:
            pity += 1
        else:
            pity = 0

    player.pull_tokens -= pulls
    player.total_pulls += pulls
    player.pity = pity
    player.up_rate = up_rate
    dbmanager.update_model(player)
    return pull_result
