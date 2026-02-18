
with open(r"c:\Users\enes3\erp\erp\notes\templates\notes\note_list.html", "rb") as f:
    lines = f.readlines()
    # Print lines 1300 to 1335
    for i, line in enumerate(lines[1299:1335], 1300):
        print(f"{i}: {repr(line)}")
