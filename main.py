from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from bs4 import BeautifulSoup
import requests, re, json, os
from datetime import datetime
from pathlib import Path

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

WEBSITES = [
    "https://www.audiusa.com/newsroom/technology",
    "https://www.bmwusa.com/connecteddrive/software-update.html"
]

KEYWORDS = ['OTA', 'Over-the-Air', 'software update', 'firmware', 'version']

def extract_ota_info(text):
    pattern = r"(OTA|over[- ]the[- ]air|software update|firmware)\\s.*?\\d{4}|\\d+\\.\\d+"
    matches = re.findall(pattern, text, re.IGNORECASE)
    return list(set(matches))

def scrape_site(url):
    try:
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        texts = soup.get_text()
        lines = texts.split('\n')
        found = []
        for line in lines:
            for keyword in KEYWORDS:
                if keyword.lower() in line.lower():
                    extracted = extract_ota_info(line)
                    if extracted:
                        found.append({"line": line.strip(), "matches": extracted})
        return found
    except Exception as e:
        return [{"line": f"Error: {e}", "matches": []}]

@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = Path("static/index.html")
    return HTMLResponse(content=html_path.read_text(), status_code=200)

@app.get("/api/scrape")
async def scrape():
    updates = {}
    for site in WEBSITES:
        updates[site] = scrape_site(site)
    result = {
        "timestamp": datetime.now().isoformat(),
        "data": updates
    }
    with open("ota_updates.json", "w") as f:
        json.dump(result, f, indent=4)
    return JSONResponse(result)

@app.get("/api/ota-data")
async def get_saved_data():
    try:
        with open("ota_updates.json") as f:
            return JSONResponse(json.load(f))
    except FileNotFoundError:
        return JSONResponse({"error": "No data found."}, status_code=404)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
