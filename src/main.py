from prompt_builder import regenerate_full_query_until_valid
from network_parser import load_network_model
import subprocess
import json
import os

def windows_to_wsl_path(path: str) -> str:
    drive, rest = os.path.splitdrive(os.path.abspath(path))
    drive_letter = drive.rstrip(':').lower()
    return f"/mnt/{drive_letter}{rest.replace('\\', '/')}"

def get_aalwines_bin():
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            config = json.load(f)
            path = config.get("aalwines_bin_path")
            return path

    raise FileNotFoundError("AalWiNes binary not found. Please set AALWINES_BIN or config.json.")


def run_aalwines(query: str, network_path: str, weight_path: str, query_path: str):
    # Save query file in Windows
    with open(query_path, 'w', encoding='utf-8') as f:
        f.write(query)

    # Convert to WSL-style paths
    network_path_wsl = windows_to_wsl_path(network_path)
    weight_path_wsl = windows_to_wsl_path(weight_path)
    query_path_wsl = windows_to_wsl_path(query_path)

    # AalWiNes binary inside WSL
    aalwines_bin = get_aalwines_bin()
    command = f"wsl {aalwines_bin} --input {network_path_wsl} -w {weight_path_wsl} -q {query_path_wsl} --trace 1 -e 1"
    
    result = subprocess.run(command, capture_output=True, text=True, shell=True)
    
    if result.returncode == 0:
        trace_output = result.stdout
        return True, trace_output
    else:
        print(f"AalWiNes error:\n{result.stderr}")
        return False, result.stderr

def main():
    print("AalWiNes Query Generator (powered by Ollama + LLaMA 3)\n")

    model = None
    while model is None:
        model_input = input("Please specify the model to use (e.g. 'Aarnet_Gen_1.json') or 'exit':\n> ")
        if model_input.lower() == "exit":
            return
        model_path = os.path.join("networks", model_input)
        try:
            model = load_network_model(model_path)
            print(model)
        except FileNotFoundError:
            print("Error: File not found. Please try again.\n")
        except json.JSONDecodeError:
            print("Error: Invalid JSON. Please try again.\n")
        except Exception as e:
            print(f"Error: {e}. Please try again.\n")

    # Use static paths for weight + query files (adjust if needed)
    weight_path = "run/Agis-weight.json"
    query_path = "run/Agis-query.q"

    while True:
        try:
            print("\nType a description of your query (or 'exit'):")
            print("e.g. » Find a path from R0 to R3 with at most one link failure.\n")
            desc = input("> ")
            if desc.lower() == "exit":
                break

            query = regenerate_full_query_until_valid(desc, model)
            print(f"[Generated query]:\n{query}")
            MAX_RETRIES = 2
            for attempt in range(MAX_RETRIES):
                success, result = run_aalwines(query, model_path, weight_path, query_path)
                if success:
                    print(result.strip())
                    print("[✓] AalWiNes executed successfully.")
                    break

                print(f"[!] AalWiNes failed:\n{result.strip()}")

                if attempt < MAX_RETRIES - 1:
                    print("[↻] Regenerating query based on error...")
                    desc = (
                        f"Original description: {desc}\n"
                        f"Regenerate the query based on the error: {result.strip()}\n"
                    )
                    query = regenerate_full_query_until_valid(desc, model)
                    print(f"[↻] New query:\n{query}\n")
                else:
                    print("[✗] Failed after multiple attempts.")
        except Exception as e:
            print(f"[!] Error: {e}")
        except KeyboardInterrupt:
            print("\n[✗] Interrupted by user.")
            break

if __name__ == "__main__":
    main()
