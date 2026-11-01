'''
So that I can quickly print out the first 5 lines of each CSV. (Instead of downloading, etc.)
Run it the first time and get the list of links, use the corresponding download link for the specific dataset you want to look at.
For bigger files might take a moment to print but better than having to unpack...
Besides this it is also important to look at the readme for each dataset to learn more.
-> Also make sure to look at the answers which are seperate.
Generated with Claude to help analyze the data.
'''

import bz2
import csv
import tarfile
import requests
from datetime import datetime
from itertools import islice

# ========== Setting Variables ==========
ARTICLE_ID = "12841247" # ID from KiltHub link.
WANTED_FILE = "r4.2.tar.bz2"
TARGETS = None  # Set to None to show every CSV, use Dictionary format to specify files.
N_ROWS = 3 # Data rows to display per file, keep low number to not overdo.
SAMPLE_ROWS = 200 # Data rows used to infer column data types.
MAX_CELL = 30 # Truncate long cells to this many characters.
HEADERS = {"User-Agent": "Mozilla/5.0"}

# CERT timestamp format with some fallbacks.
DT_FORMATS = ["%m/%d/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y"]

# Commented out because it is not required.
# Prints our all the different datasets, their download URLs and IDs.
# If you want to use, make sure to uncomment the call in main() as well.
'''
def list_files():
    api = f"https://api.figshare.com/v2/articles/{ARTICLE_ID}"
    resp = requests.get(api, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    files = resp.json()["files"]

    print("===== FILES IN DATASET =====")
    rows = [["ID", "Name", "Size (GB)", "Download URL"]]
    for f in files:
        rows.append([str(f["id"]), f["name"], f"{f['size'] / 1e9:.2f}", f["download_url"]])
    print_table(rows)
'''

def returnFiles():
    api = f"https://api.figshare.com/v2/articles/{ARTICLE_ID}"
    resp = requests.get(api, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    files = resp.json()["files"]

    return files

# Get file we specified in WANTED_FILE variable. (Looks if it exists.)
def pick_file(files):
    for f in files:
        if f["name"] == WANTED_FILE:
            return f
    names = ", ".join(f["name"] for f in files)
    raise SystemExit(f"{WANTED_FILE} not found. Available: {names}")

# ========== TYPE CHECKERS: Used to check what type a column would be... helper functions. ==========
def is_int(v):
    try:
        int(v)
        return True
    except ValueError:
        return False

def is_float(v):
    try:
        float(v)
        return True
    except ValueError:
        return False

def is_bool(v):
    return v.lower() in ("true", "false")

def is_datetime(v):
    for fmt in DT_FORMATS:
        try:
            datetime.strptime(v, fmt)
            return True
        except ValueError:
            pass
    return False

def infer_type(values):
    # Return the narrowest Python type that fits every non empty value.
    vals = [v for v in values if v != ""]
    if not vals:
        return "empty"
    for name, check in (("int", is_int), ("float", is_float),
                        ("bool", is_bool), ("datetime", is_datetime)):
        if all(check(v) for v in vals):
            return name
    return "str" # If we cannot decide -> String.

# ========== PRINT TABLE/FORMATTING FUNCTIONS (To read the output easily.) ==========
def trunc(c):
    return c if len(c) <= MAX_CELL else c[:MAX_CELL - 3] + "..."

def print_table(rows):
    ncols = max(len(r) for r in rows)
    rows = [r + [""] * (ncols - len(r)) for r in rows]
    widths = [max(len(r[i]) for r in rows) for i in range(ncols)]
    for i, row in enumerate(rows):
        print(" | ".join(c.ljust(w) for c, w in zip(row, widths)))
        if i == 0:
            print("-+-".join("-" * w for w in widths))

def show(name, f):
    # Print preview table first, inferred schema second.
    lines = (l.decode("utf-8", errors="replace") for l in f)
    rows = list(islice(csv.reader(lines), SAMPLE_ROWS + 1))
    if not rows:
        print(f"\n=== {name} (Empty) ===")
        return

    header, data = rows[0], rows[1:]
    ncols = len(header)
    data = [r + [""] * (ncols - len(r)) for r in data]  # pad short rows

    print(f"\n=== {name} ===")
    print_table([[trunc(c) for c in r] for r in [header] + data[:N_ROWS]])

    schema = [["Column", "Inferred Type", "Empty Cells", "Example"]]
    for i, col in enumerate(header):
        values = [r[i] for r in data]
        example = next((v for v in values if v != ""), "")
        schema.append([col, infer_type(values),
                       str(sum(v == "" for v in values)), trunc(example)])

    print(f"\nSchema (Inferred From Rirst {len(data)} Rows):")
    print_table(schema)

"""
1. List all files in KiltHub (optional).
2. Get specific file ID/name information.
3. Make GET request using URL.
4. Parse through files being read, print our information for target files.
"""
def main():
    #list_files() # <- Uncomment this line if you want to use list_files() function.

    files = returnFiles()
    chosen = pick_file(files)
    print(f"\nUsing File ID {chosen['id']}: {chosen['name']}")

    seen = set()
    with requests.get(chosen["download_url"], headers=HEADERS, stream=True, allow_redirects=True, timeout=60) as r:
        r.raise_for_status()
        print("Status:", r.status_code)
        print("Content-Length:", r.headers.get("Content-Length"))
        print("Final File:", r.url.split("?")[0])  # Strips the signed query string.

        # Unpack and recoginize seperate files we are reading.
        with bz2.BZ2File(r.raw) as bz, tarfile.open(fileobj=bz, mode="r|") as tar:
            for member in tar: # For each file in the .tar.
                if not member.isfile() or not member.name.endswith(".csv"): # Skip non CSV files.
                    continue

                # Clean the filenames -> r5.2/logon.csv -> logon.csv. (For target variable setting.
                base = member.name.rsplit("/", 1)[-1]
                if "decoy" in base:
                    continue
                if TARGETS and base not in TARGETS:
                    continue

                # Print all target files, when done, exit.
                show(member.name, tar.extractfile(member))
                seen.add(base)

                if TARGETS and seen == TARGETS:
                    break  # Exiting the with blocks closes the connection.

if __name__ == "__main__":
    main()