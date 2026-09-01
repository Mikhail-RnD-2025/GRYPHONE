#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — script 54: MERGE REQUIREMENTS
#  ------------------------------------------------------------
#  What this script does:
#    1. Extracts pip dependencies from INSTALL_EXCEL_IMPORT.md
#    2. Merges them with existing requirements.txt
#    3. Updates INSTALL_EXCEL_IMPORT.md to reference requirements.txt
#    4. Removes duplicate entries
#
#  RUN:   bash update_scripts/54_merge_requirements.sh
# ============================================================
set -euo pipefail

# Determine script location and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/../main.py" ]; then
    PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
else
    PROJECT_DIR="$SCRIPT_DIR"
fi

echo "📁 Project root: $PROJECT_DIR"
cd "$PROJECT_DIR"

# ============================================================
# Python detection
# ============================================================
_detect_python() {
    local cmd
    for cmd in python python3 py; do
        if command -v "$cmd" >/dev/null 2>&1; then
            if "$cmd" --version >/dev/null 2>&1; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    return 1
}

PYTHON_CMD="$(_detect_python || true)"
if [ -z "$PYTHON_CMD" ]; then
    echo "❌ ERROR: no Python interpreter found."
    exit 1
fi

read -ra PYCMD <<< "$PYTHON_CMD"
echo "✅ Python: ${PYCMD[*]}"

# ============================================================
# Step 1: Analyze INSTALL_EXCEL_IMPORT.md
# ============================================================
echo ""
echo "🔧 Analyzing INSTALL_EXCEL_IMPORT.md..."

if [ ! -f "INSTALL_EXCEL_IMPORT.md" ]; then
    echo "  ⚠️  INSTALL_EXCEL_IMPORT.md not found"
    exit 1
fi

echo "  ✔ File found: INSTALL_EXCEL_IMPORT.md"

# ============================================================
# Step 2: Extract dependencies and merge with requirements.txt
# ============================================================
echo ""
echo "🔧 Merging dependencies..."

"${PYCMD[@]}" << 'PYEOF'
from pathlib import Path
import re

# Read INSTALL_EXCEL_IMPORT.md
md_file = Path("INSTALL_EXCEL_IMPORT.md")
md_content = md_file.read_text(encoding="utf-8")

# Read existing requirements.txt if it exists
req_file = Path("requirements.txt")
existing_requirements = set()
if req_file.exists():
    existing_content = req_file.read_text(encoding="utf-8")
    for line in existing_content.split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            # Extract package name (before any version specifier)
            pkg_name = re.split(r'[<>=!~\[]', line)[0].strip().lower()
            if pkg_name:
                existing_requirements.add(pkg_name)
    print(f"  ℹ️  Existing requirements: {len(existing_requirements)} packages")
else:
    print("  ℹ️  requirements.txt not found — creating new one")

# Extract pip install commands from markdown
# Patterns: pip install pandas openpyxl, pip install -r requirements.txt, etc.
pip_install_patterns = [
    r'pip install\s+([^\n]+)',
    r'pip3 install\s+([^\n]+)',
    r'python -m pip install\s+([^\n]+)',
]

extracted_packages = set()
for pattern in pip_install_patterns:
    matches = re.findall(pattern, md_content)
    for match in matches:
        # Skip if it's installing from requirements.txt
        if 'requirements.txt' in match:
            continue
        # Split by spaces and clean up
        packages = match.split()
        for pkg in packages:
            pkg = pkg.strip()
            # Skip flags and non-package tokens
            if pkg.startswith('-') or pkg.startswith('--'):
                continue
            # Extract package name (before version specifier)
            pkg_name = re.split(r'[<>=!~\[]', pkg)[0].strip().lower()
            if pkg_name and not pkg_name.startswith('http'):
                extracted_packages.add(pkg_name)

print(f"  ℹ️  Extracted from INSTALL_EXCEL_IMPORT.md: {len(extracted_packages)} packages")
if extracted_packages:
    print(f"      {', '.join(sorted(extracted_packages))}")

