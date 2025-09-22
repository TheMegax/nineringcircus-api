import random

import httpx
import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse
import urllib.parse

import dbmanager

from api_internal import (
    GachaPullRequest,
    GachaTokensRequest,
    validate_and_get_player,
    is_admin,
    trigger_event_internal,
    add_tokens_internal,
    gacha_pull_internal
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
    db_player = await validate_and_get_player(token)
    if db_player is None:
        return {"error": "Invalid token"}
    pull_result = await gacha_pull_internal(db_player, request.pulls)
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