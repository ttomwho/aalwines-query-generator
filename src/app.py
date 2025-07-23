import streamlit as st
import os
from datetime import datetime
from prompt_builder import regenerate_full_query_until_valid, generate_answer
from network_parser import load_network_model
import json
from student_query_checker import verify_trace, is_structurally_valid, are_queries_equivalent
import random
import csv
from filelock import FileLock
import uuid

# --- Configuration ---
WEIGHT_PATH = "run/Agis-weight.json"
QUERY_PATH = "run/Agis-query.q"
NETWORK_DIR = "networks"
LOG_FILE = "results/usage_log.csv"
TEST_FILE = "run/tasks.json"


def log_event(
    event_type,
    stage,
    question_number=None,
    solution=None,
    data=None,
    log_file=LOG_FILE
):
    """
    Logs an event with a unique ID, student ID, timestamp, stage, question number, and additional data.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_id = st.session_state.log_id
    row = [
        log_id,
        timestamp,
        stage,
        question_number if question_number is not None else "",
        solution if solution is not None else "",
        event_type,
        json.dumps(data, ensure_ascii=False) if data else ""
    ]
    lock = FileLock(log_file + ".lock")
    with lock:
        write_header = not os.path.exists(log_file)
        with open(log_file, "a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow([
                    "timestamp", "log_id", "stage", "question_number", "solution", "event_type", "data"
                ])
            writer.writerow(row)


def restart_quiz():
    # Only reset quiz-related session state, keep student info
    keys_to_reset = [
        "task_index", "quiz_initialized", "shuffled_tasks", "trial_task",
        "awaiting_confidence", "pending_input", "pending_feedback",
        "input", "llm_generated", "llm_query", "joker_tasks", "joker_uses",
    ]
    for key in keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state.stage = 2  # Go to quiz stage (trial task)
    st.rerun()

with open(TEST_FILE, "r", encoding="utf-8") as f:
    test_tasks = json.load(f)
# --- UI ---
st.set_page_config(page_title="AalWiNes Query Generator", layout="wide")
st.title("AalWiNes Query Generator Study")

if "stage" not in st.session_state:
    st.session_state.stage = 0

if "log_id" not in st.session_state:
    st.session_state.log_id = str(uuid.uuid4())

def go_stage3():
    st.session_state.stage = 3


def go_stage2():
    st.session_state.stage = 2
    

def go_stage1():
    st.session_state.stage = 1


def go_stage0():
    st.session_state.stage = 0

# --- Introduction ---
if st.session_state.stage == 0:
    st.markdown("""
    ### Welcome!
                
    This study is designed to help you practice writing queries for the **AalWiNes** network verification tool.

    You will solve **13 network verification tasks** using the **AalWiNes query language**. For each task, you may:

    - Write the query manually based on your understanding of the syntax, **or**
    - Use the **LLM-powered Query Generator** integrated into this app to help you.

    ---

    #### Quiz Information

    You will begin with **one trial task** to explore the interface.  
                
    Take your time and get familiar with the UI before starting the quiz.
                
    For general questions about the AalWiNes tool or the query language, you can use the **AI Chatbot** which will be available during the quiz.
    Please do not use any external AI tools during the study, as this may invalidate your results.
                
    After completing the quiz, you will be asked to provide feedback on your experience with the LLM assistant and the study design.

    ---

    #### What is AalWiNes?

    **AalWiNes** (Aalborg-Wien Network verification suite) is a tool used to verify **logical and quantitative properties** of network paths.
    To get to know more about it access the [AalWiNes documentation](https://github.com/DEIS-Tools/AalWiNes).

    It uses a **regex-like query language** to describe what-if scenarios, such as:

    > _"Can a packet starting at Router A reach Router B even if one link fails?"_

    AalWiNes uses real forwarding tables and considers:
    - MPLS label stacks
    - Link failures
    - Complex path constraints

    ---

    #### What does an AalWiNes query look like?

    Each query consists of **four parts**:
                
        <preCondition> path <postCondition> max_failures
    
    Example:
    
        <.*> [.#Router0] .* [Router3#.] <.*> 1
    
    | Query part    | Part               | Meaning                                        |
    | ------------- | ------------------ | ---------------------------------------------- |
    | preCondition  | `<.*>`             | Any starting label stack                       |
    | path          | `[.#Router0]`      | Entry point into the network at router Sydney1 |
    | path          | `.*`               | Any number of hops between the routers         |
    | path          | `[Router3#.]`      | Exit point from router Perth1                  |
    | postCondition | `<.*>`             | Any label stack at the end                     |
    | max_failures  | `1`                | At most one link failure allowed               |

                
    **Syntax Summary**\n
    Paths:\n
    [RouterA#RouterB]: means a link/hop from A to B\n
    [.#Router]: any link to Router\n
    [Router#.]: any link from Router\n
    **.** : matches any router, label or hop. \n
    *****: zero or more of the previous element\n
    **+**: one or more of the previous element\n
    **^**: negation e.g. [^.#RouterX] excludes router X from the path\n
    Labels:\n
    <10>: means the label is 10\n
    <.*>: means any label stack **(Important: This is the default if nothing is specified in the task)**\n
    Failures: The number at the end (e.g. 1) allows that many link failures\n

    **How it works:**
    1. Answer a short form and enter your experience level.
    2. Quiz: Complete a series of 13 tasks to practice writing queries.
    3. Optionally use the LLM assistant to generate the queries.
    4. Provide feedback on your experience using the LLM assisstant at the end.
    
    Let's get started! Click "Start Study" below to begin.
    """)
    
    st.markdown(f"""
    ### Get Your Extra Points

    To receive your bonus points, **please copy the following ID** and submit it in the [ISIS course form](https://isis.tu-berlin.de):

    """)

    st.code(st.session_state.log_id, language="text")

    if st.button("Start Study"):
        go_stage1()
        st.rerun()  # Refresh to show next stage



# --- Student ID ---
if st.session_state.stage == 1:
    with st.sidebar:
        if st.button("⬅️ Back to start", help="Back to the start page"):
            go_stage0()
            st.rerun()



    with st.form(key="user_information"):
        degree = st.selectbox("Select your degree:", 
                                    ["Bachelor", "Master"])
        semester = st.selectbox(
        "Which semester are you currently in?",
        ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th or higher"]
        )   

        likert_options = [
            "Never",
            "Less than once a week",
            "At least once a week",
            "At least once a day",
            "Multiple times a day",
            "I use them all the time"
        ]

        experience_llms = st.radio("How often do you use LLMs like ChatGPT in your life?", likert_options)
        experience_programming = st.slider(
            "Programming experience:",
            min_value=0,
            max_value=3,
            value=1,
            format="%d",
            help="0 = No knowledge, 1 = Beginner, 2 = Intermediate, 3 = Advanced"
        )
        experience_networks = st.slider(
            "Experience with communication networks:",
            min_value=0,
            max_value=3,
            value=1,
            format="%d",
            help="0 = No knowledge, 1 = Beginner, 2 = Intermediate, 3 = Advanced"
        )
        experience_mpls = st.slider(
            "Experience with MPLS routing technique:",
            min_value=0,
            max_value=3,
            value=1,
            format="%d",
            help="0 = No knowledge, 1 = Beginner, 2 = Intermediate, 3 = Advanced"
        )
        experience_aalwines = st.slider(
            "Experience with network verification tools like AalWiNes:",
            min_value=0,
            max_value=3,
            value=1,
            format="%d",
            help="0 = No knowledge, 1 = Beginner, 2 = Intermediate, 3 = Advanced"
        )

        submitted = st.form_submit_button("Submit & Start Quiz")

        if submitted:
            if st.session_state.log_id:  # Ensure valid ID
                log_event(
                    event_type="form_submit",
                    stage="form",
                    data={
                        "degree": degree,
                        "semester": semester,
                        "experience_llms": experience_llms,
                        "experience_programming": experience_programming,
                        "experience_networks": experience_networks,
                        "experience_mpls": experience_mpls,
                        "experience_aalwines": experience_aalwines
                    }
                )
                st.session_state.degree = degree
                st.session_state.stage = 2
                st.rerun()  # Refresh to show next stage

    # --- Network Selection ---
if st.session_state.stage == 2:

    with st.sidebar:
        if st.button("🔄 Restart Quiz", help="Restart from the trial task"):
            restart_quiz()
        if st.button("⬅️ Back to start", help="Back to the form page"):
            go_stage1()
            st.rerun()

    

    log_id = st.session_state.get("log_id", "")
    degree = st.session_state.get("degree", "")

    print(f"ID: {log_id}, Degree: {degree}")

    st.markdown("---")
    with st.expander("💬 Need Help? Ask the AI Chatbot about AalWiNes or MPLS"):
        st.markdown("Ask any question related to the query language, MPLS concepts, or how AalWiNes works.")

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        user_input = st.text_input("Your question:", key="chat_input")

        if st.button("Ask", key="ask_button"):
            if user_input.strip():
                with st.spinner("Thinking..."):
                    try:
                        response = generate_answer(user_input)
                        st.session_state.chat_history.append(("You", user_input))
                        st.session_state.chat_history.append(("AI", response))
                        log_event(
                            event_type="llm_chat",
                            stage="quiz",
                            data={
                                "question": user_input,
                                "response": response
                            }
                        )
                    except Exception as e:
                        st.error(f"Error getting answer: {e}")
            else:
                st.warning("Please enter a question.")
        
        # Display chat history
        for sender, msg in reversed(st.session_state.chat_history[-10:]):
            if sender == "You":
                st.markdown(f"**🧑 You:** {msg}")
            else:
                st.markdown(f"**🤖 AI:** {msg}")


    if st.session_state.log_id and degree:

        if "awaiting_confidence" not in st.session_state:
            st.session_state.awaiting_confidence = False
        
        if "pending_input" not in st.session_state:
            st.session_state.pending_input = ""

        if "pending_feedback" not in st.session_state:
            st.session_state.pending_feedback = None
        
        if "input" not in st.session_state:
            st.session_state.input = None

        if "llm_generated" not in st.session_state:
            st.session_state.llm_generated = False
        
        st.markdown("## Quiz")

        if st.session_state.pending_feedback:
            level, msg = st.session_state.pending_feedback
            if level == "success":
                st.success(msg)
            elif level == "error":
                st.error(msg)
            st.session_state.pending_feedback = None

        if "task_index" not in st.session_state:
            st.session_state.task_index = 0

        if "joker_tasks" not in st.session_state:
            st.session_state.joker_tasks = set()

        if "joker_uses" not in st.session_state:
            st.session_state.joker_uses = 0
        
        if "quiz_initialized" not in st.session_state:
            log_event(
                event_type="quiz_started",
                stage="quiz"
            )
            st.session_state.trial_task = {
                "task": "This is a trial task, take as much time as you need. The quiz starts after you get this question right: Write a query to check if V0 can communicate with V1 with no failures.",
                "solution": "<.*> [.#V0] .* [V1#.] <.*> 0",
                "other_solutions": [],
                "model": "_DemoNet_.json",
                "must_contain": ["V0", "V1", "<.*>", "0"],
                "must_not_contain": [],
                "must_contain_any": [],
            }
            # Shuffle quiz tasks once for this student
            st.session_state.shuffled_tasks = random.sample(test_tasks, len(test_tasks))
            st.session_state.task_index = -1  # -1 means: trial task
            st.session_state.quiz_initialized = True


        # Determine whether we are on the trial or real tasks
        if st.session_state.task_index == -1:
            task = st.session_state.trial_task
        else:
            task = st.session_state.shuffled_tasks[st.session_state.task_index]
        
        if st.session_state.get("change_input_flag", False):
            st.session_state.input = st.session_state.input_2
            st.session_state.change_input_flag = False

        


        st.markdown(f"**Task {st.session_state.task_index + 1}/13:** {task['task']}")
        if task["model"] != "":
            st.markdown(
                f"""
                <div style='margin-left: 72px; font-size: 0.9em; margin-top: -15px; margin-bottom: 16px;'>
                -> This task is based on this network model: <b>{task['model'][:-5]}</b>.
                You can find it in the <a href='https://demo.aalwines.cs.aau.dk/' target='_blank'>AalWiNes Demo</a> to visualize the network and get results for your queries.
                </div>
                """,
                unsafe_allow_html=True
            )
        user_query = st.text_input("Enter the AalWiNes query: \n(You may do this yourself, use the LLM assisstant or use one of your three jokers)", key="input")
        
        def next_task():
            user_input = st.session_state.input
            if not user_input:
                st.warning("Please enter a query before continuing.")
                return
            log_event(
                event_type="query_entered",
                stage="quiz",
                question_number=st.session_state.task_index + 1,
                solution=task["solution"],
                data={"query": user_input}
            )
            st.session_state.pending_input = user_input
            st.session_state.awaiting_confidence = True
            st.session_state.llm_generated = False

        if st.session_state.get("check_llm", False):
            next_task()
            st.session_state.check_llm = False

        if st.session_state.awaiting_confidence:
            st.markdown("### 🤔 How confident are you in your answer?")
            confidence = st.radio(
                "Please select your confidence level:",
                ["Not confident", "Somewhat confident", "Very confident"],
                key=f"confidence_{st.session_state.task_index}"
            )

            if st.button("Submit Confidence"):
                user_input = st.session_state.pending_input
                task_model = os.path.join(NETWORK_DIR, task['model'])
                is_match = False
                print(f"User input Confidence: {user_input}")
                is_exact = user_input.strip() == task["solution"].strip()
                for t in task["other_solutions"]:
                    is_match = user_input.strip() in [s.strip() for group in task.get("other_solutions", []) for s in group]
                is_trace = False

            

                if not is_exact or is_match:
                    is_trace, result_student, result_ref = verify_trace(
                        user_input + " DUAL",
                        task["solution"] + " DUAL",
                        task_model,
                        WEIGHT_PATH,
                        QUERY_PATH
                    )

                structure_ok = is_structurally_valid(user_input, task)
                equivalent_check = are_queries_equivalent(user_input, task["solution"])

                is_semantic = (is_trace and structure_ok) or equivalent_check

                is_correct = is_exact or is_match or is_semantic

                if not is_correct:
                    for group in task.get("other_solutions", []):
                        for t in group:
                            print(f"Checking against other solution: {t}")
                            equivalent_check = are_queries_equivalent(user_input, t)

                is_semantic = (is_trace and structure_ok) or equivalent_check
                is_correct = is_exact or is_match or is_semantic

                print(f"Exact match: {is_exact} and {is_match}, Trace match: {is_trace}, must_haves: {structure_ok}, Equivalent: {equivalent_check}, is_semantic: {is_semantic}, is_correct: {is_correct}")

                # Log result
                log_event(
                    event_type="answer_checked",
                    stage="quiz",
                    question_number=st.session_state.task_index + 1,
                    solution=task["solution"],
                    data={
                        "query": user_input,
                        "is_correct": is_correct,
                        "is_exact": is_exact,
                        "is_semantic": is_semantic,
                        "confidence": confidence
                    }
                )

                # Feedback AFTER confidence
                if is_correct:
                    st.session_state.pending_feedback = ("success", "✅ Correct! Next task.")
                    st.session_state.change_input_flag = True
                    st.session_state.input_2 = ""
                else:
                    st.session_state.pending_feedback = ("error", "❌ Incorrect. Try again.")

                # Reset
                st.session_state.awaiting_confidence = False
                st.session_state.pending_input = None

                if is_correct:
                    if st.session_state.task_index < len(test_tasks) - 1:
                        st.session_state.task_index += 1
                        st.session_state.change_input_flag = True
                        st.session_state.input_2 = ""
                    else:
                        st.balloons()
                        st.success("You've completed all tasks!")
                        st.session_state.stage = 3
                st.rerun()

        current_task = st.session_state.task_index

        if not st.session_state.awaiting_confidence:
            cols = st.columns([2, 2, 2, 2, 12])
            with cols[0]:
                st.button("Check Answer", on_click=next_task)
            with cols[1]:
                if st.session_state.joker_uses < 3:
                    if st.button("Show Solution"):
                        if current_task != -1:
                            st.session_state.joker_uses += 1
                        st.session_state.joker_tasks.add(current_task)
                        log_event(
                            event_type="joker_used",
                            stage="quiz",
                            question_number=st.session_state.task_index + 1,
                            data={"solution": task["solution"]}
                        )
                        st.rerun()
                    st.caption(f"{3 - st.session_state.joker_uses} joker(s) remaining")
                else:
                    st.caption("No jokers remaining")
            with cols[3]:
                if st.session_state.get("task_index", 0) > 0:
                    if st.button("Go one question back"):
                        st.session_state.task_index -= 1
                        st.rerun()
            with cols[4]:
                if st.session_state.get("task_index", 0) > -1:
                    if st.button("Skip question"):
                        st.session_state.task_index += 1
                        st.rerun()
            with cols[2]:
                if st.button("Use LLM"):
                    try:
                        task_model = os.path.join(NETWORK_DIR, task['model'])
                        model = load_network_model(task_model)
                        llm_query = regenerate_full_query_until_valid(task['task'], model)
                        st.session_state.llm_suggestion = llm_query[:-5]
                        st.session_state.llm_generated = True
                    except Exception as e:
                        st.error(f"LLM generation failed: {e}")


        if current_task in st.session_state.joker_tasks:
            st.code(task["solution"], language="text")

        if st.session_state.task_index >= 0:
            st.progress((st.session_state.task_index) / len(test_tasks))

        def accept_llm_and_check():
            log_event(
                    event_type="llm_accepted",
                    stage="quiz",
                    question_number=st.session_state.task_index + 1,
                    data={"llm_suggestion": st.session_state.llm_suggestion}
                )
            st.session_state.input_2 = st.session_state.llm_suggestion
            st.session_state.change_input_flag = True
            st.session_state.check_llm = True

        # Show LLM Output and Accept/Reject UI
        if st.session_state.llm_generated and st.session_state.llm_suggestion:
            st.markdown("#### AI suggested query:")
            st.code(st.session_state.llm_suggestion, language="text")

            log_event(
                event_type="llm_suggested",
                stage="quiz",
                question_number=st.session_state.task_index + 1,
                data={"llm_suggestion": st.session_state.llm_suggestion}
            )

            col1, col2 = st.columns([1, 6])
            with col1:
                st.button("✅ Accept and Check LLM output", on_click=accept_llm_and_check)
                
            with col2:
                if st.button("❌ Reject"):
                    log_event(
                        event_type="llm_rejected",
                        stage="quiz",
                        question_number=st.session_state.task_index + 1,
                        data={"llm_suggestion": st.session_state.input}
                    )
                    st.session_state.llm_query = None
                    st.session_state.llm_generated = False
                    st.rerun()

        if st.button("Finish quiz & go to feedback page", help="Go to the feedback page"):
            go_stage3()
            st.rerun()
    else:
        st.warning("Please enter a degree to continue.")

if st.session_state.stage == 3:
    with st.sidebar:
        if st.button("⬅️ Back", help="Back to the quiz page"):
                go_stage2()
                st.rerun()


    st.markdown("## Thank you for participating!")
    st.markdown("Your responses have been recorded. If you have any questions, please contact the instructor.")
    st.markdown("Thank you for completing the query tasks! Please take a moment to share your experience. Your feedback helps us improve future versions of this study and the tool.")
   
    with st.form("feedback_form"):
        usage = st.radio(
            "How often did you use the LLM assistant during the quiz?",
            ["Never", "1–2 times", "3–5 times", "Almost every task", "For all tasks"]
        )

        usefulness = st.slider(
            "How useful was the LLM assistant in speeding up your work to solve the tasks?",
            1, 5, 3,
            format="%d (1 = Not useful at all, 5 = Very useful)"
        )

        reliability = st.slider(
            "How reliable was the output of the LLM assistant?",
            1, 5, 3,
            format="%d (1 = Often wrong, 5 = Always correct)"
        )

        usage_bot = st.radio(
            "How often did you use the AI Chatbot during the quiz?",
            ["Never", "1–5 times", "More than 5 times"]
        )

        familiarity = st.radio(
            "Did you become more familiar with the AalWiNes query syntax over time?",
            ["Yes, a lot", "Yes, a little bit", "Not at all"]
        )

        learning_factors = st.multiselect(
            "What helped you most in learning the syntax?",
            ["Introduction page", "LLM assistant", "AI Chatbot", "Experimenting with the tool during trial task", "Personal prior knowledge", "Other"]
        )

        struggle_points = st.text_area(
            "Was there anything specific you struggled with?"
        )

        improvement = st.text_area(
            "Do you have any suggestions for improving the tool, the study design, or the tasks?"
        )

        future_use = st.radio(
            "Would you consider using a LLM query assistant in other network tools?",
            ["Yes", "Maybe", "No"]
        )

        submitted = st.form_submit_button("Submit Feedback")
        FEEDBACK_FILE = "results/feedback.csv"
        if submitted:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            feedback_row = [
                timestamp,
                usage,
                usefulness,
                reliability,
                familiarity,
                "; ".join(learning_factors),
                struggle_points,
                improvement,
                future_use
            ]

            # Ensure directory exists
            os.makedirs(os.path.dirname(FEEDBACK_FILE), exist_ok=True)

            # Write header if file doesn't exist yet
            write_header = not os.path.exists(FEEDBACK_FILE)

            with open(FEEDBACK_FILE, "a", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                if write_header:
                    writer.writerow([
                        "timestamp",
                        "llm_usage",
                        "llm_usefulness",
                        "llm_reliability",
                        "familiarity_with_syntax",
                        "learning_helpers",
                        "struggle_points",
                        "improvement_suggestions",
                        "would_use_in_future"
                    ])
                writer.writerow(feedback_row)
            st.success("Thank you for your feedback! 🎉")
    st.stop()