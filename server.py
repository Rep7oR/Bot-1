import threading
import requests
import time
import os
from flask import Flask

# import your bot file
import complete_main   # <-- THIS runs your bot automatically

app = Flask(__name__)

# keep-alive pinger
def keep_alive(url):
    def ping():
        while True:
            try:
                print("Pinging self...")
                requests.get(url)
            except Exception as e:
                print("Ping error:", e)
            time.sleep(240)
    threading.Thread(target=ping, daemon=True).start()

@app.route("/")
def home():
    return "Bot alive!", 200


if __name__ == "__main__":
    public_url = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:5000")

    keep_alive(public_url)

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
