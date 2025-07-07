import streamlit as st
import os
from datetime import datetime
from prompt_builder import regenerate_full_query_until_valid, generate_answer
from network_parser import load_network_model
from main import run_aalwines
import json
from student_query_checker import verify_semantically
import random
import csv
from filelock import FileLock

# --- Configuration ---
WEIGHT_PATH = "run/Agis-weight.json"
QUERY_PATH = "run/Agis-query.q"
NETWORK_DIR = "networks"
LOG_FILE = "results/usage_log.csv"
TEST_FILE = "run/tasks.json"

# --- Utility ---
def log_usage(student_id, description, query, success, result):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    safe_result = str(result).strip().replace(chr(10), " ")
    row = f'"{timestamp}","{student_id}","{description}","{query}","{success}","{safe_result}"\n'

    lock = FileLock(LOG_FILE + ".lock")
    with lock:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(row)

def log_quiz(student_id, solution, input, success, task_number, confidence=""):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = f'"{timestamp}","{student_id}","{solution}","{input}","{success}","{task_number}","{confidence}"\n'

    lock = FileLock(LOG_FILE + ".lock")
    with lock:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(row)

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
st.title("🚀 AalWiNes Query Generator Study")

if "stage" not in st.session_state:
    st.session_state.stage = 0

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
    ### Welcome to the AalWiNes Query Generator Study
                
    This study is designed to help you practice writing queries for the **AalWiNes** network verification tool.

    You will solve **10 network verification tasks** using the **AalWiNes query language**. For each task, you may:

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
    
        <.> [.#R0] . [R3#.] <.*> 1
    
    | Part          | Meaning                                        |
    | ------------- | ---------------------------------------------- |
    | `<.*>`        | Any starting label stack                       |
    | `[.#R0]`      | Entry point into the network at router Sydney1 |
    | `.*`          | Any number of hops between the routers         |
    | `[R3#.]`      | Exit point from router Perth1                  |
    | `<.*>`        | Any label stack at the end                     |
    | `1`           | At most one link failure allowed               |

                
    **Syntax Summary**
    Router paths: [RouterA#RouterB] means a link from A to B\n
    [.#Router]: any link to Router\n
    [Router#.]: any link from Router\n
    Wildcard: .* matches any path\n
    Negation: [^.#RouterX] excludes a router from the path\n
    Labels:\n
    <10> means the label is 10\n
    <.*> means any label stack (This is the default if nothing is specified in the task)\n
    Failures: The number at the end (e.g. 1) allows that many link failures\n

    **How it works:**
    1. Enter your student ID and experience level.
    2. Complete a series of tasks to practice writing queries.
    3. Select a network model for the LLM Assistant.
    4. Use the LLM assistant to generate and run queries based on your descriptions and network model.
    5. Provide feedback on your experience at the end.
    
    Let's get started! Click "Start Study" below to begin.
    """)
    
    if st.button("Start Study"):
        go_stage1()
        st.rerun()  # Refresh to show next stage



# --- Student ID ---
if st.session_state.stage == 1:
    with st.sidebar:
        if st.button("⬅️ Back", help="Back to the start page"):
            go_stage0()
            st.rerun()



    with st.form(key="user_information"):
        student_id = st.text_input("Enter your student ID:")
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
        experience_programming = st.slider("Select your experience level in programming:",min_value=1,max_value=10,value=3,format="%d")
        experience_networks = st.slider("Select your experience level with communication networks:",min_value=1,max_value=10,value=3,format="%d")
        experience_mpls = st.slider("Select your experience level with the MPLS routing technique:",min_value=1,max_value=10,value=3,format="%d")
        experience_aalwines = st.slider("Select your experience level with network verification tools like AalWiNes:",min_value=1,max_value=10,value=3,format="%d")

        submitted = st.form_submit_button("Submit & Start Quiz")

        if submitted:
            if student_id:  # Ensure valid ID
                log_usage(student_id, "User started quiz", "N/A", True, "N/A")
                st.session_state.student_id = student_id
                st.session_state.degree = degree
                st.session_state.stage = 2
                st.rerun()  # Refresh to show next stage

    # --- Network Selection ---
if st.session_state.stage == 2:

    with st.sidebar:
        if st.button("🔄 Restart Quiz", help="Restart from the trial task"):
            restart_quiz()
        if st.button("⬅️ Back", help="Back to the form page"):
            go_stage1()
            st.rerun()

    

    student_id = st.session_state.get("student_id", "")
    degree = st.session_state.get("degree", "")

    print(f"Student ID: {student_id}, Degree: {degree}")

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
                    except Exception as e:
                        st.error(f"Error getting answer: {e}")
            else:
                st.warning("Please enter a question.")

        # Display chat history
        for sender, msg in reversed(st.session_state.chat_history[-10:]):
            if sender == "You":
                st.markdown(f"**🧑‍🎓 You:** {msg}")
            else:
                st.markdown(f"**🤖 AI:** {msg}")


    if student_id and degree:

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
        
        st.markdown("## 🎯 Quiz")

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
            st.session_state.trial_task = {
                "task": "This is a trial task, take as much time as you need. The quiz starts after you get this question right: Write a query to check if V0 can communicate with V1 with no failures.",
                "solution": "<.*> [.#V0] .* [V1#.] <.*> 0",
                "model": "_DemoNet_.json"
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

        st.markdown(f"**Task {st.session_state.task_index + 1}/10:** {task['task']}")
        st.session_state.input = st.text_input("Enter the AalWiNes query:", key="user_answer")
        
        def next_task():
            user_input = st.session_state.input.strip()
            if not user_input:
                st.warning("Please enter a query before continuing.")
                return
            print(f"User input Next Task: {user_input}")
            st.session_state.pending_input = user_input
            st.session_state.awaiting_confidence = True
            st.session_state.input = None
            st.session_state.llm_generated = False

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
                print(f"User input Confidence: {user_input}")
                is_exact = user_input.strip() == task["solution"].strip()
                is_semantic = False

                if not is_exact:
                    is_semantic, result_student, result_ref = verify_semantically(
                        user_input + " DUAL",
                        task["solution"] + " DUAL",
                        task_model,
                        WEIGHT_PATH,
                        QUERY_PATH
                    )

                is_correct = is_exact or is_semantic

                # Log result
                log_quiz(
                    student_id,
                    task["solution"],
                    user_input,
                    is_correct,
                    st.session_state.task_index + 1,
                    confidence=confidence
                )

                # Feedback AFTER confidence
                if is_correct:
                    st.session_state.pending_feedback = ("success", "✅ Correct!")
                else:
                    st.session_state.pending_feedback = ("error", "❌ Incorrect.")

                # Reset
                st.session_state.awaiting_confidence = False
                st.session_state.pending_input = None

                if is_correct:
                    if st.session_state.task_index < len(test_tasks) - 1:
                        st.session_state.task_index += 1
                    else:
                        st.balloons()
                        st.success("🎓 You've completed all tasks!")
                        st.session_state.stage = 3
                st.rerun()

        current_task = st.session_state.task_index

        if not st.session_state.awaiting_confidence:
            cols = st.columns([2, 2, 2, 12])
            with cols[0]:
                st.button("Check Answer", on_click=next_task)
            with cols[1]:
                if st.session_state.joker_uses < 3:
                    if st.button("🃏 Show Solution"):
                        st.session_state.joker_uses += 1
                        st.session_state.joker_tasks.add(current_task)
                        st.rerun()
                    st.caption(f"{3 - st.session_state.joker_uses} joker(s) remaining")
                else:
                    st.caption("🃏 No jokers remaining")
            with cols[3]:
                if st.session_state.get("task_index", 0) > 0:
                    if st.button("Go one question back"):
                        st.session_state.task_index -= 1
                        st.rerun()
            with cols[2]:
                if st.button("Use LLM"):
                    try:
                        task_model = os.path.join(NETWORK_DIR, task['model'])
                        model = load_network_model(task_model)
                        llm_query = regenerate_full_query_until_valid(task['task'], model)
                        st.session_state.input = llm_query[:-5]
                        st.session_state.llm_generated = True
                    except Exception as e:
                        st.error(f"LLM generation failed: {e}")


        if current_task in st.session_state.joker_tasks:
            st.code(task["solution"], language="text")

        if st.session_state.task_index >= 0:
            st.progress((st.session_state.task_index) / len(test_tasks))

        # Show LLM Output and Accept/Reject UI
        if st.session_state.llm_generated and st.session_state.input:
            st.markdown("#### 💡 Suggested query:")
            st.code(st.session_state.input, language="text")

            col1, col2 = st.columns([1, 6])
            with col1:
                st.button("✅ Accept and Check", on_click=next_task)
            with col2:
                if st.button("❌ Reject"):
                    st.session_state.llm_query = None
                    st.session_state.llm_generated = False
                    st.rerun()

        if st.button("Finish quiz & go to feedback page", help="Go to the feedback page"):
            go_stage3()
            st.rerun()
    else:
        st.warning("Please enter your student ID and select a network to continue.")

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
            "How useful was the LLM assistant in helping you solve the tasks?",
            1, 5, 3,
            format="%d (1 = Not useful at all, 5 = Very useful)"
        )

        reliability = st.slider(
            "How reliable was the output of the LLM assistant?",
            1, 5, 3,
            format="%d (1 = Often wrong, 5 = Always correct)"
        )

        usage_bot = st.radio(
            "How often did you use the Chatbot during the quiz?",
            ["Never", "1–5 times", "More than 5 times"]
        )

        familiarity = st.radio(
            "Did you become more familiar with the AalWiNes query syntax over time?",
            ["Yes, I got used to it", "Somewhat", "Not really", "I still find it confusing"]
        )

        learning_factors = st.multiselect(
            "What helped you most in learning the syntax?",
            ["Introduction page", "LLM assistant", "LLM chatbot", "Experimenting with the tool during trial task", "Personal prior knowledge", "Other"]
        )

        struggle_points = st.text_area(
            "Was there anything specific you struggled with?"
        )

        improvement = st.text_area(
            "Do you have any suggestions for improving the tool, the study design, or the tasks?"
        )

        future_use = st.radio(
            "Would you consider using a LLM query assistant in future network tools?",
            ["Yes", "Maybe", "No"]
        )

        submitted = st.form_submit_button("Submit Feedback")
        FEEDBACK_FILE = "results/feedback.csv"
        if submitted:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            student_id = st.session_state.get("student_id", "anonymous")

            feedback_row = [
                timestamp,
                student_id,
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
                        "student_id",
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