--discard-files-in    txt con rutas (coma o salto de línea)
--discard-all-in      idem
--discard-files       nombres de archivo separados por coma

Comando:

```
    # solo JSON
    python scan_project.py C:\mi\repo

    # JSON + árbol en consola
    python scan_project.py C:\mi\repo --pretty

    # JSON + árbol en consola + árbol en README_TREE.md
    python scan_project.py C:\mi\repo --pretty --tree-md README_TREE.md

    # Ignora archivos dentro de archivo/permisos, salta carpetas en .git y node_modules,
    # y nunca indexa README.md ni .DS_Store
    python scan_project.py C:\miRepo `
    --discard-files-in "generated/acceso" `
    --discard-all-in   ".git,node_modules" `
    --discard-files    "README.md,.DS_Store" `
    --pretty --tree-md README_TREE.md

    python scan_project.py C:\miRepo `
    --discard-all-in    "generated/acceso,generated/permisos,generated/roles" `
    --discard-files-in  ".git,node_modules,logs,media" `
    --pretty --tree-md  README_TREE.md
```