"""Draw the Followers and Profile Views badges in the same style as the other
profile badges. Run daily by .github/workflows/profile-assets.yml.

The text comes from scripts/badge-kit.json: pre-shaped outlines of the two
labels and the digits 0-9 (no font file is needed or shipped).
"""
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = json.load(open(os.path.join(ROOT, "scripts", "badge-kit.json"), encoding="utf-8"))
USER = os.environ.get("PROFILE_USER", "YasinKiani")
OUT = sys.argv[1] if len(sys.argv) > 1 else "dist"


def get(url, token=None):
    headers = {"User-Agent": "profile-badges"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30).read().decode()


def followers():
    data = json.loads(get(f"https://api.github.com/users/{USER}", os.environ.get("GITHUB_TOKEN")))
    return int(data["followers"])


def views():
    # the counter also has an invisible copy in the README, which counts real visits
    svg = get(f"https://komarev.com/ghpvc/?username={USER}&style=flat-square")
    numbers = re.findall(r">\s*([\d,]+)\s*<", svg)
    return int(numbers[-1].replace(",", ""))


def badge(key, value):
    k = KIT
    text = f"{value:,}"
    label = k["labels"][key]
    num_w = sum(k["digits"][ch]["adv"] for ch in text)
    iw = k["isz"] + 8
    w = int(k["px"] * 2 + iw + label["width"] + k["gap"] + num_w + 1)
    h = k["h"]
    base = h / 2 + k["size"] * 0.36
    parts = [f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="7" fill="{k["bg"]}" stroke="{k["stroke"]}"/>',
             f'<g transform="translate({k["px"]} {(h - k["isz"]) / 2})">{k["icons"][key]}</g>']
    x0 = k["px"] + iw
    for p in label["paths"]:
        parts.append(f'<path transform="translate({x0 + p["x"]:.2f} {base:.2f})" fill="{k["fg"]}" d="{p["d"]}"/>')
    x = x0 + label["width"] + k["gap"]
    for ch in text:
        g = k["digits"][ch]
        if g["d"]:
            parts.append(f'<path transform="translate({x:.2f} {base:.2f})" fill="{k["accent"]}" d="{g["d"]}"/>')
        x += g["adv"]
    title = f'{"Followers" if key == "followers" else "Profile Views"}: {text}'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" '
            f'aria-label="{title}"><title>{title}</title>\n' + "\n".join(parts) + "\n</svg>\n")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for key, fn in (("followers", followers), ("views", views)):
        try:
            value = fn()
        except Exception as exc:  # keep the workflow going if one source is down
            print(f"could not read {key}: {exc}")
            continue
        open(os.path.join(OUT, f"{key}.svg"), "w", encoding="utf-8").write(badge(key, value))
        print(f"{key}: {value}")
