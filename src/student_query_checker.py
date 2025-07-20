import json
from main import run_aalwines
from pyformlang.regular_expression import Regex
from prompt_builder import extract_parts
import re

def extract_core_trace(output_str):
    """
    Extract simplified core trace from the AalWiNes output JSON string.
    Assumes 'trace' is part of the output and returns key features for comparison.
    """
    try:
        result = json.loads(output_str)
        trace = result.get("answers", {}).get("Q1", {}).get("trace", [])
        if not trace:
            return None

        # Extract router traversal (excluding NULL)
        routers = [step.get("from_router") for step in trace if "from_router" in step and step["from_router"] != "NULL"]
        routers += [trace[-1].get("to_router")] if trace[-1].get("to_router") not in ["NULL", None] else []

        # Stack at beginning and end
        stack_start = trace[0].get("stack", [])
        stack_end = trace[-1].get("stack", [])

        return {
            "routers": routers,
            "stack_start": stack_start,
            "stack_end": stack_end,
            "num_hops": len(routers) - 1
        }
    except Exception:
        return None
    
def verify_trace(student_query, reference_query, model_path, weight_path, query_path):
    success_s, result_s = run_aalwines(student_query, model_path, weight_path, query_path)
    success_r, result_r = run_aalwines(reference_query, model_path, weight_path, query_path)
    
    if not (success_s and success_r):
        return False, result_s, result_r

    core_s = extract_core_trace(result_s)
    core_r = extract_core_trace(result_r)

    print(f"{result_s}")
    print(f"{result_r}")

    print(f"Core S: {core_s}")
    print(f"Core R: {core_r}")



    if not core_s or not core_r:
        return False, result_s, result_r

    return core_s == core_r, result_s, result_r

def is_structurally_valid(student_query: str, task: dict) -> bool:
    must_contain = task.get("must_contain", [])
    must_contain_any = task.get("must_contain_any", [])

    for required in must_contain:
        if required not in student_query:
            print(f"Missing required: '{required}'")
            return False

    for group in must_contain_any:
        if not any(variant in student_query for variant in group):
            print(f"Missing one of required group: {group}")
            return False

    return True

def are_queries_equivalent(query1: str, query2: str) -> bool:

    start1, path1, end1, k1 = extract_parts(query1)
    start2, path2, end2, k2 = extract_parts(query2)

    if k1 != k2:
        return False

    def to_nfa(regex_str):
        try:
            normalized = normalize_aalwines_regex(regex_str)
            return Regex(normalized).to_epsilon_nfa()
        except Exception as e:
            print(f"Error when parsing '{regex_str}': {e}")
            return None

    start_nfa1 = to_nfa(start1)
    start_nfa2 = to_nfa(start2)
    path_nfa1 = to_nfa(path1)
    path_nfa2 = to_nfa(path2)
    end_nfa1 = to_nfa(end1)
    end_nfa2 = to_nfa(end2)

    if any(x is None for x in [start_nfa1, start_nfa2, path_nfa1, path_nfa2, end_nfa1, end_nfa2]):
        return False

    return (
        start_nfa1.is_equivalent_to(start_nfa2)
        and path_nfa1.is_equivalent_to(path_nfa2)
        and end_nfa1.is_equivalent_to(end_nfa2)
    )


def normalize_aalwines_regex(expr: str) -> str:
    expr = expr.strip()
    #expr = re.sub(r"[()]", "", expr)
    expr = re.sub(r"\.\+", "(ANY)(ANY)*", expr)
    expr = re.sub(r"\.\*", "(ANY)*", expr)
    expr = re.sub(r"\.", "(ANY)", expr)
    expr = re.sub(r"(?<!\()(?<!ANY)\.(?!\*|\+)", "ANY", expr)
    expr = re.sub(r"(?<!\w)(\w+)\+", r"\1 \1*", expr)
    expr = re.sub(r"\(([^()]+)\)\+", r"(\1) (\1)*", expr)
    

    def transform_atom_list(match):
        raw = match.group(0)
        content = match.group(1).strip()
        negated = raw.startswith("[^")
        parts = [c.strip() for c in content.split(",")]
        transformed = []
        for part in parts:
            part = part.replace("#", "_").replace(".", "DOT")
            transformed.append(part)
        inner = "|".join(transformed)
        return f"(~({inner}))" if negated else f"({inner})"

    expr = re.sub(r"\[\^([^\]]+)\]", transform_atom_list, expr)
    expr = re.sub(r"\[([^\]]+)\]", transform_atom_list, expr)

    return expr