
import streamlit as st
import json
from openai import OpenAI
from memory import ConversationManager, EscalationDetector, FollowUpTracker
import langchain_tools
from dotenv import load_dotenv
import os

load_dotenv()
model_choice = os.getenv("DEFAULT_MODEL")


def load_prompt(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
    

st.set_page_config(
    page_title="Home Maintenance Assistant",
    page_icon="",
    layout="centered"
)

st.title("Home Maintenance Assistant")
TOOL_CAPABLE_MODELS = set(os.getenv("TOOL_CAPABLE_MODELS", "").split(","))
with st.sidebar:
    
    if "conversation" in st.session_state:
        st.divider()
        st.header("Conversation Stats")
        
        conv = st.session_state.conversation
        st.metric("User Messages", conv.get_turn_count())
        st.metric("Tool Calls", conv.get_tool_call_count())
 
        if conv.get_all_facts():
            st.divider()
            st.header(" Confirmed Facts")
            facts = conv.get_all_facts()
            for key, value in facts.items():
                st.text(f"• {key}: {value}")
        if "followup_tracker" in st.session_state:
            tracker = st.session_state.followup_tracker
            unanswered = tracker.get_unanswered_count()
            if unanswered > 0:
                st.divider()
                st.warning(f"⏳ {unanswered} question(s) awaiting response")
    st.divider()
    st.header("Data Management")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("View Data", use_container_width=True):
            st.session_state.show_data_viewer = True
    
    with col2:
        if st.button("Clear Data", use_container_width=True):
            langchain_tools.clear_all_data()
            st.success("All data cleared!")
            st.rerun()
    
   
    bookings = langchain_tools.get_all_bookings()
    issues = langchain_tools.get_all_issues()
    tickets = langchain_tools.get_all_tickets()
    escalations = langchain_tools.get_all_escalations()
    
    st.text(f"Bookings: {len(bookings)}")
    st.text(f"Issues: {len(issues)}")
    st.text(f"Tickets: {len(tickets)}")
    st.text(f"Escalations: {len(escalations)}")
 
    st.divider()
    if st.button("New Conversation", use_container_width=True):

        for key in list(st.session_state.keys()):
            if key not in ['show_data_viewer']:
                del st.session_state[key]
        st.rerun()
if st.session_state.get('show_data_viewer', False):
    with st.expander("Stored Data Viewer", expanded=True):
        tab1, tab2, tab3, tab4 = st.tabs(["Bookings", "Issues", "Tickets", "Escalations"])
        
        with tab1:
            bookings = langchain_tools.get_all_bookings()
            if bookings:
                st.json(bookings)
            else:
                st.info("No bookings yet")
        
        with tab2:
            issues = langchain_tools.get_all_issues()
            if issues:
                st.json(issues)
            else:
                st.info("No issues logged yet")
        
        with tab3:
            tickets = langchain_tools.get_all_tickets()
            if tickets:
                st.json(tickets)
            else:
                st.info("No tickets created yet")
        
        with tab4:
            escalations = langchain_tools.get_all_escalations()
            if escalations:
                st.json(escalations)
            else:
                st.info("No escalations yet")
        
        if st.button("Close Viewer"):
            st.session_state.show_data_viewer = False
            st.rerun()

SYSTEM_PROMPT = load_prompt(os.getenv("SYSTEM_PROMPT_PATH"))


def extract_facts(client, model, user_message):
    FACT_EXTRACTION_PROMPT = load_prompt(os.getenv("FACT_PROMPT_PATH"))
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": FACT_EXTRACTION_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0
        )
        
        content = response.choices[0].message.content.strip()
        return json.loads(content)
    except Exception as e:
        return {}


