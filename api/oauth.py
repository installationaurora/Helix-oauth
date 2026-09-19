import json
import os
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler


HELIX_CALLBACK_URL = os.environ.get(
    "HELIX_CALLBACK_URL",
    ""
).strip()

HELIX_CALLBACK_SECRET = os.environ.get(
    "HELIX_CALLBACK_SECRET",
    ""
).strip()


def html_response(message, success=True):
    title = (
        "Helix Verification Complete"
        if success
        else "Helix Verification Error"
    )

    color = "#57F287" if success else "#ED4245"

    body = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <title>{title}</title>

    <style>
        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #0f1115;
            color: white;
            font-family: Arial, Helvetica, sans-serif;
        }}

        .card {{
            width: min(500px, calc(100% - 40px));
            padding: 35px;
            border-radius: 16px;
            background: #181b21;
            border: 1px solid #2b2f38;
            text-align: center;
            box-shadow: 0 15px 50px rgba(0, 0, 0, 0.35);
        }}

        .icon {{
            width: 64px;
            height: 64px;
            margin: 0 auto 20px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            background: {color};
            color: #111;
            font-size: 32px;
            font-weight: bold;
        }}

        h1 {{
            margin: 0 0 12px;
            font-size: 25px;
        }}

        p {{
            color: #b5bac1;
            line-height: 1.6;
            margin: 0;
        }}
    </style>
</head>

<body>
    <div class="card">
        <div class="icon">
            {"✓" if success else "!"}
        </div>

        <h1>{title}</h1>

        <p>{message}</p>
    </div>
</body>
</html>
"""

    return body


def forward_to_helix(code, state):
    if not HELIX_CALLBACK_URL:
        raise RuntimeError(
            "HELIX_CALLBACK_URL is not configured in Vercel."
        )

    if not HELIX_CALLBACK_SECRET:
        raise RuntimeError(
            "HELIX_CALLBACK_SECRET is not configured in Vercel."
        )

    payload = json.dumps({
        "code": code,
        "state": state,
    }).encode("utf-8")

    request = urllib.request.Request(
        HELIX_CALLBACK_URL,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Helix-Secret": HELIX_CALLBACK_SECRET,
            "User-Agent": "Helix-OAuth-Callback/1.0",
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=15
        ) as response:

            raw = response.read().decode(
                "utf-8",
                errors="replace"
            )

            try:
                return response.status, json.loads(raw)

            except json.JSONDecodeError:
                return response.status, {
                    "ok": response.status < 400,
                    "raw": raw,
                }

    except urllib.error.HTTPError as exc:
        raw = exc.read().decode(
            "utf-8",
            errors="replace"
        )

        try:
            details = json.loads(raw)
        except json.JSONDecodeError:
            details = {
                "raw": raw
            }

        raise RuntimeError(
            f"Helix returned HTTP {exc.code}: {details}"
        ) from exc

    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Could not connect to Helix: {exc.reason}"
        ) from exc


class handler(BaseHTTPRequestHandler):

    def send_html(self, status_code, html):
        encoded = html.encode("utf-8")

        self.send_response(status_code)

        self.send_header(
            "Content-Type",
            "text/html; charset=utf-8"
        )

        self.send_header(
            "Content-Length",
            str(len(encoded))
        )

        self.send_header(
            "Cache-Control",
            "no-store"
        )

        self.end_headers()

        self.wfile.write(encoded)

    def do_GET(self):
        parsed = urllib.parse.urlparse(
            self.path
        )

        if parsed.path != "/api/oauth":
            self.send_html(
                404,
                html_response(
                    "This OAuth endpoint does not exist.",
                    success=False,
                ),
            )
            return

        query = urllib.parse.parse_qs(
            parsed.query
        )

        error = query.get(
            "error",
            [None]
        )[0]

        error_description = query.get(
            "error_description",
            [None]
        )[0]

        if error:
            description = (
                error_description
                or error
            )

            self.send_html(
                400,
                html_response(
                    "Roblox did not complete authorization."
                    f"<br><br>{description}",
                    success=False,
                ),
            )
            return

        code = query.get(
            "code",
            [None]
        )[0]

        state = query.get(
            "state",
            [None]
        )[0]

        if not code or not state:
            self.send_html(
                400,
                html_response(
                    "The Roblox authorization response "
                    "was missing the code or state.",
                    success=False,
                ),
            )
            return

        try:
            status, result = forward_to_helix(
                code,
                state
            )

            if status < 200 or status >= 300:
                raise RuntimeError(
                    f"Helix returned HTTP {status}: {result}"
                )

            if (
                isinstance(result, dict)
                and not result.get("ok", True)
            ):
                raise RuntimeError(
                    result.get(
                        "error",
                        "Helix rejected the verification."
                    )
                )

            self.send_html(
                200,
                html_response(
                    "Your Roblox account has been "
                    "linked successfully. "
                    "You can now return to Discord.",
                    success=True,
                ),
            )

        except Exception as exc:
            print(
                f"OAuth callback error: {exc}"
            )

            self.send_html(
                502,
                html_response(
                    "Helix could not complete the "
                    "verification. Check that the "
                    "Helix bot is online and reachable.",
                    success=False,
                ),
            )

    def do_POST(self):
        self.send_html(
            405,
            html_response(
                "This endpoint only accepts "
                "the Roblox OAuth GET callback.",
                success=False,
            ),
        )

    def log_message(self, format, *args):
        print(format % args)
