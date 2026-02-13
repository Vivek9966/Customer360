# 🏠 CUSTOMER 360
Home Maintenance Assistant (Local AI Agent)

A **local, stateful AI support agent** for home maintenance issues, built with **Streamlit + Ollama + LangChain tools**.

This project demonstrates how to design a **realistic customer-support AI system** with:
- conversational memory
- fact tracking
- sentiment-aware responses
- safety-first escalation
- real JSON-based data persistence

> ⚠️ The assistant is intentionally **restricted to home maintenance topics only** to ensure safety and prevent hallucinations.

---

## 🚀 Key Features

### 🧠 Conversational Intelligence
- Maintains **multi-turn conversation memory**
- Remembers confirmed facts (room, issue type, location, etc.)
- Avoids repeating already-answered questions

### 📊 Automatic Fact Extraction
- Extracts structured facts from user messages
- Stores them explicitly (no implicit guessing)
- Reuses facts naturally in later responses

### 😌 Sentiment-Aware Responses
- Detects **calm / anxious / frustrated / urgent** tones
- Adjusts response style accordingly
- Prioritizes empathy and safety for distressed users

### 🚨 Smart Escalation System
- Detects:
  - safety-critical issues
  - repeated frustration
  - stalled conversations
- Recommends escalation to a human or professional when needed

### 🧰 Tool-Driven Actions (LangChain)
- Booking technician appointments
- Logging customer issues
- Creating maintenance tickets
- Escalating to human representatives
- All data stored as **real JSON files**

### 💾 Persistent Storage
- Bookings, issues, tickets, and escalations are saved to disk
- Data survives app restarts
- Built for auditability and debugging

---

## 🧱 Architecture Overview

```text
User Input
   ↓
Domain Guard (Home Maintenance Only)
   ↓
Sentiment Detection
   ↓
Fact Extraction
   ↓
Conversation Memory
   ↓
LLM (Ollama, local)
   ↓
LangChain Tools (Bookings / Tickets / Escalation)
   ↓
JSON Persistence
```
---



Ollama – Local LLM inference
OpenAI-compatible API (local)
LangChain StructuredTools
python-dotenv – environment config
JSON – persistent storage
## 🛠️ Tech Stack
### Python
### Streamlit – UI
### Ollama – Local LLM inference
### Ollama – Local LLM inference

## 🧱 Project Structure
.
├── main.py                     # Streamlit app
├── memory.py                   # Conversation, escalation & follow-up logic
├── langchain_tools.py          # Tool definitions + JSON persistence
├── prompts/
│   ├── system_prompt.txt       # Assistant behavior rules
│   └── fact_extraction.txt     # Fact extraction prompt
├── maintenance_data/           # Auto-generated JSON storage
│   ├── bookings.json
│   ├── issues.json
│   ├── tickets.json
│   └── escalations.json
├── .env.example                # Environment variable template
├── .gitignore
├── requirements.txt
└── README.md



