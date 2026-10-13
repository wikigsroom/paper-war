"""Resolve runtime asset paths from exported data and native GDScript literals."""
from pathlib import Path
import json
import re
import fnmatch
import os

RASTER_AUDIO_FONT = {'.png','.jpg','.jpeg','.webp','.svg','.ttf','.otf','.wav','.ogg','.mp3','.tres','.tscn','.gdshader'}


def project_files(game, patterns):
    """Walk authoring files without descending into Godot's generated cache."""
    game=Path(game).resolve()
    patterns=tuple(patterns)
    for root, directories, files in os.walk(game):
        directories[:]=[name for name in directories if name not in {'.godot','output'}]
        for name in files:
            if any(fnmatch.fnmatchcase(name,pattern) for pattern in patterns):
                yield Path(root)/name


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from strings(child)


def runtime_asset_inputs(game):
    game=Path(game).resolve()
    presets=(game/'export_presets.cfg').read_text('utf-8')
    excluded={pattern for value in re.findall(r'exclude_filter="([^"]*)"',presets) for pattern in value.split(',') if pattern}
    def omitted(path):
        name=path.relative_to(game).as_posix()
        return any(fnmatch.fnmatchcase(name,pattern) for pattern in excluded)
    names=set()
    for file in (game/'data').glob('*.json'):
        if omitted(file):continue
        names.update(s for s in strings(json.loads(file.read_text('utf-8'))) if s.startswith('res://assets/'))
    literal_sources=[game/'project.godot',*sorted((game/'scripts').glob('*.gd'))]
    for pattern in ('*.tscn','*.tres','*.gdshader'):
        literal_sources.extend(project_files(game,[pattern]))
    for file in literal_sources:
        if omitted(file):continue
        names.update(re.findall(r'res://assets/[^\s"\'\)\]\}]+',file.read_text('utf-8')))
    paths=set()
    for name in names:
        path=game/name.removeprefix('res://')
        # Static paths have exact files. Concatenated script prefixes select
        # only their matching sibling resources, never an authoring frame tree.
        candidates=[path] if path.is_file() else list(path.parent.glob(path.name+'*')) if path.parent.is_dir() else []
        for candidate in candidates:
            if candidate.is_file() and candidate.suffix.lower() in RASTER_AUDIO_FONT and not omitted(candidate):
                candidate.resolve().relative_to(game)
                paths.add(candidate)
    return sorted(paths)
