#!/usr/bin/env python3
"""
scan_project.py – Explora un proyecto y genera project_structure.json
Nuevos filtros:
  --discard-files-in  carpetas donde solo se indexan sub-carpetas
  --discard-all-in    carpetas que se saltan por completo
  --discard-files     archivos específicos a ignorar globalmente
pip install typer rich pydantic
"""
import json
import sys
from pathlib import Path
from typing import Dict, Optional, Set

import typer
from pydantic import BaseModel, Field
from rich.console import Console
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


# ---------- helpers ----------
def _read_list_option(value: Optional[str]) -> Set[str]:
    """Convierte string separado por comas o saltos de línea en conjunto."""
    if not value:
        return set()
    parts = [p.strip() for p in value.replace(",", "\n").splitlines() if p.strip()]
    return set(parts)


def extract_package_json_info(file_path: Path) -> dict:
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        pkg = PackageJson.model_validate(data)
        return pkg.model_dump(exclude_none=True)
    except Exception as e:
        console.print(f"[yellow]⚠️  No se pudo leer {file_path}: {e}[/yellow]")
        return {}


def _fill_rich_tree(node: DirNode, parent: Tree):
    for name, child in node.children.items():
        if isinstance(child, DirNode):
            branch = parent.add(f"[bold cyan]{name}/")
            _fill_rich_tree(child, branch)
        else:
            parent.add(f"[green]{name}[/green]")


def render_tree_plain(root_node: DirNode, root_name: str) -> str:
    buffer = StringIO()
    cons = Console(file=buffer, color_system=None, width=240)
    tree = Tree(root_name)
    _fill_rich_tree(root_node, tree)
    cons.print(tree)
    return buffer.getvalue()


# ---------- árbol ----------
def build_tree(
    current: Path,
    root: Path,
    ignore: Set[str],
    discard_files_in: Set[str],
    discard_all_in: Set[str],
    discard_files: Set[str],
    rich_parent: Tree
) -> DirNode:
    relative = current.relative_to(root)
    relative_str = str(relative).replace("\\", "/")
    node = DirNode(path=relative_str)

    # Si esta carpeta está en "descartar todo", devolvemos nodo vacío y listo
    if relative_str in discard_all_in:
        return node

    items = sorted(current.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))  # carpetas primero

    for item in items:
        name = item.name
        if name in ignore:
            continue

        # Filtro global de archivos específicos
        if item.is_file() and name in discard_files:
            continue

        ruta_completa = str(item.relative_to(root)).replace("\\", "/")

        if item.is_dir():
            # ¿Está dentro de alguna carpeta "discard-files-in"?
            flag_discard_files = any(ruta_completa.startswith(df) for df in discard_files_in)
            rich_dir = rich_parent.add(f"[bold cyan]{name}/")
            child_node = build_tree(
                item, root, ignore,
                discard_files_in, discard_all_in, discard_files,
                rich_dir
            )
            node.children[name] = child_node
        elif item.is_file():
            # ¿Está dentro de alguna carpeta "discard-files-in"?
            if any(ruta_completa.startswith(df) for df in discard_files_in):
                continue
            file_info = extract_package_json_info(item) if name == "package.json" else {}
            file_node = FileNode(
                path=ruta_completa,
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
        list(DEFAULT_IGNORE), "--ignore", "-i", help="Carpetas a omitir (por defecto)"
    ),
    pretty: bool = typer.Option(False, "--pretty", "-p", help="Mostrar árbol en consola"),
    tree_md: Optional[str] = typer.Option(
        None, "--tree-md", help="Guardar solo el árbol en un archivo .md (p. ej. README_TREE.md)"
    ),
    discard_files_in: Optional[str] = typer.Option(
        None, "--discard-files-in",
        help="Rutas relativas donde solo se indexan carpetas (separadas por coma o \\n)"
    ),
    discard_all_in: Optional[str] = typer.Option(
        None, "--discard-all-in",
        help="Rutas relativas que se ignoran por completo (separadas por coma o \\n)"
    ),
    discard_files: Optional[str] = typer.Option(
        None, "--discard-files",
        help="Nombres de archivo a ignorar globalmente (separados por coma)"
    ),
) -> None:
    root = project_path.resolve()
    if not root.is_dir():
        console.print("[red]✖ La ruta indicada no es un directorio.[/red]")
        raise typer.Exit(1)

    discard_files_in_set = _read_list_option(discard_files_in)
    discard_all_in_set = _read_list_option(discard_all_in)
    discard_files_set = _read_list_option(discard_files)

    console.print(f"[bold]Explorando:[/bold] {root}")
    rich_tree = Tree(f"[bold bright_white]{root.name}/") if pretty else Tree("")
    structure = {root.name: build_tree(
        root, root, set(ignore),
        discard_files_in_set, discard_all_in_set, discard_files_set,
        rich_tree
    )}

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