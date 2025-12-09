import json
import os
import logging

def update_notebook_logging(notebook_path: str = None):
    """
    Updates the Jupyter Notebook logging configuration to include FileHandler.
    """
    if notebook_path is None:
        # Resolve path relative to this script: ../main.ipynb
        script_dir = os.path.dirname(os.path.abspath(__file__))
        notebook_path = os.path.join(script_dir, '..', 'main.ipynb')
    
    notebook_path = os.path.abspath(notebook_path)
    print(f"Targeting notebook at: {notebook_path}")

    if not os.path.exists(notebook_path):
        print(f"Error: Notebook not found at {notebook_path}")
        return

    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    # The code we want to insert
    new_logging_code = [
        "import os\n",
        "\n",
        "# Crear carpeta logs si no existe\n",
        "log_dir = \"logs\"\n",
        "os.makedirs(log_dir, exist_ok=True)\n",
        "log_file = os.path.join(log_dir, \"pipeline.log\")\n",
        "\n",
        "# Configurar logger raiz (evitando duplicados en re-runs)\n",
        "logger = logging.getLogger()\n",
        "if logger.hasHandlers():\n",
        "    logger.handlers.clear()\n",
        "\n",
        "logging.basicConfig(\n",
        "    level=logging.INFO,\n",
        "    format='%(asctime)s - %(levelname)s - %(message)s',\n",
        "    handlers=[\n",
        "        logging.FileHandler(log_file, mode='a', encoding='utf-8'),\n",
        "        logging.StreamHandler()\n",
        "    ]\n",
        ")\n",
        "logging.info(f\"Logging iniciado. Archivo: {log_file}\")\n"
    ]

    # Find the cell and replace the line
    found = False
    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            source = cell['source']
            for i, line in enumerate(source):
                # Check for old config OR new config (to avoid re-patching if already correct but just update the code block)
                if "logging.basicConfig" in line:
                    # Logic to determine if update is needed could be here, but simpler to just overwrite 
                    # if it looks like a logging config block.
                    # Warning: simple string matching. 
                    cell['source'][i:i+len(new_logging_code)] = new_logging_code
                    # Truncate if we replaced a single line with multiple previously, 
                    # but here we might be replacing a block.
                    # Best approach: Replace the WHOLE cell content if it's the specific config cell.
                    # But finding specific cell is hard. 
                    # Let's stick to the previous robust logic:
                    # If line has basicConfig AND NOT FileHandler -> Update
                    if "logging.FileHandler" not in ''.join(source):
                         cell['source'][i:i+1] = new_logging_code
                         found = True
                    else:
                        print("Notebook already has FileHandler configuration.")
                        found = True # Considered "success" as it's already done
                    break
        if found:
            break

    if found:
        with open(notebook_path, 'w', encoding='utf-8') as f:
            json.dump(nb, f, indent=4)
        print("Notebook configuration checked/updated successfully.")
    else:
        print("Could not find the target logging configuration line to update.")

if __name__ == "__main__":
    update_notebook_logging()
