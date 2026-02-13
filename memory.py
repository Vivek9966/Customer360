

class ConversationManager:

    
    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt
        self.messages = [{"role": "system", "content": system_prompt}]
        self.facts = {}  
        self.turn_count = 0
        self.tool_call_count = 0
        
    def add(self, role: str, content: str):
        """Add a message to conversation history"""
        if content:
            self.messages.append({"role": role, "content": content})
            if role == "user":
                self.turn_count += 1
    
    def add_tool(self, tool_call_id: str, name: str, content: str):
        """Add a tool call result"""
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name,
            "content": content
        })
        self.tool_call_count += 1
    
    def set_fact(self, key: str, value: str):
      
        if value and value.strip():
            self.facts[key] = value
    
    def get_fact(self, key: str):
      
        return self.facts.get(key)
    
    def get_all_facts(self):
  
        return self.facts.copy()
    
    def get_facts_summary(self):
     
        if not self.facts:
            return ""
        
        summary = "Confirmed Information:\n"
        for key, value in self.facts.items():
            summary += f"  • {key}: {value}\n"
        return summary.strip()
    
    def get_context(self, include_facts=False):
        """Get conversation context, optionally with facts"""
        if include_facts and self.facts:

            context = self.messages.copy()
    
            return context
        return self.messages.copy()
    
    def get_user_messages(self):

        return [msg for msg in self.messages if msg["role"] == "user"]
    
    def get_turn_count(self):

        return self.turn_count
    
    def get_tool_call_count(self):
 
        return self.tool_call_count
    
    def clear(self):
 
        self.messages = [{"role": "system", "content": self.system_prompt}]
        self.facts = {}
        self.turn_count = 0
        self.tool_call_count = 0


class EscalationDetector:

    
    def __init__(self):
        self.turn_threshold = 8
        self.frustrated_turn_threshold = 3
        self.tool_call_threshold = 5
        self.repeated_question_threshold = 2
    
    def should_escalate(self, conversation: ConversationManager, sentiment: dict, 
                        critical_safety_logged: bool = False):
        """
        Returns:
            tuple: (should_escalate: bool, reasons: list, severity: str)
        """
        reasons = []
        severity = "low"
        
        if critical_safety_logged:
            reasons.append("Critical safety issue logged - immediate expert attention required")
            severity = "critical"
            return True, reasons, severity
        
   
        if conversation.get_turn_count() >= self.turn_threshold:
            reasons.append(f"Conversation exceeds {self.turn_threshold} turns - may need expert guidance")
            severity = max(severity, "high")
     
        if sentiment.get("is_frustrated") and conversation.get_turn_count() >= self.frustrated_turn_threshold:
            reasons.append("Customer appears frustrated after multiple exchanges")
            severity = max(severity, "high")
   
        if sentiment.get("is_urgent") and conversation.get_turn_count() >= 4:
            reasons.append(" Urgent issue not resolved after several exchanges")
            severity = max(severity, "medium")
        
   
        if conversation.get_tool_call_count() >= self.tool_call_threshold:
            reasons.append(f"Complex issue requiring {conversation.get_tool_call_count()} tool calls")
            severity = max(severity, "medium")

        if self._detect_repeated_questions(conversation):
            reasons.append("User asking similar questions - AI may not be helping effectively")
            severity = max(severity, "medium")

        should_escalate = len(reasons) > 0
        
        return should_escalate, reasons, severity
    
    def _detect_repeated_questions(self, conversation: ConversationManager):
        """Detect if user is asking the same thing multiple times"""
        user_messages = conversation.get_user_messages()
        
        if len(user_messages) < 3:
            return False
        
    
        recent_messages = user_messages[-3:]

        word_sets = []
        for msg in recent_messages:
            words = set(msg["content"].lower().split())
   
            words = words - {"the", "a", "an", "is", "are", "how", "what", "when", "where", 
                            "why", "can", "could", "should", "i", "my", "me", "you"}
            word_sets.append(words)

        if len(word_sets) >= 2:
            overlap_01 = len(word_sets[0] & word_sets[1]) / max(len(word_sets[0]), 1)
            if len(word_sets) >= 3:
                overlap_12 = len(word_sets[1] & word_sets[2]) / max(len(word_sets[1]), 1)
                if overlap_01 > 0.5 or overlap_12 > 0.5:
                    return True
        
        return False
    
    def get_escalation_message(self, severity: str):

        if severity == "critical":
            return """IMMEDIATE ATTENTION REQUIRED

Based on the safety concerns identified, I strongly recommend connecting with a qualified professional immediately. 

Would you like me to help you find emergency contact information?"""
        
        elif severity == "high":
            return """Expert Consultation Recommended

I've provided general guidance, but this issue may benefit from professional assessment. A qualified technician can:
- Inspect the issue in person
- Provide accurate diagnosis
- Ensure safety and compliance

Would you like to proceed with booking a specialist?"""
        
        elif severity == "medium":
            return """Consider Professional Help

While I can provide general advice, a professional might be better suited for:
- Complex or persistent issues
- Situations requiring specialized tools
- Cases where safety is a concern

Would you like assistance finding a qualified professional?"""
        
        return ""


class FollowUpTracker:

    
    def __init__(self):
        self.pending_questions = []
        self.answered_questions = []
    
    def extract_questions(self, ai_message: str):
        """Extract questions from AI's response"""
        import re
        questions = re.findall(r'[^.!?]*\?', ai_message)
        return [q.strip() for q in questions if len(q.strip()) > 10]
    
    def add_ai_response(self, ai_message: str):
        new_questions = self.extract_questions(ai_message)
        self.pending_questions.extend(new_questions)
    
    def check_if_answered(self, user_response: str):
       
        answered = []
        user_lower = user_response.lower()
        
        for question in self.pending_questions:
            
            question_lower = question.lower()
            key_words = [w for w in question_lower.split() 
                        if w not in {"is", "are", "the", "a", "an", "when", "where", "what", "how"}]
            
           
            if any(word in user_lower for word in key_words[:3]):
                answered.append(question)
                self.answered_questions.append(question)
  
        self.pending_questions = [q for q in self.pending_questions if q not in answered]
        
        return answered
    
    def get_unanswered(self):
    
        return self.pending_questions.copy()
    
    def has_unanswered(self):

        return len(self.pending_questions) > 0
    
    def get_unanswered_count(self):

        return len(self.pending_questions)