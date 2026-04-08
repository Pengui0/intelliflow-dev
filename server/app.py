from app.api.main import app
import uvicorn

def start():
    uvicorn.run(app, host="0.0.0.0", port=7860)
