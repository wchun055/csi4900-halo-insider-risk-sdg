import bz2
import csv
import sys
import tarfile
from contextlib import redirect_stdout
from datetime import datetime
from itertools import islice

"""
I am finding  that sometimes print_data.py has 403 issues with figshare.
This is a local version. Download the .tar, add the local path to the settings.
It will produce same results as print_data.py, unpacks the files but does not write it to disk.
Also have an option to make the result a .txt as I did not want to keep running this over and over.
"""

# ========== Setting Variables ==========
LOCAL_PATH = r"r4.2.tar.bz2"  # Path to downloaded archive.
TARGETS = None   # Set to None to show every CSV, use Dictionary format to specify files.
N_ROWS = 3          # Data rows to display per file, keep low number to not overdo.
SAMPLE_ROWS = 100   # Data rows used to infer column data types.
MAX_CELL = 30       # Truncate long cells to this many characters.
OUTPUT_TXT = "local_print_data_results.txt"   # "text.txt" for a .txt output, None for only in console.

# CERT timestamp format with some fallbacks.
DT_FORMATS = ["%m/%d/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y"]

# Some fields (e.g. email/http content) can exceed csv's default size limit.
csv.field_size_limit(10_000_000)


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
    return "str"  # If we cannot decide -> String.

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
        print(f"\n=== {name} (empty) ===")
        return

    header, data = rows[0], rows[1:]
    ncols = len(header)
    data = [r + [""] * (ncols - len(r)) for r in data]  # Pad short rows.

    print(f"\n=== {name} ===")
    print_table([[trunc(c) for c in r] for r in [header] + data[:N_ROWS]])

    schema = [["Column", "Inferred Type", "Empty Cells", "Example"]]
    for i, col in enumerate(header):
        values = [r[i] for r in data]
        example = next((v for v in values if v != ""), "")
        schema.append([col, infer_type(values),
                       str(sum(v == "" for v in values)), trunc(example)])

    print(f"\nSchema (Inferred From First {len(data)} Rows):")
    print_table(schema)

def run():
    seen = set()

    try:
        # BZ2File handles multi-stream bz2, tarfile reads the plain tar ("r|").
        with bz2.BZ2File(LOCAL_PATH) as bz, tarfile.open(fileobj=bz, mode="r|") as tar:
            for member in tar:
                if not member.isfile() or not member.name.endswith(".csv"): # Skip non CSV files.
                    continue
 
                base = member.name.rsplit("/", 1)[-1] # Clean the filenames -> r5.2/logon.csv -> logon.csv. (For target variable setting.)
                if "decoy" in base:
                    continue
                if TARGETS and base not in TARGETS:
                    continue

                # Print all target files, when done, exit.
                show(member.name, tar.extractfile(member))
                seen.add(base)
 
                if TARGETS and seen == TARGETS:
                    break # Exiting the with blocks closes the connection.
    except EOFError:
        print("\nArchive ended early (partial file). Files above were read fine.")
 
class Tee:
    # Send everything printed to both the console + .txt file.
    def __init__(self, *streams):
        self.streams = streams
 
    def write(self, text):
        for s in self.streams:
            s.write(text)
 
    def flush(self):
        for s in self.streams:
            s.flush()
 
 
def main():
    if not OUTPUT_TXT:
        run()
        return
    with open(OUTPUT_TXT, "w", encoding="utf-8") as out:
        with redirect_stdout(Tee(sys.stdout, out)):
            run()
    print(f"\nOutput also saved to {OUTPUT_TXT}.")
 
if __name__ == "__main__":
    main()
