import time
from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse
import httpx
import asyncio
from features import extract_features, Request as FeaturesRequest
from predict import load_onnx, predict_onnx
import sys

# =======================
# Config
# =======================
BACKEND_URL = sys.argv[1] if len(sys.argv) > 1 else "https://example.com/"  # your actual backend
BOT_THRESHOLD = 0.15  # probability threshold to block bots

# Load ML model once
print("Loading ML model...")
model = load_onnx("artifacts/model.onnx")

# Async HTTP client for forwarding requests
client = httpx.AsyncClient(timeout=None)

# FastAPI app
app = FastAPI(title="Bot-Blocking Reverse Proxy")

# =======================
# Helper
# =======================
def remove_trailing_questionmark(s: str) -> str:
    return s[:-1] if s.endswith("?") else s

async def is_bot(request: Request) -> bool:
    """
    Extract features and predict bot probability
    """
    features_req = FeaturesRequest()
    features_req.headers = {k.lower(): v for k, v in request.headers.items()}
    features_req.uri = remove_trailing_questionmark(str(request.url.path) + ("?" + str(request.url.query) if request.url.query else ""))
    features_req.method = request.method
    features_req.body = await request.body()

    client_ip = request.headers.get("x-real-ip") or request.client.host

    features = extract_features(time.time(), features_req, client_ip)
    print(features.as_np_array())
    bot_prob = predict_onnx(features.as_np_array(), model)

    print(f"[BotProb] {client_ip} -> {bot_prob:.2f}")
    return bot_prob > BOT_THRESHOLD

# =======================
# Reverse proxy endpoint
# =======================
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy(path: str, request: Request):
    # Check bot
    if await is_bot(request):
        return PlainTextResponse("Access denied", status_code=403)

    # Forward request to backend
    backend_url = f"{BACKEND_URL}/{path}"
    req_headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}

    try:
        # Apply incoming cookies to client cookie jar
        client.cookies.clear()
        for name, value in request.cookies.items():
            client.cookies.set(name, value)

        resp = await client.request(
            method=request.method,
            url=backend_url,
            headers=req_headers,
            content=await request.body(),
            params=request.query_params,
            timeout=None
        )

    except httpx.RequestError as e:
        return PlainTextResponse(f"Error forwarding request: {e}", status_code=502)

    excluded_headers = ["transfer-encoding", "connection"]
    headers = [(k, v) for k, v in resp.headers.items() if k.lower() not in excluded_headers]

    return Response(content=resp.content, status_code=resp.status_code, headers=dict(headers))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
