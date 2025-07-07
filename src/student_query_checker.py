import json
from main import run_aalwines

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
    
def verify_semantically(student_query, reference_query, model_path, weight_path, query_path):
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