import re
from typing import List, Tuple

QUERY_PATTERN = re.compile(r"\s*⟨(.*?)⟩\s*(.*?)\s*⟨(.*?)⟩\s*(\d+)\s*")

ROUTER_REGEX = re.compile(r"\[\.?#?(\w+)#?\.?\]")


def validate_router_names(path: str, allowed_routers: List[str]) -> Tuple[bool, str]:
    """
    Extracts all router names from the path component and checks
    whether they exist in the allowed router list.
    """
    used_routers = ROUTER_REGEX.findall(path)
    invalid = [r for r in used_routers if r not in allowed_routers]

    if invalid:
        print(f"[!] Invalid router names in query: {', '.join(invalid)}")
        return False, f"Invalid router names in query: '{', '.join(invalid)}'."

    return True, ""

def is_valid_label(label: str, model) -> bool:
    """
    Validates a label expression from <...>.
    Supports space-separated label stacks, comma-separated lists,
    and regex-like modifiers (?, *, +) and wildcards.
    """
    label_set = set(model.labels)

    # Split on spaces and commas, keep each part
    parts = re.split(r'[,\s]+', label.strip())

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Allow full wildcard expressions
        if part in [".", ".*", ".+", ".?"]:
            continue

        # Allow label modifiers like *, +, ?
        m = re.match(r'^(\w+)?$', part)
        if m:
            base_label = m.group(1)
            if base_label not in label_set:
                return False
            continue

        # Plain label
        if part in label_set:
            continue

        return False  # invalid token

    return True


def is_valid_path_format(path: str, model) -> Tuple[bool, str]:
    path = path.strip()
    if not path:
        return False, "Path is empty."

    # 1. Character whitelist
    allowed_chars_pattern = re.compile(r'^[\w\s\[\]\.\*\+\?\^\(\)\#\,\-\"]+$')
    if not allowed_chars_pattern.fullmatch(path):
        return False, "Path contains illegal characters."

    # 2. Balanced brackets
    if path.count('[') != path.count(']'):
        return False, "Unbalanced square brackets."
    if path.count('(') != path.count(')'):
        return False, "Unbalanced parentheses."

    # 3. Extract atom blocks
    atom_pattern = re.compile(r'\[[^\[\]]+\]')
    atoms = atom_pattern.findall(path)

    for atom in atoms:
        if not is_valid_atom_block(atom):
            return False, f"Invalid atom block: {atom}"

    # 4. Check router names inside atoms
    is_valid, router_err = validate_router_names(path, model.routers)
    if not is_valid:
        return False, router_err

    # 5. Check for forbidden leading ^ outside atoms
    if re.search(r'\s\^', path) or path.lstrip().startswith('^'):
        return False, "Invalid use of '^' outside of atoms."

    return True, ""


def is_valid_atom_block(atom: str) -> bool:
    """
    Validates a single [ ... ] atom block.
    Accepts:
    - [.#R], [R#.]
    - [^A#B], [A#B,C#D]
    - [^.#v1, .#v2], etc.
    """
    atom = atom.strip()
    if not atom.startswith('[') or not atom.endswith(']'):
        return False

    inner = atom[1:-1].strip()
    if not inner:
        return False

    is_negated = inner.startswith('^')
    if is_negated:
        inner = inner[1:].strip()

    parts = [p.strip() for p in inner.split(',') if p.strip()]
    if not parts:
        return False

    for part in parts:
        if '#' not in part:
            return False

        src, dst = part.split('#', 1)
        for iface in (src, dst):
            if iface == '.':
                continue
            if iface.startswith('"') and iface.endswith('"'):
                continue
            if not re.fullmatch(r'[\w\.]+', iface):
                return False

    return True

