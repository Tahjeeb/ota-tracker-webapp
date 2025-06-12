from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from bs4 import BeautifulSoup
import requests, re, json, os
from datetime import datetime, timedelta
from pathlib import Path

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

WEBSITES = [
    "https://www.audiusa.com/newsroom/technology",
    "https://www.bmwusa.com/connecteddrive/software-update.html"
]

KEYWORDS = ['OTA', 'Over-the-Air', 'software update', 'firmware', 'version']
HISTORY_DIR = Path("ota_history")
HISTORY_DIR.mkdir(exist_ok=True)

# Remove files older than 4 months
def clean_old_history():
    cutoff = datetime.now() - timedelta(days=120)
    for file in HISTORY_DIR.glob("*.json"):
        timestamp_str = file.stem.split("_")[-1]
        try:
            file_time = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
            if file_time < cutoff:
                file.unlink()
        except:
            continue

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
    # Save to latest file
    with open("ota_updates.json", "w") as f:
        json.dump(result, f, indent=4)
    # Save with timestamp for history
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    with open(HISTORY_DIR / f"ota_updates_{timestamp}.json", "w") as f:
        json.dump(result, f, indent=4)
    clean_old_history()
    return JSONResponse(result)

@app.get("/api/ota-data")
async def get_saved_data():
    try:
        with open("ota_updates.json") as f:
            return JSONResponse(json.load(f))
    except FileNotFoundError:
        return JSONResponse({"error": "No data found."}, status_code=404)

@app.get("/api/history")
async def get_history():
    history = []
    for file in sorted(HISTORY_DIR.glob("*.json")):
        with open(file) as f:
            data = json.load(f)
            history.append({"file": file.name, "timestamp": data.get("timestamp"), "data": data.get("data")})
    return JSONResponse(history)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)