def detect_sentiment(message: str) -> dict:
    frustrated_words = [
        "angry", "frustrated", "terrible", "worst", "useless",
        "ridiculous", "annoyed", "fed up", "disappointed"
    ]

    anxious_words = [
        "worried", "anxious", "scared", "afraid", "nervous",
        "concerned", "not sure", "uncertain", "don't know"
    ]

    urgent_words = [
        "urgent", "emergency", "asap", "immediately", "now",
        "right now", "help", "serious", "critical", "danger"
    ]

    text = message.lower()

    is_frustrated = any(w in text for w in frustrated_words)
    is_anxious = any(w in text for w in anxious_words)
    is_urgent = any(w in text for w in urgent_words)

    if is_urgent:
        tone = "urgent"
    elif is_frustrated:
        tone = "frustrated"
    elif is_anxious:
        tone = "anxious"
    else:
        tone = "calm"

    return {
        "tone": tone,
        "is_frustrated": is_frustrated,
        "is_anxious": is_anxious,
        "is_urgent": is_urgent
    }


def get_sentiment_instruction(sentiment: dict) -> str:
    if sentiment["tone"] == "frustrated":
        return """TONE ADJUSTMENT: User is frustrated.
- Acknowledge their frustration explicitly
- Be extra patient and empathetic
- Keep sentences short and reassuring
- Consider offering human help if frustration continues
- Focus on immediate helpful actions"""

    if sentiment["tone"] == "anxious":
        return """TONE ADJUSTMENT: User is anxious/worried.
- Provide calm reassurance without false promises
- Explain steps slowly and clearly
- Emphasize what they can control
- Highlight safety measures"""

    if sentiment["tone"] == "urgent":
        return """TONE ADJUSTMENT: User indicates urgency.
- Prioritize immediate safety advice FIRST
- Be direct and concise
- Create tickets for urgent issues
- Avoid unnecessary questions unless critical
- Provide clear action steps"""

    return """TONE ADJUSTMENT: User appears calm.
- Proceed with normal professional guidance
- Maintain friendly, helpful demeanor"""


def build_context_with_facts(conversation: ConversationManager, sentiment_guidance: str = None):
    """Build message context with facts and sentiment injected appropriately"""
    messages = conversation.get_context().copy()

    facts_summary = conversation.get_facts_summary()
    if facts_summary:
        messages.insert(1, {
            "role": "system",
            "content": facts_summary
        })

    if sentiment_guidance:
        messages.insert(1, {
            "role": "system",
            "content": sentiment_guidance
        })
    
    return messages


def display_escalation_alert(should_escalate: bool, reasons: list, severity: str, detector: EscalationDetector):
    """Display escalation warning to user"""
    if not should_escalate:
        return
    
    if severity == "critical":
        alert_type = st.error
        icon = "!!!ERROR!!!"
    elif severity == "high":
        alert_type = st.warning
        icon = "!!!WARNING!!!"
    else:
        alert_type = st.info
        icon = "!!!NOTICE!!!"
    
    with alert_type(icon=icon):
        st.subheader("Professional Assistance Recommended")
        
        for reason in reasons:
            st.write(reason)
        
        st.divider()
        st.write(detector.get_escalation_message(severity))
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Connect to Specialist", use_container_width=True, key="escalate_btn"):
                st.success("Initiating connection to specialist...")
                # trigger actual escalation
        
        with col2:
            if st.button("Continue Conversation", use_container_width=True, key="continue_btn"):
                st.info("Continuing conversation. Type your next message below.")



if "conversation" not in st.session_state:
    st.session_state.conversation = ConversationManager(SYSTEM_PROMPT)

if "escalation_detector" not in st.session_state:
    st.session_state.escalation_detector = EscalationDetector()

if "followup_tracker" not in st.session_state:
    st.session_state.followup_tracker = FollowUpTracker()

if "last_sentiment" not in st.session_state:
    st.session_state.last_sentiment = {"tone": "calm"}

conversation = st.session_state.conversation
escalation_detector = st.session_state.escalation_detector
followup_tracker = st.session_state.followup_tracker


