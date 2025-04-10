from crewai import Agent, Task, Crew, Process
from crewai import LLM
from crewai_tools import FileReadTool ,PGSearchTool
from crewai.tools import BaseTool
import os
from typing import Type, Optional ,Dict ,Any
from pydantic import Field
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain.tools import BaseTool as LangChainBaseTool
#from langchain_community.llms import HuggingFaceHub
from langchain_community.llms import Ollama
import sqlite3
import sqlalchemy

API_KEY = "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"


sql_llm = Ollama(
    model="mistral",
    base_url="http://localhost:11434",
    temperature=0.3
)


llm_use_case = LLM(
    model="ollama/zephyr",
    base_url="http://localhost:11434",
    temperature=0.5
)


llm_schema = LLM(
    model="ollama/llama3",
    base_url="http://localhost:11434",
    temperature=0.3
)

# Source Mapper Agent LLM (to map schema fields to source fields)
llm_mapper = LLM(
    model="ollama/llama3",
    base_url="http://localhost:11434",
    temperature=0.4
)

#----------------------------------------------------------------------SQLDatabase toolkit crew ai compatiable
os.environ["DATABASE_URL"] = "sqlite:///example.db"

def convert_langchain_tool_to_crewai(lc_tool: LangChainBaseTool) -> BaseTool:
    class CrewAIAdaptedTool(BaseTool):
        name: str = lc_tool.name
        description: str = lc_tool.description

        # Accept the full input as an optional dictionary.
        # CrewAI will supply a dict with key "input" or an empty dict.
        def _run(self, input: Optional[Dict[str, Any]] = None) -> str:
            # Ensure input is a dictionary.
            if input is None:
                input = {}
            # Extract the inner value for our tool.
            # If the caller didn't supply "input_text", default to empty string.
            input_text = input.get("input_text", "")
            return lc_tool.run(input_text)

    return CrewAIAdaptedTool()


def get_crewai_sql_tools(db_uri: str, llm) -> list[BaseTool]:
    print(f"🔌 Using SQLite source: {db_uri}")

    # Step 1: Create SQLDatabase from URI
    db = SQLDatabase.from_uri(db_uri)

    # Step 2: Build LangChain SQL Toolkit
    sql_toolkit = SQLDatabaseToolkit(db=db, llm=llm)

    # Step 3: Convert tools to CrewAI-compatible tools
    langchain_tools = sql_toolkit.get_tools()
    crewai_sql_tools = [convert_langchain_tool_to_crewai(tool) for tool in langchain_tools]

    return crewai_sql_tools

db = SQLDatabase.from_uri(os.environ["DATABASE_URL"])

sql_toolkit = SQLDatabaseToolkit(db=db,llm=sql_llm)

langchain_tools = sql_toolkit.get_tools()

crewai_sql_tools = [convert_langchain_tool_to_crewai(tool) for tool in langchain_tools]

#--------------------------------------crewai_sql_tools----------------------------------------------------------

# def get_source_tool(mode: str = "sqlite", db_path="project_memory.db", json_path="inputs/source_schema.json"):
#     """
#     Returns the appropriate source schema tool based on selected mode.
#
#     Parameters:
#         mode (str): 'sqlite' or 'json'
#         db_path (str): Path to SQLite DB
#         json_path (str): Path to JSON schema file
#
#     Returns:
#         tool: Initialized CrewAI-compatible tool
#     """
#     if mode == "sqlite":
#         if os.path.exists(db_path):
#             print("🔌 Using SQLite source: ", db_path)
#             return SQLDatabaseToolkit(db=db_path)
#         else:
#             print(f"⚠️ SQLite DB not found at {db_path}. Falling back to JSON.")
#             mode = "json"
#
#     if mode == "json":
#         if os.path.exists(json_path):
#             print("📄 Using JSON source: ", json_path)
#             return FileReadTool(file_path=json_path)
#         else:
#             raise FileNotFoundError(f"❌ JSON schema not found at {json_path}.")
#
#     raise ValueError("❌ Invalid mode selected. Choose 'sqlite' or 'json'.")




# -------------------------- Tools


use_case_reader = FileReadTool(file_path="inputs/use_case.txt")

# SQLite tool for source schema mapping
sqlite_tool = crewai_sql_tools
crewai_sql_tools = get_crewai_sql_tools("sqlite:///project_memory.db", sql_llm)

#------------DEMO
#pg = PGSearchTool()

#-------------------------- Agent


use_case_agent = Agent(
    role="Use Case Interpreter",
    goal="Extract key customer fields from business requirements",
    backstory="Understands business needs and translates them to data attributes.",
    llm=llm_use_case,
    tools=[use_case_reader],
    verbose=True
)

schema_designer = Agent(
    role="Schema Designer",
    goal="Create a Customer 360 schema using customer attributes",
    backstory="Designs structured schemas from given data requirements.",
    llm=llm_schema,
    verbose=True
)
#------------------------------------------------------Helper
source_mode = "sqlite"

# source_tool = get_source_tool(mode=source_mode)
#--------------------------------------------------------------
source_mapper = Agent(
    role="Source Mapper",
    goal="Map schema fields to source systems (SQLite database)",
    backstory="Maps the schema fields to source systems by querying available data.",
    llm=llm_mapper,
    tools=crewai_sql_tools,
    verbose=True
)

# --------------------------- Tasks

# Task 1
task_use_case = Task(
    description="Extract customer attributes from business use case",
    expected_output="List of required fields: [customer_id, age, ...]",
    agent=use_case_agent
)

# Task 2
task_schema = Task(
    description="Design schema from the required customer attributes",
    expected_output="A dictionary: {field_name: data_type}",
    agent=schema_designer
)

# Task 3
task_mapping = Task(
    description="Map schema fields to source fields",
    expected_output="Mapping: {source_field: target_field}",
    agent=source_mapper
)
#------------------------------------------Testing __________________
# task_mapping = Task(
#     description="Given a target schema field 'age', find the best matching field from the source database tables. Respond with the best match and the source table it belongs to.",
#     expected_output="Example: {'age': 'crm_db.dob'}",
#     agent=source_mapper
# )
# crew1= Crew(
#     agents = [source_mapper],
#     tasks=[task_mapping],
#     process = Process.sequential,
#     verbose = True
# )
# -------------------------- Crew

crew = Crew(
    agents=[use_case_agent, schema_designer, source_mapper],
    tasks=[task_use_case, task_schema, task_mapping],
    process=Process.sequential,
    verbose=True
)

# -------------------------- Running the Demo --------------------------- #

result = crew.kickoff()

# Print the final result (mapping + schema)
print("Final Result: ", result)

# -------------------------- Markdown Report --------------------------- #

# Certifier Agent
class MarkdownWriterTool:
    name = "markdown_writer"
    description = "Writes the certification summary to markdown"

    def _run(self, content):
        with open("outputs/certification_report.md", "w") as f:
            f.write(content)
        return "Certification saved to certification_report.md"

#Certification Report
certification_content = """
# Certification Report for Customer 360 Data Product

## Overview:
- **Schema Fields**: customer_id, age, location, credit_score, investment_history
- **Mapped Fields**: crm_db.cust_id -> customer_id, banking_db.avg_balance_12m -> average_balance
- **Status**: Approved

## Notes:
- No missing fields
- **Warning**: 'dob' used for age calculation, could be flagged as PII
"""


markdown_writer = MarkdownWriterTool()
markdown_writer._run(certification_content)
print("Certification report saved successfully.")
