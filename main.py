import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from starlette.responses import HTMLResponse

app = FastAPI()


class Token(BaseModel):
    token: str


@app.get("/")
async def root():
    return {"message": "Hello there!"}


@app.get("/oauth", response_class=HTMLResponse)
async def oauth():
    # HTML with JavaScript to catch token from the fragment
    return """
    <!DOCTYPE html>
    <html>
    <head><title>OAuth Callback</title></head>
    <body>
        <h2>Processing OAuth Token...</h2>
        <script>
            window.onload = function() {
                const hash = window.location.hash.substring(1); // remove leading #
                const params = new URLSearchParams(hash);
                const accessToken = params.get("access_token");

                if (accessToken) {
                    // Send token to backend
                    fetch("/save_token", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ token: accessToken })
                    });
                }
                window.open('','_self').close();
            }
        </script>
    </body>
    </html>
    """


@app.post("/save_token")
async def save_token(token: Token):
    print("Received token:", token.token)
    return {"status": "success", "received_token": token.token}


@app.get("/api/1/{token}/me")
async def itch_user(token: str):
    return {"message": f"{token}!"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
