import re
import sys
from pathlib import Path

DOCS_DIR = Path("docs")
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent

# Matches markdown links: [text](link)
LINK_PATTERN = re.compile(r"\[([^]]*)\]\(([^)]*)\)")


def check_link(file_path: Path, link: str) -> bool:
    """Verifies a single link. Returns True if valid, False otherwise."""
    # Ignore web URLs
    if link.startswith(("http://", "https://", "mailto:", "#")):
        return True

    # Strip anchor fragments
    clean_link = link.split("#")[0]
    if not clean_link:
        return True

    # If it is a file:/// scheme, parse it as absolute path
    if clean_link.startswith("file:///"):
        # Strip scheme and convert to path (keep leading slash)
        target_path = Path(clean_link[7:])
        # Verify it exists
        if not target_path.exists():
            print(f"[ERR] File link target does not exist: {link} in {file_path} (Resolved: {target_path})")
            return False
        return True

    # Resolve target path relative to source file directory
    target_path = (file_path.parent / clean_link).resolve()
    
    if not target_path.exists():
        print(f"[ERR] Broken relative link: '{link}' in {file_path} (Resolved to: {target_path})")
        return False

    return True


def main():
    """Scan all .md files in docs/ and verify local links."""
    print("Starting documentation link verification...")
    md_files = list(DOCS_DIR.glob("**/*.md")) + [Path("README.md"), Path("MASTER_PLAN.md")]
    broken_count = 0
    total_links = 0

    for file_path in md_files:
        if not file_path.is_file():
            continue
            
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        for match in LINK_PATTERN.finditer(content):
            total_links += 1
            link_target = match.group(2)
            
            # Skip empty targets
            if not link_target.strip():
                continue
                
            if not check_link(file_path, link_target):
                broken_count += 1

    print(f"Scanned {len(md_files)} files. Checked {total_links} links.")
    if broken_count > 0:
        print(f"[FAIL] Found {broken_count} broken links.")
        sys.exit(1)
    
    print("[PASS] All local documentation links resolved successfully.")
    sys.exit(0)


if __name__ == "__main__":
    main()
