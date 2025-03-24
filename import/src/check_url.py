from pathlib import Path
import json
import requests
import sys

def check_urls(file_path):
    data = json.loads(Path(file_path).read_text())
    for obj in data:
        url = obj.get("url")
        if url:
            try:
                response = requests.head(url, allow_redirects=True, timeout=5)
                if response.status_code >= 400:
                    print(f"Broken: {url} ({response.status_code})")
            except requests.RequestException:
                print(f"Broken: {url} (Request failed)")

check_urls(sys.argv[1])
