import argparse
import ast
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

"""
I don't love using vars like: a b c
but it's really needed here
p - path
f - file
pd - priority dir
"""

# CONFIGURATION
SCRIPT_DIR = Path(__file__).parent.resolve()
DIST_DIR = SCRIPT_DIR / "dist"
ROOT_DIST_DIR = SCRIPT_DIR.parent.parent
OUTPUT_FILENAME = "LiteGram.plugin"
SRC_DIR = SCRIPT_DIR / "LiteGram"
HEADER_FILE = SRC_DIR / "header.py"

PRIORITY_FILES = ["header.py"]
PRIORITY_DIRS = ["data", "i18n", "utils"]
LAST_FILES = ["ui/settings.py", "main.py"]

COPYRIGHT_STRING = (
    "# Open Source LiteGram plugin for https://exteragram.app\n"
    "# Plugin created by t.me/wepinek\n"
    "# Licensed under the MIT License\n"
    "# Repository: https://github.com/nonFeature/LegacyGram\n"
)

HEADER_WATERMARK = """
#          @@@@@@@@@@
#        @@@@@@@@@@@@
#       @@@@@
#       @@@@
# @@@@@@@@@@@@@@@@@@@
# @@@@@@@@@@@@@@@@@@@
#       @@@@
#       @@@@
#       @@@@
#       @@@@
#       @@@@
#       @@@@
# @@@@@@@@@@@@@@@@@@@
# @@@@@@@@@@@@@@@@@@@
"""

FOOTER_WATERMARK = """
#       @@@@
# @@@@@@@@@@@@@@@@
# @@@@@@@@@@@@@@@@
# @@@@@@@@@@@@@@@@
# @@@@@@@@@@@@@@@
# @@@@@@@@@@@@@@@
# @@@@@@@@@@@@@@@
# @@@@@@@@@@@@@@@@
# @@@@@@@@@@@@@@@@
# @@@@@@@@@@@@@@@@
"""

captured_imports = defaultdict(set)
captured_from_imports = defaultdict(set)


def parse_args():
    parser = argparse.ArgumentParser(description="LiteGram Build Script")
    parser.add_argument("--no-bump", action="store_true", help="Compatibility flag; build no longer increments the version")
    parser.add_argument("--no-minify", action="store_true", help="Disable minification entirely (keep comments, docstrings, and type hints)")
    parser.add_argument(
        "--minify-level",
        choices=["light", "medium", "max"],
        default="max",
        help=(
            "Minification level (default: max). "
            "light = remove comments/docstrings/annotations only (AST); "
            "medium = + whitespace compression, no variable renaming; "
            "max = + rename locals, hoist literals (smallest size)"
        ),
    )
    parser.add_argument("--no-lint", action="store_true", help="Disable linter check")
    parser.add_argument("--crlf", action="store_true", help="Use Windows CRLF line endings instead of Unix LF")
    return parser.parse_args()


def get_current_version() -> str | None:
    content = HEADER_FILE.read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', content)
    if match:
        return match.group(1)
    return None


def increment_version(version: str) -> str:
    match = re.search(r"(\d+)([^\d]*)$", version)
    if match:
        num = int(match.group(1))
        suffix = match.group(2)
        prefix = version[: match.start(1)]
        return f"{prefix}{num + 1}{suffix}"
    return version


def update_header_version(new_version: str) -> None:
    content = HEADER_FILE.read_text(encoding="utf-8")
    content = re.sub(
        r'__version__\s*=\s*"[^"]+"',
        f'__version__ = "{new_version}"',
        content,
    )
    HEADER_FILE.write_text(content, encoding="utf-8")


