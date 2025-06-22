import streamlit as st
import os
from datetime import datetime
from prompt_builder import regenerate_full_query_until_valid
from network_parser import load_network_model
from main import run_aalwines

# --- Configuration ---
WEIGHT_PATH = "run/Agis-weight.json"
QUERY_PATH = "run/Agis-query.q"
NETWORK_DIR = "networks"
LOG_FILE = "results/usage_log.csv"

# --- Utility ---
def log_usage(student_id, description, query, result, success):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = f'"{timestamp}","{student_id}","{description}","{query.strip()}","{success}","{result.strip().replace(chr(10), " | ")}"\n'
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(row)

# --- UI ---
st.set_page_config(page_title="AalWiNes Query Generator", layout="wide")
st.title("🚀 AalWiNes Query Generator (LLM-powered)")

# --- Student ID ---
student_id = st.text_input("Enter your student ID:")

# --- Network Selection ---
network_files = [f for f in os.listdir(NETWORK_DIR) if f.endswith(".json")]
selected_file = st.selectbox("Select a Network Model:", network_files)

if student_id and selected_file:
    try:
        model_path = os.path.join(NETWORK_DIR, selected_file)
        model = load_network_model(model_path)
    except Exception as e:
        st.error(f"Failed to load model: {e}")
        st.stop()

    # --- Query Description ---
    st.markdown("### Describe your query:")
    description = st.text_area("Example: Find a path from R0 to R3 with at most one link failure.", height=100)

    if st.button("🧠 Generate & Run Query") and description:
        with st.spinner("Generating query and running AalWiNes..."):
            try:
                query = regenerate_full_query_until_valid(description, model)
                st.code(query, language="text")

                success, result = run_aalwines(query, model_path, WEIGHT_PATH, QUERY_PATH)

                if success:
                    st.success("✅ AalWiNes executed successfully!")
                    st.text_area("Output:", result.strip(), height=300)
                else:
                    st.error("❌ AalWiNes execution failed.")
                    st.text_area("Error Output:", result.strip(), height=300)

                # Logging
                log_usage(student_id, description, query, result, success)

            except Exception as e:
                st.error(f"Unexpected error: {e}")
else:
    st.warning("Please enter your student ID and select a network to continue.")