for msg in conversation.get_context():
    if msg["role"] in ("user", "assistant"):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

critical_safety = len([t for t in langchain_tools.get_all_tickets() if t.get("severity") in ["high", "critical"]]) > 0
should_escalate, reasons, severity = escalation_detector.should_escalate(
    conversation, 
    st.session_state.last_sentiment,
    critical_safety
)

if should_escalate:
    display_escalation_alert(should_escalate, reasons, severity, escalation_detector)

if prompt := st.chat_input("Describe the issue you're facing..."):
    conversation.add("user", prompt)

    with st.chat_message("user"):
        st.markdown(prompt)

    client = OpenAI(
        base_url=os.getenv("OLLAMA_BASE_URL"),
        api_key=os.getenv("OLLAMA_API_KEY")
    )

    sentiment = detect_sentiment(prompt)
    st.session_state.last_sentiment = sentiment
    tone_guidance = get_sentiment_instruction(sentiment)

    with st.spinner("Analyzing message..."):
        extracted_facts = extract_facts(client, model_choice, prompt)
        for key, value in extracted_facts.items():
            conversation.set_fact(key, value)
    answered_questions = followup_tracker.check_if_answered(prompt)
    if answered_questions:
        with st.sidebar:
            st.success(f"Answered {len(answered_questions)} question(s)")

    with st.chat_message("assistant"):
        placeholder = st.empty()

        messages = build_context_with_facts(conversation, tone_guidance)

        request_args = {
            "model":os.getenv("DEFAULT_MODEL"),
            "messages": messages,
        }

        if model_choice in TOOL_CAPABLE_MODELS:
            request_args["tools"] = langchain_tools.langchain_tools_schema
            request_args["tool_choice"] = "auto"

        with st.spinner("Thinking..."):
            response = client.chat.completions.create(**request_args)
        
        msg = response.choices[0].message
        tool_calls = getattr(msg, "tool_calls", None)

        if tool_calls:
            if msg.content:
                conversation.add("assistant", msg.content)
                placeholder.markdown(msg.content)

            for tc in tool_calls:
                fn_name = tc.function.name
                fn_args = json.loads(tc.function.arguments)

                with st.status(f"Executing {fn_name}...", expanded=False) as status:
                    st.write(f"Arguments: {fn_args}")

                    fn = langchain_tools.available_langchain_functions.get(fn_name)
                    if fn:
                        try:
                            result = fn.invoke(fn_args)
                        except:
                            result = fn(**fn_args)
                        result_data = json.loads(result)

                        st.write(f"Result: {result_data.get('message', result_data.get('status', 'Done'))}")
                        status.update(label=f"{fn_name} completed", state="complete")
                    else:
                        result = json.dumps({"error": "Tool unavailable"})
                        st.error("Tool not found!")

                conversation.add_tool(
                    tool_call_id=tc.id,
                    name=fn_name,
                    content=result
                )

            messages = build_context_with_facts(conversation, tone_guidance)
            
            with st.spinner("Processing results..."):
                final_response = client.chat.completions.create(
                    model=model_choice,
                    messages=messages,
                )

            final_text = final_response.choices[0].message.content
            conversation.add("assistant", final_text)

            if msg.content:
                placeholder.markdown(msg.content + "\n\n" + final_text)
            else:
                placeholder.markdown(final_text)

        else:
   
            final_text = msg.content
            conversation.add("assistant", final_text)
            placeholder.markdown(final_text)


        followup_tracker.add_ai_response(final_text)


    critical_safety = len([t for t in langchain_tools.get_all_tickets() if t.get("severity") in ["high", "critical"]]) > 0
    should_escalate, reasons, severity = escalation_detector.should_escalate(
        conversation, 
        sentiment,
        critical_safety
    )

    if should_escalate:
        st.divider()
        display_escalation_alert(should_escalate, reasons, severity, escalation_detector)

st.divider()
