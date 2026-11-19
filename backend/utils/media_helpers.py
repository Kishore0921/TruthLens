from pathlib import Path

def ensure_directory(path: Path):
    path.mkdir(parents=True, exist_ok=True)

def get_relative_path(full_path: Path, base_path: Path) -> str:
    try:
        return str(full_path.relative_to(base_path))
    except ValueError:
        return full_path.name
