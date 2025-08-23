import httpx
import uvicorn

import dbmanager
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse
import urllib.parse

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
    await trigger_event_internal(event_id, db_player)
    seen_events.append(event_id)
    db_player.seen_events = ",".join(seen_events)
    dbmanager.update_db_player(db_player)
    return {"message": "Event triggered successfully", "player_id": db_player.player_id}


@app.post("/api/circus/{token}/player/link_mc/{mc_username}")
async def link_mc_username(token: str, mc_username: str):
    if len(mc_username) > 16 or not mc_username.isalnum():
        return {"error": "Invalid Minecraft username. It must be alphanumeric and up to 16 characters long."}
    db_player = await validate_and_get_player(token)
    if db_player is None:
        return {"error": "Invalid token"}
    db_player.mc_username = mc_username
    dbmanager.update_db_player(db_player)
    return {"message": "Minecraft username linked successfully", "player_id": db_player.player_id}


async def validate_and_get_player(token: str) -> dbmanager.DBPlayer | None:
    itch_id = await get_itch_id_from_token(token)
    if itch_id is None:
        return None
    db_player = dbmanager.get_db_player_from_itch_id(itch_id)
    if not db_player:
        db_player = dbmanager.create_db_player(itch_id)
    return db_player


async def get_itch_id_from_token(token: str) -> int | None:
    response = await itch_user(token)
    if response.is_error:
        return None
    user_data = response.json()
    return user_data.get("id")


async def is_admin(player: dbmanager.DBPlayer) -> bool:
    itch_id = player.itch_id
    if itch_id is None:
        return False
    return itch_id in [7258425]


async def trigger_event_internal(event_id: str, player: dbmanager.DBPlayer):
    match event_id:
        case "test_event":
            print(f"Test event triggered for player {player.player_id}")
        case _:
            print(f"Unknown event ID: {event_id}")


if __name__ == "__main__":
    print("BOT STARTED")
    dbmanager.initialize_database()
    uvicorn.run(app, host="0.0.0.0", port=4468)
