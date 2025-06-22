import re
from query_formatter import is_valid_label, is_valid_path_format
from rag_network import embed_examples, store_embeddings_in_faiss, search
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")


client = OpenAI(api_key=api_key)

def generate_query2(description, model, feedback=""):
    prompt = build_prompt(description, model, feedback)
    response = client.chat.completions.create(
        model="gpt-4.1-mini-2025-04-14",
        messages=[
            {"role": "system", "content": "You are an assistant that generates valid AalWiNes query components."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )
    if not response.choices or not response.choices[0].message.content:
        return "Error: No response from model."
    return response.choices[0].message.content.strip()


def extract_parts(query: str):
    try:
        # Extract all <...> patterns including multiple labels inside
        label_matches = re.findall(r"<([^<>]+)>", query)
        k_matches = re.findall(r"\b\d+\b", query)

        if len(label_matches) < 2 or not k_matches:
            return None, None, None, None

        start_label = f"<{label_matches[0]}>"
        end_label = f"<{label_matches[1]}>"
        k = k_matches[-1]

        # Find everything between start_label and end_label
        start_index = query.find(start_label)
        end_index = query.find(end_label, start_index + len(start_label))
        path_expr = query[start_index + len(start_label):end_index].strip()

        return start_label, path_expr, end_label, k

    except Exception as e:
        print(f"[!] Error parsing query: {e}")
        return None, None, None, None


def regenerate_full_query_until_valid(desc, model):
    max_attempts = 3
    attempts = 0
    feedback = ""

    while attempts < max_attempts:
        query = generate_query2(desc, model, feedback)
        print(f"[Try {attempts + 1}] Generated query: {query}")

        start_label, path_expr, end_label, k = extract_parts(query)
        if not start_label or not path_expr or not end_label or not k:
            print("[!] Query is None or empty. Retrying...")
            attempts += 1
            continue
        if not all([start_label, path_expr, end_label, k]):
            print("[!] Query format incomplete. Retrying...")
            attempts += 1
            continue

        if not is_valid_label(start_label.strip('<>'), model):
            print(f"[!] Invalid start label: {start_label}")
            feedback = f"Invalid start label: {start_label}"
            attempts += 1
            continue

        if not is_valid_path_format(path_expr, model)[0]:
            print(f"This path {path_expr} is incorrect: {is_valid_path_format(path_expr, model)[1]}")
            feedback = f"This path {path_expr} is incorrect: {is_valid_path_format(path_expr, model)[1]}. Review the rules and generate a valid path.\n"
            attempts += 1
            continue

        if not is_valid_label(end_label.strip('<>'), model):
            print(f"[!] Invalid end label: {end_label}")
            feedback = f"Invalid end label: {end_label}"
            attempts += 1
            continue

        if not k.isdigit():
            print(f"[!] Invalid k: {k}")
            attempts += 1
            continue

        print(f"[✓] Valid full query after {attempts + 1} attempt(s).")
        return f"{start_label} {path_expr} {end_label} {k} DUAL"

    raise ValueError("Failed to generate a valid query.")


def build_prompt(description, model, feedback=""):
    examples = load_examples()
    chunks = ["".join(map(str, sublist)) for sublist in examples]
    embedded = embed_examples(chunks, cache_file="embeddings/examples.json", model = "text-embedding-3-small")
    store_embeddings_in_faiss(embedded)
    top_chunks = search(f"Input: {description}", k=3)
    retrieved_text = ""
    for chunk in top_chunks:
        retrieved_text += f"{chunk}\n"
    
    routers_text = ", ".join(model.routers)
    
    labels_text = ", ".join(model.labels)

    return f"""
Context: How to Generate Valid AalWiNes Queries
You are tasked with generating structured verification queries for a tool called AalWiNes. This tool performs what-if analysis in MPLS (Multiprotocol Label Switching) networks. Each query describes how packets are expected to move through a network from source to destination, possibly under link failure conditions. Accuracy in formatting and semantics is crucial. Here's what you must understand and follow:

AalWiNes Query Structure
Each query has to be in this format:

<start_label> <path_expression> <end_label> <max_link_failures>

1. <start_label> (Label regex):
Must describe the label stack before entering the network.

Only allows:
Single known labels (e.g. <500>)
These are the labels that you are allowed to use: Either the wildcard, if no label is specified <.*> or these {labels_text}
Space-separated lists of such labels (e.g. <250 10>)
Optional suffixes: *, +, ? (e.g. <68843*>, <10000?>)
Always use the wildcard <.*> if no label is specified by the user
Reject generic words like mpls, label, or invalid regex (e.g., <label> or smpls?).
If the user specifies a "top of stack label" its <label .*> if its just the label its <label> with no suffix. 

Service labels are used for passing through a network (e.g., s60 or <60>). They are typically removed before exit — use <> as the end stack to enforce this. If checking for leaks, allow the label to remain at the end (e.g., <10> or <[.+ .]>).

2. <path_expression> (Path regex):
A regex describing the routers/interfaces the packet traverses. If just a number of hops is specified, use the dot (.) to represent one wildcard hop.

Built using atom blocks like:
[.#RouterName] → enter router
[RouterName#.] → exit router
[RouterA#RouterB] → hop from A to B

Path must:
Start with [.#Router]
End with [Router#.]
Use only [.#Router] for intermediate hops
Only use the following router names if specified by the user: {routers_text}
If no router names are specified, use the dot to represent one wildcard router.
If the user input requests a number of hops (e.g., “three or more hops”), express this as ...(.)*  that is, one dot per required hop, followed by (.)* if more hops are allowed. Make sure to check the number of hops that the user asks.

You may use:
*, +, ?, |, parentheses
Negation with [^...] is allowed for blocks

3. <end_label>:
Same rules as for <start_label>.
These are the labels that you are allowed to use: Either the wildcard, if no label is specified <.*> or these {labels_text}
Reflects the label stack expected when exiting the network.

4. <max_link_failures>:
An integer (e.g., 0, 1, 3) indicating how many link failures are allowed in the analysis.
Search the user input for it. If there is no specified maximum link failure use the default of 0.


What to Avoid:
Do not invent new keywords like label, mpls, smpls.
Do not start or end the path with the wrong atom type.
Do not write raw text between brackets ([Router]) without #.
Avoid malformed regex like nested brackets, unclosed parentheses, or illegal characters.
Do not make up unknown labels or router names unless you're working with a provided list (e.g. Chicago, R6, v0, Santa_Clara).


Guidance for the AI
Use regex operators correctly: * means 0 or more hops, + means 1 or more, ? means optional.
Refer to sample router names or labels always when provided by the user.
Try to model realistic network movement: enter a router, transit through the network, exit from another.
Be consistent in formatting: always use <start_label> <path_expression> <end_label> <max_link_failures>


Use these examples to generate the AalWiNes query:
{retrieved_text}

Please generate the query and do exactly like the examples suggest just with consideration of user input.
{feedback}

Do not output anything else than the query in the format:
<start_label> <path_expression> <end_label> <max_link_failures>

Do not output any explanation, just the query.

User Input: {description}
Query:
"""



def load_examples(filepath="run/examples.txt"):
    examples = []
    with open(filepath, "r", encoding="utf-8") as f:
        current_nl = ""
        current_regex = ""
        for line in f:
            line = line.strip()
            if line.startswith("Input:"):
                current_nl = f"{line[0:].strip()} "
            elif line.startswith("REGEX:"):
                current_regex = line[0:].strip()
                examples.append((current_nl, current_regex))
                current_nl, current_regex = "", ""

    return examples
