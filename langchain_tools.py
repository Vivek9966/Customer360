from langchain.tools import tool
from langchain_core.tools import Tool
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import random

DATA_DIR = "maintenance_data"
BOOKINGS_FILE = os.path.join(DATA_DIR, "bookings.json")
ISSUES_FILE = os.path.join(DATA_DIR, "customer_issues.json")
TICKETS_FILE = os.path.join(DATA_DIR, "tickets.json")
ESCALATIONS_FILE = os.path.join(DATA_DIR, "escalations.json")

def init_storage():

    os.makedirs(DATA_DIR, exist_ok=True)

    for filepath in [BOOKINGS_FILE, ISSUES_FILE, TICKETS_FILE, ESCALATIONS_FILE]:
        if not os.path.exists(filepath):
            with open(filepath, 'w') as f:
                json.dump([], f)


init_storage()

def load_json(filepath: str) -> List[Dict]:
    """Load data from JSON file"""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_json(filepath: str, data: List[Dict]):
    """Save data to JSON file"""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

def generate_id(prefix: str) -> str:
    """Generate unique ID with prefix"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_suffix = random.randint(1000, 9999)
    return f"{prefix}-{timestamp}-{random_suffix}"

def parse_flexible_date(date_input: str) -> str:
    """
    Parse flexible date formats and convert to YYYY-MM-DD.
    Assumes current year and month when not specified.
    
    Supported formats:
    - "21" or "21st" → current year and month, day 21
    - "March 15" or "15 March" → current year, March 15
    - "2025-03-15" → exact date
    - "tomorrow" → tomorrow's date
    - "next week" → 7 days from now
    - "next month" → same day next month
    
    Args:
        date_input: Flexible date string
        
    Returns:
        Date in YYYY-MM-DD format
    """
    import re
    
    date_input = date_input.lower().strip()
    today = datetime.now()
    

    if date_input in ["today", "now"]:
        return today.strftime("%Y-%m-%d")
    
    if date_input == "tomorrow":
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")
    
    if "next week" in date_input:
        return (today + timedelta(days=7)).strftime("%Y-%m-%d")
    
    if "next month" in date_input:
   
        return (today + timedelta(days=30)).strftime("%Y-%m-%d")
    
   
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_input):
        return date_input
    
    
    day_match = re.search(r'\b(\d{1,2})(?:st|nd|rd|th)?\b', date_input)
    
 
    months = {
        'january': 1, 'jan': 1,
        'february': 2, 'feb': 2,
        'march': 3, 'mar': 3,
        'april': 4, 'apr': 4,
        'may': 5,
        'june': 6, 'jun': 6,
        'july': 7, 'jul': 7,
        'august': 8, 'aug': 8,
        'september': 9, 'sep': 9, 'sept': 9,
        'october': 10, 'oct': 10,
        'november': 11, 'nov': 11,
        'december': 12, 'dec': 12
    }
 
    month = None
    for month_name, month_num in months.items():
        if month_name in date_input:
            month = month_num
            break

    if day_match:
        day = int(day_match.group(1))
        year = today.year
        
        if month is None:
 
            month = today.month

            if day < today.day:
                month += 1
                if month > 12:
                    month = 1
                    year += 1
        else:
        
            if month < today.month or (month == today.month and day < today.day):
                year += 1
        
        try:
            parsed_date = datetime(year, month, day)
            return parsed_date.strftime("%Y-%m-%d")
        except ValueError:
          
            raise ValueError(f"Invalid date: day {day} doesn't exist in month {month}")
    

    raise ValueError(f"Could not parse date: '{date_input}'. Use format like '21', 'March 15', or '2025-03-15'")

@tool
def book_maintenance_appointment(
    customer_name: str,
    contact_number: str,
    issue_description: str,
    preferred_date: str,
    address: str,
    urgency: str = "normal"
) -> str:
    """
    Book a maintenance appointment and store it in the system.
    
    Args:
        customer_name: Customer's full name
        contact_number: Phone number for contact
        issue_description: Brief description of the maintenance issue
        preferred_date: Flexible date format - can be:
            - Just day: "21" or "21st" (assumes current month/year)
            - Month and day: "March 15" or "15 March" (assumes current year)
            - Full date: "2025-03-15"
            - Keywords: "tomorrow", "next week", "next month"
        address: Full address where service is needed
        urgency: Priority level (normal, high, critical)
    
    Returns:
        JSON string with booking confirmation details
    """
    try:
     
        try:
            parsed_date = parse_flexible_date(preferred_date)
        except ValueError as e:
            return json.dumps({
                "status": "error",
                "message": str(e)
            })
        

        booking_date = datetime.strptime(parsed_date, "%Y-%m-%d")
        

        if booking_date.date() < datetime.now().date():
            return json.dumps({
                "status": "error",
                "message": f"Cannot book appointments in the past. Today's date is {datetime.now().strftime('%Y-%m-%d')}. Please choose today or a future date."
            })

        bookings = load_json(BOOKINGS_FILE)
        
    
        booking_id = generate_id("BOOK")
        
        
        booking = {
            "booking_id": booking_id,
            "customer_name": customer_name,
            "contact_number": contact_number,
            "issue_description": issue_description,
            "preferred_date": parsed_date, 
            "original_date_input": preferred_date, 
            "address": address,
            "urgency": urgency,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "assigned_technician": None,
            "estimated_time_slot": "09:00-12:00" if urgency != "critical" else "ASAP"
        }
  
        bookings.append(booking)

        save_json(BOOKINGS_FILE, bookings)
        
        return json.dumps({
            "status": "success",
            "booking_id": booking_id,
            "customer_name": customer_name,
            "preferred_date": parsed_date,
            "original_input": preferred_date,
            "time_slot": booking["estimated_time_slot"],
            "urgency": urgency,
            "message": f"Appointment booked successfully! Booking ID: {booking_id}. "
                      f"Date: {parsed_date}. A technician will contact you at {contact_number} to confirm the exact time."
        })
        
    except ValueError as e:
        return json.dumps({
            "status": "error",
            "message": f"Date parsing error: {str(e)}"
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to create booking: {str(e)}"
        })



@tool
def log_customer_issue(
    customer_name: str,
    issue_type: str,
    description: str,
    location: str,
    severity: str = "medium",
    contact_info: Optional[str] = None
) -> str:
    """
    Log a customer's maintenance issue for tracking and follow-up.
    
    Args:
        customer_name: Customer's name
        issue_type: Type of issue (damp, leak, electrical, heating, structural, etc.)
        description: Detailed description of the issue
        location: Specific location (e.g., "bedroom wall", "kitchen ceiling")
        severity: Issue severity (low, medium, high, critical)
        contact_info: Optional contact information
    
    Returns:
        JSON string with issue ID and confirmation
    """
    try:
   
        issues = load_json(ISSUES_FILE)
 
        issue_id = generate_id("ISSUE")
        

        issue = {
            "issue_id": issue_id,
            "customer_name": customer_name,
            "issue_type": issue_type.lower(),
            "description": description,
            "location": location,
            "severity": severity,
            "contact_info": contact_info,
            "status": "open",
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "notes": [],
            "resolved": False
        }
        

        issues.append(issue)

        save_json(ISSUES_FILE, issues)
        
        return json.dumps({
            "status": "success",
            "issue_id": issue_id,
            "message": f"Issue logged successfully with ID: {issue_id}. "
                      f"This will be tracked for follow-up and resolution.",
            "severity": severity,
            "next_steps": "Our team will review this issue and contact you for next steps."
        })
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to log issue: {str(e)}"
        })


@tool
def create_maintenance_ticket(
    issue_type: str,
    severity: str,
    description: str,
    customer_name: str,
    location: str,
    requires_immediate_action: bool = False
) -> str:
    """
    Create a formal maintenance or safety ticket for urgent issues.
    Use this for issues that require professional attention.
    
    Args:
        issue_type: Type of issue (electrical, plumbing, structural, gas, fire, etc.)
        severity: Severity level (low, medium, high, critical)
        description: Detailed description of the safety concern or issue
        customer_name: Customer's name
        location: Address or specific location
        requires_immediate_action: Whether this needs urgent response
    
    Returns:
        JSON string with ticket details and priority information
    """
    try:

        tickets = load_json(TICKETS_FILE)
  
        ticket_id = generate_id("TKT")
        

        priority_map = {
            "critical": {"priority": "P1", "response_time": "Immediate (within 1 hour)"},
            "high": {"priority": "P2", "response_time": "Same day (within 4 hours)"},
            "medium": {"priority": "P3", "response_time": "Next business day"},
            "low": {"priority": "P4", "response_time": "Within 3 business days"}
        }
        
        priority_info = priority_map.get(severity, priority_map["medium"])

        ticket = {
            "ticket_id": ticket_id,
            "issue_type": issue_type,
            "severity": severity,
            "priority": priority_info["priority"],
            "description": description,
            "customer_name": customer_name,
            "location": location,
            "requires_immediate_action": requires_immediate_action,
            "status": "open",
            "assigned_to": None,
            "created_at": datetime.now().isoformat(),
            "response_time_target": priority_info["response_time"],
            "resolution_notes": [],
            "escalated": severity in ["high", "critical"] or requires_immediate_action
        }
        
      
        tickets.append(ticket)
      
        save_json(TICKETS_FILE, tickets)
      
        message = f"Maintenance ticket {ticket_id} created successfully.\n"
        message += f"Priority: {priority_info['priority']} ({severity})\n"
        message += f"Expected Response: {priority_info['response_time']}\n"
        
        if severity == "critical" or requires_immediate_action:
            message += "\nURGENT: This ticket has been flagged for immediate attention. "
            message += "Emergency team has been notified."
        
        return json.dumps({
            "status": "success",
            "ticket_id": ticket_id,
            "priority": priority_info["priority"],
            "severity": severity,
            "response_time": priority_info["response_time"],
            "escalated": ticket["escalated"],
            "message": message
        })
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to create ticket: {str(e)}"
        })


@tool
def escalate_to_human_representative(
    reason: str,
    customer_name: str,
    issue_summary: str,
    urgency: str = "normal",
    conversation_history_summary: Optional[str] = None
) -> str:
    """
    Escalate the conversation to a human representative.
    Use this when:
    - Issue is too complex for AI to handle
    - Customer is frustrated or dissatisfied
    - Safety concerns require human judgment
    - Customer explicitly requests human assistance
    
    Args:
        reason: Why escalation is needed (frustrated_customer, complex_issue, safety_concern, customer_request, etc.)
        customer_name: Customer's name
        issue_summary: Brief summary of the issue discussed
        urgency: Urgency level (normal, high, critical)
        conversation_history_summary: Optional summary of the conversation so far
    
    Returns:
        JSON string with escalation confirmation and next steps
    """
    try:
   
        escalations = load_json(ESCALATIONS_FILE)
     
        escalation_id = generate_id("ESC")

        wait_times = {
            "critical": "Connecting you now (0-2 minutes)",
            "high": "Agent available within 5 minutes",
            "normal": "Agent available within 15 minutes"
        }
        
        wait_time = wait_times.get(urgency, wait_times["normal"])
        
        # Create escalation record
        escalation = {
            "escalation_id": escalation_id,
            "reason": reason,
            "customer_name": customer_name,
            "issue_summary": issue_summary,
            "urgency": urgency,
            "conversation_summary": conversation_history_summary,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "assigned_agent": None,
            "estimated_wait_time": wait_time,
            "resolved": False
        }
        
        escalations.append(escalation)
        
       
        save_json(ESCALATIONS_FILE, escalations)
   
        if urgency == "critical":
            message = "🚨 URGENT ESCALATION IN PROGRESS\n\n"
            message += "Connecting you to a specialist immediately...\n"
            message += f"Escalation ID: {escalation_id}\n"
            message += "Please stay on the line."
        else:
            message = "📞 Connecting You to a Human Representative\n\n"
            message += f"Escalation ID: {escalation_id}\n"
            message += f"Estimated wait time: {wait_time}\n\n"
            message += "Your conversation history has been shared with our team. "
            message += "They will have full context of your issue.\n\n"
            message += "What happens next:\n"
            message += "1. Your request is now in the priority queue\n"
            message += "2. An agent will join this conversation shortly\n"
            message += "3. They'll have all the details we've discussed\n\n"
            message += "Thank you for your patience!"
        
        return json.dumps({
            "status": "success",
            "escalation_id": escalation_id,
            "urgency": urgency,
            "wait_time": wait_time,
            "message": message,
            "action": "HUMAN_TAKEOVER",
            "note": "AI should stop responding. Human agent will take over."
        })
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to escalate: {str(e)}"
        })


@tool
def check_booking_availability(date_str: str) -> str:
    """
    Check if technicians are available on a specific date.
    
    Args:
        date_str: Flexible date format - can be:
            - Just day: "21" or "21st" (assumes current month/year)
            - Month and day: "March 15" (assumes current year)
            - Full date: "2025-03-15"
            - Keywords: "tomorrow", "next week"
    
    Returns:
        JSON string with availability information
    """
    try:
        # Parse flexible date input
        try:
            parsed_date = parse_flexible_date(date_str)
        except ValueError as e:
            return json.dumps({
                "status": "error",
                "message": str(e)
            })
        
        # Validate date
        check_date = datetime.strptime(parsed_date, "%Y-%m-%d")
        
        # Check if date is in the past (allow today)
        if check_date.date() < datetime.now().date():
            return json.dumps({
                "status": "unavailable",
                "date": parsed_date,
                "original_input": date_str,
                "message": f"Cannot check availability for past dates. Today is {datetime.now().strftime('%Y-%m-%d')}."
            })
        
        # Load existing bookings
        bookings = load_json(BOOKINGS_FILE)
        
        # Count bookings for that date
        bookings_on_date = [b for b in bookings if b["preferred_date"] == parsed_date]
        
        # Simple availability logic (max 4 bookings per day)
        max_bookings_per_day = 4
        available_slots = max_bookings_per_day - len(bookings_on_date)
        
        if available_slots > 0:
            # Generate available time slots
            all_slots = ["09:00-12:00", "12:00-15:00", "15:00-18:00", "18:00-21:00"]
            booked_slots = [b.get("estimated_time_slot", "") for b in bookings_on_date]
            available_time_slots = [slot for slot in all_slots if slot not in booked_slots]
            
            return json.dumps({
                "status": "available",
                "date": parsed_date,
                "original_input": date_str,
                "available_slots": available_slots,
                "time_slots": available_time_slots,
                "message": f"{available_slots} technician(s) available on {parsed_date}"
            })
        else:
            # Find next available date
            next_date = check_date + timedelta(days=1)
            return json.dumps({
                "status": "fully_booked",
                "date": parsed_date,
                "original_input": date_str,
                "message": f"Fully booked on {parsed_date}. Try {next_date.strftime('%Y-%m-%d')} instead."
            })
        
    except ValueError as e:
        return json.dumps({
            "status": "error",
            "message": f"Date parsing error: {str(e)}"
        })


langchain_tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "book_maintenance_appointment",
            "description": "Book a maintenance appointment for a customer. Use this when customer wants to schedule a technician visit. Accepts flexible date formats.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Customer's full name"},
                    "contact_number": {"type": "string", "description": "Phone number"},
                    "issue_description": {"type": "string", "description": "What needs to be fixed"},
                    "preferred_date": {
                        "type": "string", 
                        "description": "Flexible date format. Can be: '21' (just day), 'March 15' (month and day), '2025-03-15' (full date), 'tomorrow', 'next week'"
                    },
                    "address": {"type": "string", "description": "Service address"},
                    "urgency": {"type": "string", "enum": ["normal", "high", "critical"], "description": "Priority level"}
                },
                "required": ["customer_name", "contact_number", "issue_description", "preferred_date", "address"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_customer_issue",
            "description": "Log a customer's issue for tracking. Use this to create a record of the customer's problem.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string"},
                    "issue_type": {"type": "string", "description": "damp, leak, electrical, heating, etc."},
                    "description": {"type": "string"},
                    "location": {"type": "string", "description": "e.g., bedroom wall, kitchen ceiling"},
                    "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                    "contact_info": {"type": "string"}
                },
                "required": ["customer_name", "issue_type", "description", "location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_maintenance_ticket",
            "description": "Create a formal maintenance ticket for issues requiring professional attention. Use for safety concerns or complex issues.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_type": {"type": "string"},
                    "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                    "description": {"type": "string"},
                    "customer_name": {"type": "string"},
                    "location": {"type": "string"},
                    "requires_immediate_action": {"type": "boolean"}
                },
                "required": ["issue_type", "severity", "description", "customer_name", "location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human_representative",
            "description": "Escalate conversation to a human agent. Use when issue is too complex, customer is frustrated, or explicitly requests human help.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "frustrated_customer, complex_issue, safety_concern, customer_request, etc."},
                    "customer_name": {"type": "string"},
                    "issue_summary": {"type": "string", "description": "Brief summary of the issue"},
                    "urgency": {"type": "string", "enum": ["normal", "high", "critical"]},
                    "conversation_history_summary": {"type": "string"}
                },
                "required": ["reason", "customer_name", "issue_summary"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_booking_availability",
            "description": "Check if technicians are available on a specific date before booking. Accepts flexible date formats.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_str": {
                        "type": "string", 
                        "description": "Flexible date format. Can be: '21' (just day), 'March 15' (month and day), '2025-03-15' (full date), 'tomorrow', 'next week'"
                    }
                },
                "required": ["date_str"]
            }
        }
    }
]


available_langchain_functions = {
    "book_maintenance_appointment": book_maintenance_appointment,
    "log_customer_issue": log_customer_issue,
    "create_maintenance_ticket": create_maintenance_ticket,
    "escalate_to_human_representative": escalate_to_human_representative,
    "check_booking_availability": check_booking_availability
}


def get_all_bookings() -> List[Dict]:
   
    return load_json(BOOKINGS_FILE)

def get_all_issues() -> List[Dict]:
   
    return load_json(ISSUES_FILE)

def get_all_tickets() -> List[Dict]:

    return load_json(TICKETS_FILE)

def get_all_escalations() -> List[Dict]:
   
    return load_json(ESCALATIONS_FILE)

def clear_all_data():
 
    for filepath in [BOOKINGS_FILE, ISSUES_FILE, TICKETS_FILE, ESCALATIONS_FILE]:
        save_json(filepath, [])
    print(" All data cleared")



