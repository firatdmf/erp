
import re

with open(r"c:\Users\enes3\erp\erp\notes\templates\notes\note_list.html", "r", encoding="utf-8") as f:
    content = f.read()

# Define start and end markers
start_marker = "/* Skeleton Loading */"
end_marker = "// ---- Grid loading indicator"

# Find start index
start_idx = content.rfind(start_marker) # Use rfind to get the LAST occurrence (the one in script tag)
if start_idx == -1:
    print("Start marker not found")
    exit(1)

# Find end index after start
end_idx = content.find(end_marker, start_idx)
if end_idx == -1:
    print("End marker not found")
    exit(1)

# Construct new content: keep everything before start, discard middle, keep everything after end
new_content = content[:start_idx] + content[end_idx:]

with open(r"c:\Users\enes3\erp\erp\notes\templates\notes\note_list.html", "w", encoding="utf-8") as f:
    f.write(new_content)

print("Successfully removed CSS block from script tag")
