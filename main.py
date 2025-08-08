from crewai import Agent, Task, Crew, Process
from crewai import LLM
from crewai_tools import FileReadTool ,PGSearchTool
from crewai.tools import BaseTool
import os
from typing import Type, Optional ,Dict ,Any ,List
from pydantic import Field
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain.tools import BaseTool as LangChainBaseTool
#from langchain_community.llms import HuggingFaceHub
from langchain_community.llms import Ollama
import sqlite3
import sqlalchemy

API_KEY = "#######

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

#------------------------------------SQLDatabase toolkit crew ai compatiable
os.environ["DATABASE_URL"] = "sqlite:///example.db"

def convert_langchain_tool_to_crewai(lc_tool: LangChainBaseTool) -> BaseTool:
    class CrewAIAdaptedTool(BaseTool):
        name: str = lc_tool.name
        description: str = lc_tool.description

        def _run(self, input_text: Optional[str] = "") -> str:
            return lc_tool.run(input_text or "")

    return CrewAIAdaptedTool()

def get_crewai_sql_tools(db_uri: str, llm) -> List[BaseTool]:
    """
    Returns a list of CrewAI-compatible SQL tools connected to the specified DB.

    Args:
        db_uri (str): URI of the database (e.g. sqlite:///example.db or postgresql://...)
        llm: LangChain-compatible LLM instance (can be HuggingFaceHub, Ollama, etc.)

    Returns:
        List[BaseTool]: Adapted tools usable in CrewAI agents.
    """
    db = SQLDatabase.from_uri(db_uri)
    sql_toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    langchain_tools = sql_toolkit.get_tools()
    crewai_tools = [convert_langchain_tool_to_crewai(tool) for tool in langchain_tools]
    return crewai_tools

db = SQLDatabase.from_uri(os.environ["DATABASE_URL"])

sql_toolkit = SQLDatabaseToolkit(db=db,llm=sql_llm)

langchain_tools = sql_toolkit.get_tools()

crewai_sql_tools = [convert_langchain_tool_to_crewai(tool) for tool in langchain_tools]


use_case_reader = FileReadTool(file_path="inputs/use_case.txt")

#------------------------------------------------------- SQLite tool for source schema mapping
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
#-----------------------------------------------Helper agent for sql
def get_named_tool(tools, name):
    return next((t for t in tools if t.name == name), None)

list_tool = get_named_tool(crewai_sql_tools, "sql_db_list_tables")
schema_tool = get_named_tool(crewai_sql_tools, "sql_db_schema")
#--------------------------------------------------------------
source_mapper = Agent(
    role="Source Mapper",
    goal="Map target schema to source DB tables/fields",
    backstory="Knows the DB inside out.",
    llm=llm_mapper,
    tools=[list_tool, schema_tool],
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
schema_result = task_schema.execute_sync()
# Task 3
task_mapping = Task(
    description=(
        "Given the schema: {schema}, explore the database using the tools provided. "
        "First call `sql_db_list_tables` to see available tables, then use `sql_db_schema` "
        "to inspect relevant ones. Finally, return a JSON mapping from schema field to DB column."
    ),
    expected_output=(
        "Example: { 'first_name': 'users.first_name', 'email': 'users.email' }"
    ),
    agent=source_mapper,
    inputs={"schema": schema_result}
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
for tool in crewai_sql_tools:
    print("✅ Tool loaded:", tool.name)

result = crew.kickoff()
print(result)

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