# Standard dependencies for the project (based on known usage)
standard_dependencies = {
    'flask',
    'pandas',
    'openpyxl',
    'xlrd',
}

# Merge all dependencies
all_dependencies = existing_requirements | extracted_packages | standard_dependencies

# Sort and prepare requirements.txt content
sorted_deps = sorted(all_dependencies)
requirements_content = "# ============================================================\n"
requirements_content += "#  GRYPHONE — Python dependencies\n"
requirements_content += "#  ------------------------------------------------------------\n"
requirements_content += "#  Install with: pip install -r requirements.txt\n"
requirements_content += "# ============================================================\n\n"

for dep in sorted_deps:
    requirements_content += f"{dep}\n"

# Write requirements.txt
req_file.write_text(requirements_content, encoding="utf-8")
print(f"\n  ✔ Updated requirements.txt with {len(sorted_deps)} packages")
print(f"      {', '.join(sorted_deps)}")
PYEOF

# ============================================================
# Step 3: Update INSTALL_EXCEL_IMPORT.md
# ============================================================
echo ""
echo "🔧 Updating INSTALL_EXCEL_IMPORT.md..."

"${PYCMD[@]}" << 'PYEOF'
from pathlib import Path
import re

md_file = Path("INSTALL_EXCEL_IMPORT.md")
content = md_file.read_text(encoding="utf-8")
original = content

# Replace individual pip install commands with requirements.txt reference
# Pattern 1: pip install pandas openpyxl
content = re.sub(
    r'pip3? install\s+(?!.*requirements\.txt)[^\n]+',
    'pip install -r requirements.txt',
    content
)

# Pattern 2: python -m pip install ...
content = re.sub(
    r'python\s+-m\s+pip\s+install\s+(?!.*requirements\.txt)[^\n]+',
    'pip install -r requirements.txt',
    content
)

# Remove duplicate lines (if multiple pip install lines were replaced)
lines = content.split('\n')
seen_pip_lines = set()
filtered_lines = []
for line in lines:
    stripped = line.strip()
    if stripped == 'pip install -r requirements.txt':
        if stripped not in seen_pip_lines:
            filtered_lines.append(line)
            seen_pip_lines.add(stripped)
    else:
        filtered_lines.append(line)

content = '\n'.join(filtered_lines)

# Add a note about requirements.txt if not already present
if 'requirements.txt' not in content:
    # Find the first ## Installation or ## Установка section
    install_section = re.search(r'(##\s+(?:Installation|Установка|Инсталляция)[^\n]*\n)', content, re.IGNORECASE)
    if install_section:
        insert_pos = install_section.end()
        note = "\nВсе зависимости перечислены в `requirements.txt`. Установите их одной командой:\n```bash\npip install -r requirements.txt\n```\n"
        content = content[:insert_pos] + note + content[insert_pos:]

if content != original:
    md_file.write_text(content, encoding="utf-8")
    print("  ✔ Updated INSTALL_EXCEL_IMPORT.md")
    print("      - Individual pip install commands replaced with requirements.txt")
    print("      - Added note about requirements.txt")
else:
    print("  ℹ️  No changes needed in INSTALL_EXCEL_IMPORT.md")
PYEOF

# ============================================================
# Step 4: Verification
# ============================================================
echo ""
echo "🔍 Verification..."

if [ -f "requirements.txt" ]; then
    echo "  ✔ requirements.txt exists"
    echo ""
    echo "  📋 Content of requirements.txt:"
    echo "  ─────────────────────────────────"
    sed 's/^/  │ /' requirements.txt
    echo "  ─────────────────────────────────"
else
    echo "  ❌ ERROR: requirements.txt was not created"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Requirements merged successfully"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 What was done:"
echo "  • Extracted dependencies from INSTALL_EXCEL_IMPORT.md"
echo "  • Merged with existing requirements.txt"
echo "  • Added standard project dependencies"
echo "  • Updated INSTALL_EXCEL_IMPORT.md to reference requirements.txt"
echo ""
echo "🚀 To install dependencies:"
echo "  pip install -r requirements.txt"