def run_linter():
    print("🔍 Running Ruff and ty...")

    subprocess.run(["ruff", "check", ".", "--fix"], capture_output=True)
    subprocess.run(["ruff", "format", "."], capture_output=True)

    result = subprocess.run(["ruff", "check", "."], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ Ruff issues found:\n{result.stdout}")
        return False

    ty_result = subprocess.run(["ty", "check"], capture_output=True, text=True)

    if ty_result.returncode != 0:
        print(f"❌ Type issues found:\n{ty_result.stdout}")
        return False

    print("✅ Code is clean. Proceeding to build...")
    return True


def get_all_python_files(src: Path) -> list[Path]:
    return [p.relative_to(src) for p in src.rglob("*.py") if p.name != "__init__.py"]


def get_merge_order(all_files: list[Path]) -> list[Path]:
    order = []
    processed: set[Path] = set()

    # Priority Files
    for pf in PRIORITY_FILES:
        p = Path(pf)
        if p in all_files:
            order.append(p)
            processed.add(p)

    # Priority Directories
    for pd in PRIORITY_DIRS:
        dir_files = sorted([f for f in all_files if f.parts[0] == pd and f not in processed])
        order.extend(dir_files)
        processed.update(dir_files)

    # Everything else (except LAST_FILES)
    last_paths = {Path(f) for f in LAST_FILES}
    others = sorted([f for f in all_files if f not in processed and f not in last_paths])
    order.extend(others)
    processed.update(others)

    # Last Files
    for lf in LAST_FILES:
        p = Path(lf)
        if p in all_files:
            order.append(p)
            processed.add(p)

    return order


def parse_import_line(line: str):
    line = line.strip()

    from_match = re.match(r"^from ([\w.]+) import (.+)$", line)
    if from_match:
        module, names = from_match.groups()
        for name in names.split(","):
            captured_from_imports[module].add(name.strip())
        return

    import_match = re.match(r"^import ([\w.]+)$", line)
    if import_match:
        module = import_match.group(1)
        _ = captured_imports[module]


def normalize_import_block(import_lines: list[str]) -> str:
    block = " ".join(line.strip() for line in import_lines)
    block = re.sub(r"#.*", "", block)  # Strip inline comments
    block = re.sub(r"\s+", " ", block)
    block = block.replace("( ", "").replace("(", "").replace(" )", "").replace(")", "")
    return block.strip()


def generate_imports_block() -> str:
    lines = []

    for mod in sorted(captured_imports.keys()):
        lines.append(f"import {mod}")

    for mod in sorted(captured_from_imports.keys()):
        names = sorted(captured_from_imports[mod])
        lines.append(f"from {mod} import {', '.join(names)}")

    return "\n".join(lines) + "\n"


def process_file_content(file_path: Path) -> list[str]:
    """Removes imports, only comments lines, and docstrings"""
    with open(SRC_DIR / file_path, encoding="utf-8") as f:
        lines = f.readlines()

    processed_lines = []
    in_docstring = False
    docstring_char = None

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Check for docstring delimiters (both """ and ''')
        if not in_docstring:
            if stripped.startswith('"""'):
                docstring_char = '"""'
            elif stripped.startswith("'''"):
                docstring_char = "'''"
            else:
                docstring_char = None

        if docstring_char and docstring_char in stripped:
            count = stripped.count(docstring_char)
            if count == 1:
                in_docstring = not in_docstring
                i += 1
                continue
            elif count >= 2:
                if not in_docstring:
                    i += 1
                    continue
                else:
                    in_docstring = False
                    docstring_char = None
                    i += 1
                    continue

        # Skip if in docstrings
        if in_docstring:
            i += 1
            continue

        # Skip comment-only lines
        if stripped.startswith("#"):
            i += 1
            continue

        # Skip import lines (but parse them first)
        is_import = stripped.startswith(("import ", "from "))
        is_internal = stripped.startswith(("import LiteGram", "from LiteGram"))

        if is_import:
            import_lines = [line]
            open_parens = line.count("(") - line.count(")")
            while open_parens > 0 and i + 1 < len(lines):
                i += 1
                next_line = lines[i]
                import_lines.append(next_line)
                open_parens += next_line.count("(") - next_line.count(")")

            if not is_internal:
                parse_import_line(normalize_import_block(import_lines))
            i += 1
            continue

        processed_lines.append(line)
        i += 1

    file_code = "".join(processed_lines)
    cleaned_code = file_code.strip()
    cleaned_code = re.sub(r"\n{3,}", "\n\n", cleaned_code)

    return [cleaned_code + "\n"]


class ASTMinifier(ast.NodeTransformer):
    """AST transformer that removes docstrings and type annotations to reduce file size."""

    def visit_FunctionDef(self, node):
        node.returns = None
        for arg in node.args.posonlyargs:
            arg.annotation = None
        for arg in node.args.args:
            arg.annotation = None
        if node.args.vararg:
            node.args.vararg.annotation = None
        for arg in node.args.kwonlyargs:
            arg.annotation = None
        if node.args.kwarg:
            node.args.kwarg.annotation = None
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node):
        node.returns = None
        for arg in node.args.posonlyargs:
            arg.annotation = None
        for arg in node.args.args:
            arg.annotation = None
        if node.args.vararg:
            node.args.vararg.annotation = None
        for arg in node.args.kwonlyargs:
            arg.annotation = None
        if node.args.kwarg:
            node.args.kwarg.annotation = None
        self.generic_visit(node)
        return node

    def visit_AnnAssign(self, node):
        self.generic_visit(node)
        if node.value is None:
            return None  # Remove variable declarations that have only type hints (e.g. x: int)
        new_node = ast.Assign(targets=[node.target], value=node.value)
        return ast.copy_location(new_node, node)

    def visit_Expr(self, node):
        # Remove docstring statements
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return None
        self.generic_visit(node)
        return node

    def visit_Module(self, node):
        self.generic_visit(node)
        if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
            node.body.pop(0)
        return node

    def visit_ClassDef(self, node):
        self.generic_visit(node)
        if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
            node.body.pop(0)
        return node


def build():
    args = parse_args()
    print(f"🚀 Starting build: {OUTPUT_FILENAME}...")

    if not SRC_DIR.exists():
        print(f"❌ Error: Source directory '{SRC_DIR}' not found!")
        sys.exit(1)

    if not HEADER_FILE.exists():
        print(f"❌ Error: Header file '{HEADER_FILE}' not found!")
        sys.exit(1)

    current_version = get_current_version()
    if not current_version:
        print("❌ Error: Can't find __version__ field in header!")
        sys.exit(1)

    print(f"📌 Version: {current_version}")

    if not args.no_lint:
        if not run_linter():
            sys.exit(1)

    all_files = get_all_python_files(SRC_DIR)
    merge_order = get_merge_order(all_files)

    body_content = []
    for file_path in merge_order:
        print(f"📦 Merging: {file_path}")
        body_content.append(f"\n# === {file_path} ===\n")
        body_content.extend(process_file_content(file_path))

    imports_block = generate_imports_block()
    combined_code = imports_block + "".join(body_content)

    if args.no_minify:
        print("ℹ️ Minification is disabled via --no-minify")
        full_code = COPYRIGHT_STRING + "\n" + combined_code
    else:
        level = args.minify_level
        print(f"⚡ Minifying plugin (level: {level})...")

        if level == "light":
            # AST-only: strip docstrings, type annotations, pass statements
            try:
                tree = ast.parse(combined_code)
                minifier = ASTMinifier()
                minified_tree = minifier.visit(tree)
                minified_code = ast.unparse(minified_tree)
                full_code = COPYRIGHT_STRING + "\n" + minified_code
            except Exception as e:
                print(f"⚠️ Warning: AST minification failed ({e}). Falling back to unminified build.")
                full_code = COPYRIGHT_STRING + "\n" + combined_code
        else:
            # medium / max: use python-minifier
            rename_locals = level == "max"
            hoist_literals = level == "max"
            try:
                import python_minifier

                minified_code = python_minifier.minify(
                    combined_code,
                    rename_globals=False,
                    rename_locals=rename_locals,
                    hoist_literals=hoist_literals,
                    remove_annotations=True,
                    remove_pass=True,
                    remove_literal_statements=True,
                    combine_imports=True,
                )
                full_code = COPYRIGHT_STRING + "\n" + minified_code
            except Exception as e:
                print(f"⚠️ Warning: python-minifier failed ({e}). Falling back to AST minification.")
                try:
                    tree = ast.parse(combined_code)
                    minifier = ASTMinifier()
                    minified_tree = minifier.visit(tree)
                    minified_code = ast.unparse(minified_tree)
                    full_code = COPYRIGHT_STRING + "\n" + minified_code
                except Exception as e2:
                    print(f"⚠️ Warning: AST minification failed ({e2}). Falling back to unminified build.")
                    full_code = COPYRIGHT_STRING + "\n" + combined_code

    full_code = HEADER_WATERMARK + "\n" + full_code + "\n\n" + FOOTER_WATERMARK

    DIST_DIR.mkdir(exist_ok=True)
    out_path = DIST_DIR / OUTPUT_FILENAME

    newline = "\r\n" if args.crlf else "\n"
    out_path.write_text(full_code, encoding="utf-8", newline=newline)

    try:
        ROOT_DIST_DIR.mkdir(exist_ok=True)
        (ROOT_DIST_DIR / OUTPUT_FILENAME).write_text(full_code, encoding="utf-8", newline=newline)
    except Exception:
        pass

    # Calculate actual sizes
    orig_bytes = (HEADER_WATERMARK + "\n" + COPYRIGHT_STRING + "\n" + combined_code + "\n\n" + FOOTER_WATERMARK).replace("\n", newline).encode("utf-8")
    orig_size = len(orig_bytes)
    final_size = out_path.stat().st_size

    print(f"\n🎉 Build successful: {out_path}")

    saved_bytes = orig_size - final_size
    pct = (saved_bytes / orig_size) * 100 if orig_size > 0 else 0

    print(f"📉 Size on disk: {final_size / 1024:.1f} KB (originally {orig_size / 1024:.1f} KB, saved {saved_bytes / 1024:.1f} KB / {pct:.1f}%)")


if __name__ == "__main__":
    build()
