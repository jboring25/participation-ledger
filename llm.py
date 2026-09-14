"""One model call. Isolated so the graph does not care which model it uses.

Zero dependencies, standard library only, same pattern as the council skill.
"""
import json, os, socket, time, urllib.error, urllib.request

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
KEY_FILES = [os.path.expanduser("~/.config/gemini_key")]


def _key() -> str:
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"].strip()
    for p in KEY_FILES:
        if os.path.exists(p):
            return open(p).read().strip()
    raise RuntimeError("no gemini key found")


def ask_json(prompt: str) -> dict:
    """Send a prompt, insist on JSON back, return it as a dict."""
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{MODEL}:generateContent?key={_key()}")
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json",
                             "temperature": 0},
    }
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})

    # Transport-level retry. 429 and 5xx are the API being busy, not the
    # request being wrong, so they are worth repeating. A read timeout or a
    # dropped connection is the same kind of problem and has to be caught
    # separately, because socket.timeout is not an HTTPError and will
    # otherwise take down an entire unattended run over one slow response.
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                payload = json.load(r)
            break
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(2 ** attempt)
                continue
            raise
        except (socket.timeout, urllib.error.URLError) as e:
            if attempt < 3:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"model unreachable after 4 attempts: {e}")
    # Some models return reasoning parts alongside the answer, so take the
    # first part that actually carries text rather than assuming index 0.
    parts = payload["candidates"][0]["content"]["parts"]
    text = next(p["text"] for p in parts if "text" in p)
    return json.loads(text)
