import requests, tarfile, bz2, csv
from itertools import islice

'''
So that I can quickly print out the first 5 lines of each CSV. (Instead of downloading, etc.)
Run it the first time and get the list of links, use the corresponding download link for the specific dataset you want to look at.
For bigger files might take a moment to print but better than having to unpack...
Besides this it is also important to look at the readme for each dataset to learn more.
-> Also make sure to look at the answers which are seperate.
Generated for Claude to help analyze the data.
'''

ARTICLE_ID = "12841247" # From the end of the dataset URL.
API = f"https://api.figshare.com/v2/articles/{ARTICLE_ID}"

info = requests.get(API, timeout=30).json()
for f in info["files"]:
    print(f["id"], f["name"], f["size"], f["download_url"])

print("=====") # Seperate the actual lines from CSV...

URL = "https://ndownloader.figshare.com/files/24849308"
N_LINES = 5
MAX_CELL = 30 # Truncate long cells to this many characters.
TARGETS = None # Use as a set and list out each file if you want to target a specific one.
HEADERS = {"User-Agent": "Mozilla/5.0"}

# I believe in the end it just reaches out to an AWS S3.
def show(name, f):
    """Print the header plus the first N_ROWS rows as an aligned table."""
    lines = (l.decode("utf-8", errors="replace") for l in f)
    rows = list(islice(csv.reader(lines), N_LINES + 1))
    if not rows:
        print(f"\n=== {name} (Empty) ===")
        return

    rows = [
        [c if len(c) <= MAX_CELL else c[:MAX_CELL - 3] + "..." for c in row]
        for row in rows
    ]
    ncols = max(len(r) for r in rows)
    rows = [r + [""] * (ncols - len(r)) for r in rows]
    widths = [max(len(r[i]) for r in rows) for i in range(ncols)]

    print(f"\n=== {name} ===")
    for i, row in enumerate(rows):
        print(" | ".join(c.ljust(w) for c, w in zip(row, widths)))
        if i == 0:
            print("-+-".join("-" * w for w in widths))

def main():
    seen = set()

    with requests.get(URL, headers=HEADERS, stream=True,
                      allow_redirects=True, timeout=60) as r:
        r.raise_for_status()
        print("Status:", r.status_code)
        print("Content-Length:", r.headers.get("Content-Length"))
        print("Final File:", r.url.split("?")[0])  # Strips the signed query string.

        # BZ2File handles multi-stream bz2; tarfile then reads the plain tar stream.
        with bz2.BZ2File(r.raw) as bz, tarfile.open(fileobj=bz, mode="r|") as tar:
            for member in tar:
                if not member.isfile() or not member.name.endswith(".csv"):
                    continue

                base = member.name.rsplit("/", 1)[-1]
                if "decoy" in base:
                    continue
                if TARGETS and base not in TARGETS:
                    continue

                show(member.name, tar.extractfile(member))
                seen.add(base)

                if TARGETS and seen == TARGETS:
                    break  # Exiting the with-blocks closes the connection.

if __name__ == "__main__":
    main()