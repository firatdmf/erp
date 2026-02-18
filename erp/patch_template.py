
import re

file_path = r"c:\Users\enes3\erp\erp\team\templates\team_task_detail.html"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern to find the split line (flexible whitespace)
# Matches: <span ...></span> {{ \n section.title }}
pattern = r'(<span class="status-dot"[^>]*></span>)\s*\{\{\s*\n\s*section\.title\s*\}\}'
replacement = r'\1 {{ section.title }}'

new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

if content == new_content:
    print("No changes made. Pattern not found.")
    # Try searching for the exact chars observed
    print("Dumping context around expected location:")
    idx = content.find("status-dot")
    if idx != -1:
        print(repr(content[idx:idx+200]))
else:
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("File patched successfully.")
