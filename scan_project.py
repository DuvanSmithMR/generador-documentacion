#!/usr/bin/env python3
"""
scan_project.py – Explora un proyecto y genera project_structure.json
pip install typer rich pydantic
"""
import json
from pathlib import Path
from typing import Dict, Optional

import typer
from pydantic import BaseModel, Field
from rich.console import Console, Capture
from rich.tree import Tree

from io import StringIO

app = typer.Typer()
console = Console()

DEFAULT_IGNORE = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    ".next", "dist", "build", ".nuxt", ".pytest_cache", ".mypy_cache"
}


# ---------- modelos ----------
class PackageJson(BaseModel):
    scripts: Dict[str, str] = Field(default_factory=dict)
    dependencies: Dict[str, str] = Field(default_factory=dict)
    devDependencies: Dict[str, str] = Field(default_factory=dict)


class FileNode(BaseModel):
    type: str = "file"
    path: str
    descripcion: str = ""
    scripts: Optional[Dict[str, str]] = None
    dependencies: Optional[Dict[str, str]] = None
    devDependencies: Optional[Dict[str, str]] = None


class DirNode(BaseModel):
    type: str = "directory"
    path: str
    descripcion: str = ""
    children: Dict[str, "Node"] = Field(default_factory=dict)


Node = FileNode | DirNode   # 3.10+ syntax


# ---------- utilidades ----------
def extract_package_json_info(file_path: Path) -> dict:
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        pkg = PackageJson.model_validate(data)
        return pkg.model_dump(exclude_none=True)
    except Exception as e:
        console.print(f"[yellow]⚠️  No se pudo leer {file_path}: {e}[/yellow]")
        return {}


def render_tree_plain(root_node: DirNode, root_name: str) -> str:
    """Devuelve el árbol como texto sin colores."""
    buffer = StringIO()
    cons = Console(file=buffer, color_system=None, width=240)
    tree = Tree(root_name)
    _fill_rich_tree(root_node, tree)
    cons.print(tree)
    return buffer.getvalue()

def _fill_rich_tree(node: DirNode, parent: Tree):
    """Recursivo para Rich."""
    for name, child in node.children.items():
        if isinstance(child, DirNode):
            branch = parent.add(f"{name}/")
            _fill_rich_tree(child, branch)
        else:
            parent.add(name)


# ---------- árbol ----------
def build_tree(current: Path, root: Path, ignore: set[str], rich_parent: Tree) -> DirNode:
    relative = current.relative_to(root)
    node = DirNode(path=str(relative).replace("\\", "/"))

    for item in sorted(current.iterdir()):
        name = item.name
        if name in ignore:
            continue
        if item.is_dir():
            rich_dir = rich_parent.add(f"[bold cyan]{name}/")
            node.children[name] = build_tree(item, root, ignore, rich_dir)
        elif item.is_file():
            file_info = extract_package_json_info(item) if name == "package.json" else {}
            file_node = FileNode(
                path=str(item.relative_to(root)).replace("\\", "/"),
                descripcion="",
                **file_info
            )
            node.children[name] = file_node
            rich_parent.add(f"[green]{name}[/green]")
    return node


# ---------- CLI ----------
@app.command()
def main(
    project_path: Path = typer.Argument(".", help="Carpeta a escanear"),
    output: str = typer.Option("project_structure.json", "--output", "-o"),
    ignore: list[str] = typer.Option(
        list(DEFAULT_IGNORE), "--ignore", "-i", help="Carpetas a omitir"
    ),
    pretty: bool = typer.Option(False, "--pretty", "-p", help="Mostrar árbol en consola"),
    tree_md: Optional[str] = typer.Option(
        None, "--tree-md", help="Guardar solo el árbol en un archivo .md (p. ej. README_TREE.md)"
    ),
) -> None:
    root = project_path.resolve()
    if not root.is_dir():
        console.print("[red]✖ La ruta indicada no es un directorio.[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]Explorando:[/bold] {root}")
    rich_tree = Tree(f"[bold bright_white]{root.name}/") if pretty else Tree("")
    structure = {root.name: build_tree(root, root, set(ignore), rich_tree)}

    if pretty:
        console.print(rich_tree)

    if tree_md:
        plain_text = render_tree_plain(structure[root.name], root.name)
        Path(tree_md).write_text(
            f"# Árbol del proyecto\n\n```\n{plain_text}\n```\n",
            encoding="utf-8"
        )
        console.print(f"[bold green]✅ Árbol guardado en {tree_md}[/bold green]")

    out_path = Path(output)
    out_path.write_text(
        json.dumps(structure, indent=2, ensure_ascii=False, default=dict),
        encoding="utf-8"
    )
    console.print(f"[bold green]✅ JSON guardado en {out_path.absolute()}[/bold green]")


if __name__ == "__main__":
    app()