# AalWiNes OpenAI Extension

## Overview
The AalWiNes OpenAI Extension is a tool designed to generate structured queries for the AalWiNes analysis tool using OpenAI's language model. This extension facilitates what-if analysis in MPLS (Multiprotocol Label Switching) networks by allowing users to describe their queries in natural language, which are then converted into valid AalWiNes query formats.

## Project Structure
The project is organized as follows:

### src
- **app.py**: The main entry point for the Streamlit web application. It handles user input, displays the UI, and manages the query generation and execution process.
- **main.py**: Contains the core logic for generating queries and running the AalWiNes tool. It includes functions for handling user queries and executing the analysis.
- **prompt_builder.py**: Responsible for constructing prompts for the OpenAI model and generating valid queries based on user descriptions.
- **query_formatter.py**: Validates and formats the generated queries to ensure they meet the required structure and syntax for AalWiNes.
- **rag_network.py**: Manages the embedding of examples and the search functionality using FAISS for efficient retrieval of relevant query examples.
- **network_parser.py**: Loads and parses network model files, extracting routers, links, labels, and atoms for use in query generation.

### networks
- **(sample-network-files).json**: Contains sample network model files in JSON format, which define the network structure for analysis.

### run
- **Agis-weight.json**: A JSON file containing weight configurations for the AalWiNes tool.
- **Agis-query.q**: A file where generated queries are saved for execution.

### results
- **examples.txt**: A text file containing example queries and their corresponding regex patterns.
- **usage_log.csv**: A CSV file that logs user interactions with the application, including queries generated and results obtained.
- **faiss_index.index**: The FAISS index file used for storing embeddings of example queries.
- **faiss_metadata.pkl**: A pickle file containing metadata associated with the FAISS index.

### config.json
A configuration file that stores paths and settings required for the application to run.

### requirements.txt
A file listing the Python dependencies required for the project.

### README.md
This file provides an overview and documentation for the project.

## Installation
1. Clone the repository:
   ```
   git clone <repository-url>
   cd aalwines-openai-extension
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Configure the `config.json` file with the necessary paths.
4. Create a .env file with the content of the .env.example file.
   Edit the file and paste your OpenAI API key.
   ```
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
   ```

## Usage
1. Run the application:
   ```
   streamlit run src/app.py
   ```

2. Enter your student ID and select a network model from the dropdown menu.

3. Describe your query in the text area and click "Generate & Run Query" to see the generated query and its results.

## Example Prompts
"Find a path from R0 to R3 with at most 1 link failure."
"Give me a trace from v0 to v4 avoiding v2."
"Verify if a packet with label 10 can reach v5 from v1."

Make sure to only use valid router names and labels which also appear in the chosen network model.

## Contributing
Contributions are welcome! Please feel free to submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.