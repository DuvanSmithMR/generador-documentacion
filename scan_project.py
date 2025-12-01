import os
import json
from pathlib import Path

IGNORED_DIRS = {
    'node_modules', '.git', '__pycache__', '.venv', 'venv', '.next', 'dist', 'build', '.nuxt'
}

def extract_package_json_info(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {
            "scripts": data.get("scripts", {}),
            "dependencies": data.get("dependencies", {}),
            "devDependencies": data.get("devDependencies", {})
        }
    except Exception as e:
        return {"error": str(e)}

def scan_directory(root_path):
    root = Path(root_path).resolve()
    structure = {}

    def build_tree(current_path: Path):
        relative = current_path.relative_to(root)
        node = {
            "type": "directory",
            "path": str(relative).replace("\\", "/"),
            "children": {},
            "descripcion": ""
        }

        for item in sorted(current_path.iterdir()):
            if item.is_dir() and item.name not in IGNORED_DIRS:
                node["children"][item.name] = build_tree(item)
            elif item.is_file():
                file_node = {
                    "type": "file",
                    "path": str(item.relative_to(root)).replace("\\", "/"),
                    "descripcion": ""
                }
                if item.name == "package.json":
                    file_node.update(extract_package_json_info(item))
                node["children"][item.name] = file_node

        return node

    structure[root.name] = build_tree(root)
    return structure

def save_to_json(data, output_file="project_structure.json"):
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    import sys
    project_path = sys.argv[1] if len(sys.argv) > 1 else "."
    result = scan_directory(project_path)
    save_to_json(result)
    print("✅ Estructura guardada en 'project_structure.json'")