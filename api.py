import random

import httpx
import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse
import urllib.parse

import dbmanager

from main import (
    lerp,
    GachaPullRequest,
    GachaTokensRequest,
    validate_and_get_player,
    is_admin,
    trigger_event_internal,
    add_tokens_internal,
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Hello there!"}


@app.get("/oauth/callback", response_class=HTMLResponse)
async def oauth():
    return """
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>OAuth Redirect</title></head>
    <body>
    <script>
      const params = new URLSearchParams(window.location.hash.substring(1));
      const token = params.get("access_token");
    
      if (token) {
        // Send token back to parent window
        console.log("Token received:", token);
        window.opener.postMessage({ token }, "*");
      } else {
        console.log("No token found");
        window.opener.postMessage({ error: "No token found" }, "*");
      }
    
      window.close();
    </script>
    </body>
    """


@app.post("/api/1/{token}/me")
async def itch_user(token: str):
    url = f"https://itch.io/api/1/{token}/me"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


@app.get("/api/1/image")
async def get_image(image_url: str):
    if not image_url.startswith("https://"):
        return {"error": "Invalid image URL. It must start with 'https://'."}
    async with httpx.AsyncClient() as client:
        parsed = urllib.parse.urlparse(image_url)
        image_url = "https://" + parsed.hostname + parsed.path + urllib.parse.quote("#" + parsed.fragment)
        print(image_url)
        response = await client.get(image_url)
        if response.status_code != 200:
            return {"error": "Failed to fetch image."}
        return HTMLResponse(content=response.content, media_type="image/png")


@app.post("/api/circus/{token}/player/trigger_event")
async def trigger_event(token: str, event_id: str):
    db_player = await validate_and_get_player(token)
    if db_player is None:
        return {"error": "Invalid token"}

    seen_events = db_player.seen_events.split(",") if db_player.seen_events else []
    if event_id in seen_events:
        return {"message": "Event already triggered", "player_id": db_player.player_id}
    if await trigger_event_internal(event_id, db_player) > 0:
        return {"message": "Event not found", "player_id": db_player.player_id}
    seen_events.append(event_id)
    db_player.seen_events = ",".join(seen_events)
    dbmanager.update_model(db_player)
    return {"message": "Event triggered successfully", "player_id": db_player.player_id}


@app.post("/api/circus/{token}/player/link_mc/{mc_username}")
async def link_mc_username(token: str, mc_username: str):
    if len(mc_username) > 16 or not mc_username.isalnum():
        return {"error": "Invalid Minecraft username. It must be alphanumeric and up to 16 characters long."}
    db_player = await validate_and_get_player(token)
    if db_player is None:
        return {"error": "Invalid token"}
    db_player.mc_username = mc_username
    dbmanager.update_model(db_player)
    return {"message": "Minecraft username linked successfully", "player_id": db_player.player_id}


@app.post("/api/circus/{token}/gacha/pull")
async def gacha_pull(token: str, request: GachaPullRequest):
    pulls = request.pulls
    up_rate = 0.5
    pity = 0
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
                    max_range: int
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
    return {"message": "Gacha pull completed", "results": pull_result}


@app.post("/api/circus/{token}/gacha/tokens")
async def add_tokens(token: str, request: GachaTokensRequest):
    amount = request.amount
    db_player = await validate_and_get_player(token)
    if db_player is None:
        return {"error": "Invalid token"}
    if not await is_admin(db_player):
        return {"error": "Unauthorized"}
    await add_tokens_internal(db_player, amount)
    return {"message": f"Added {amount} tokens", "player_id": db_player.player_id}


def start():
    print("BOT STARTED")
    dbmanager.initialize_database()
    uvicorn.run(app, host="0.0.0.0", port=4468)