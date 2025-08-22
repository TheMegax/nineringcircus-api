import httpx
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Token(BaseModel):
    token: str


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


if __name__ == "__main__":
    print("BOT STARTED")
    uvicorn.run(app, host="0.0.0.0", port=8080)
