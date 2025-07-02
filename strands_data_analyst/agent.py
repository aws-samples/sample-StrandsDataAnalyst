import json

import boto3
from json_repair import repair_json

from strands import Agent
from strands.models import BedrockModel
from strands.handlers.callback_handler import null_callback_handler
from strands.agent.conversation_manager import SlidingWindowConversationManager

from strands_data_analyst.db_schema import format_db_schema
from strands_data_analyst.databases import SQLiteDB
from strands_data_analyst.callback_handler import MessageCallbackHandler
from strands_data_analyst.python_environment import PythonInterpreter
from strands_data_analyst.templates import populate_template


LLM_HAIKU = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
LLM_SONNET = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"

class DataAnalystAgent:
    DATA_ANALYSIS_PROMPT = """
<CONTEXT>
Data analysis requests (queries, visualizations, etc) from the user are referencing a {{db_type}} database.
To open a connection to the database use the following code:
```python
{{db_conn_open}}

# Data Analysis code
...

{{db_conn_close}}
```

This is the DB schema:
{{db_schema}}

You can run SQL queries to fetch the relevant data using this code:
```python
import pandas as pd

sql_query = "SELECT ..."
data_frame = pd.read_sql_query(sql_query, db_conn)
```
Always keep the SQL query in a `sql_query` variable and the pandas data-frame in a `data_frame` variable for later inspection.

You can then further analyze this data-frame to answer the user query.
Print all the information you might need to answer the user query.

If a `visualization` could enrich the answer, you should:
1. Write a `visualization_caption` about the visualization you want to generate.
2. Use the SVG matplotlib static backend, because the visualization code will be executed without a GUI. 
3. Generate a `matplotlib.figure.Figure` object called `visualization`, adding a title and label the x and y axes appropriately. Set the `visualization` subtitle as empty. Do not save nor show the `visualization`, the user can directly access its instantiation.

Example Code:
```python
import matplotlib
matplotlib.use('svg')

import matplotlib.pyplot as plt

# Init the figure
visualization, ax = plt.subplots(1, 1, figsize=(10, 4))

visualization_caption = "caption about the visualization to be generated"

# Add the data visualization code here
...

```
It is important that you use the variable names `visualization` for the figure and `visualization_caption` for the caption to allow later access to them.
Do not invoke `data_frame.plot`, only the `visualization` `matplotlib.figure.Figure` will be visible to the user.
</CONTEXT>"""

    DATA_REPORT_PROMPT="""
You are running a data analysis session with the user, and you need to summarize all the information and insights into the following MarkDown document:
<DOCUMENT>
{{document}}
</DOCUMENT>

You can intermix in the report the following images: 
{%- for image in images %}
    - {{ image.markdown() }}
{%- endfor %}

Try to find common threads between the sections, and provide a business narrative.
Feel free to change the document title, add new sections/findings, and update general sections like an "Executive Summary", "Conclusion", etc...

You should return to the user only the final Markdown document text, without any additional comment, and without any markup.
"""

    DATA_EXPLORATION = """
You are a highly skilled data analyst who is given a DB with the following schema:
{{db_schema}}

You should come up with three insightful analysis goals about the data.

You should return a single JSON data-structure with a list of dictionaries containing the following fields:
- `goal_rationale`: a rationale of why this is an interesting analysis goal, describing what new insights we will gain.
- `goal_question`: the goal description formulated as a question to be answered.

Output only JSON data, without adding any other comment:
[
  {
    "goal_rationale": "",
    "goal_question": ""
  },
  {
    "goal_rationale": "",
    "goal_question": ""
  },
  {
    "goal_rationale": "",
    "goal_question": ""
  }
]
""" 
    def __init__(self,
                 verbose=True,
                 always_reset=False,
                 img_handler=None,
                 conversation_window=8):
        self.python_interpreter = PythonInterpreter()
        self.agent = Agent(
            model=BedrockModel(
                model_id=LLM_HAIKU,
                boto_session=boto3.Session()),
            tools=[self.python_interpreter.get_tool()],
            callback_handler=MessageCallbackHandler() if verbose else null_callback_handler,
            conversation_manager=SlidingWindowConversationManager(window_size=conversation_window),
            system_prompt="""
You are an expert Data Analyst who can solve any task using code blobs. You will be given a data analysis task to solve as best you can.
To do so, you have been given access to a tool to execute python code: `python_repl`
""")
        self.always_reset = always_reset
        self.db_id = None
        self.db_schema = None
        self.dataset_context = None

        self.img_handler = img_handler
        self.document = ""

    def reset(self):
        self.agent.messages = []
        
        if self.img_handler is not None:
            self.img_handler.reset()
        self.document = ""

    def set_db(self, db_id, db):
        if db_id == self.db_id:
            return
        
        self.reset()

        self.db_id = db_id
        self.db_schema = format_db_schema(db.get_schema())
        db_conn_open, db_conn_close = db.get_connection_code()
        
        self.dataset_context = populate_template(
            DataAnalystAgent.DATA_ANALYSIS_PROMPT,
            variables={
                'db_type': db.DB_TYPE,
                'db_schema': self.db_schema,
                'db_conn_open': db_conn_open,
                'db_conn_close': db_conn_close
            })

    def generate_report(self):
        response = self.agent(populate_template(
            DataAnalystAgent.DATA_REPORT_PROMPT,
            variables={
                'document': self.document,
                'images': self.img_handler.images if self.img_handler is not None else []
            }))
        self.document = response.message['content'][0]['text'].strip()
        return self.document

    def query(self, query):
        if self.always_reset:
            self.reset()

        if self.dataset_context:
            query = f"{query}\n{self.dataset_context}"

        self.python_interpreter.clear_state()
        output = self.agent(query)
        
        response = {
            'answer': output.message['content'][0]['text'].strip()
        }
        for var_name in ['sql_query', 'data_frame', 'visualization', 'visualization_caption']:
            if var_name in self.python_interpreter.state:
                response[var_name] = self.python_interpreter.state[var_name]
        
        if 'visualization' in response and self.img_handler is not None:
            response['visualization'] = self.img_handler.save_img(
                response['visualization'],
                response.get("visualization_caption"))
            
        return response

    def automated_data_exploration(self):
        response = self.agent(populate_template(
            DataAnalystAgent.DATA_EXPLORATION,
            variables={
                'db_schema': self.db_schema,
            }))
        goals = json.loads(repair_json(response.message['content'][0]['text']))

        for i, goal in enumerate(goals, start=1):
            goal['goal_progress'] = f"[{i}/{len(goals)}]"
            yield 'goal', goal

            yield 'query_response', self.query(goal['goal_question'])

        yield 'report', self.generate_report()


if __name__ == "__main__":
    agent = DataAnalystAgent(verbose=True)
    db = SQLiteDB({'db_location': './data/databases/chinook_sqlite/db.sqlite'})
    agent.set_db('chinook', db)

    for msg in agent.automated_data_exploration():
        print(msg)
