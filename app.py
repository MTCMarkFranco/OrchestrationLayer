from semantic_kernel.orchestration.context_variables import ContextVariables
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.planning import SequentialPlanner
from flask import Flask, request, jsonify
from functools import wraps
from dotenv import dotenv_values
import json
import time
import logging
import colorlog
from typing import List
from dataclasses import dataclass
import semantic_kernel as sk

from plugins.library.query_index.native_function import QueryIndexPlugin
 
app = Flask(__name__, template_folder="templates", static_folder="static")
config = dotenv_values(".env")
apiKey = config.get("API_KEY", None)

class DurationFormatter(colorlog.ColoredFormatter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_time = time.time()

    def format(self, record):
        duration = time.time() - self.start_time
        self.start_time = time.time()
        record.duration = "{:.1f}".format(duration)
        return super().format(record)
    
@dataclass
class Record:
    publisheddate: str
    filename: str
    summary: str

@dataclass
class AssistantAction:
    records: List[Record]
    question: str

async def processQuery(query):
   
    useAzureOpenAI = True
    chatTurnResponse = None
   
    # Set up logging
    handler = colorlog.StreamHandler()
    handler.setFormatter(DurationFormatter('%(log_color)s%(levelname)s: Previous Step Time: %(duration)s(seconds). Next Step: %(message)s'))
    logger: logging.Logger = colorlog.getLogger(__name__)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
     
    # Initialize the SemanticKernel
    logger.info("Initializing SemanticKernel")
    kernel = sk.Kernel()
   
    deployment, api_key, endpoint  = sk.azure_openai_settings_from_dot_env()
    kernel.add_chat_service("GPT", AzureChatCompletion(deployment_name=deployment, api_key=api_key, base_url=endpoint))    
           
    logger.info("Loading Semantic and Native Plugins...")
    query_index_plugin = kernel.import_plugin(QueryIndexPlugin(), "QueryIndexPlugin")
    semantic_plugins = kernel.import_semantic_plugin_from_directory("plugins", "library") 
   
    # Define the plan
    logger.info("Generating the plan...")      
    planner = SequentialPlanner(kernel=kernel)
    planDirective = """To interact with the Azure Search Library index, 
                    retrieve relevant documents based on the user's query,
                    and prepare a response to send back to the librarian in valid JSON Format.
                    """
    sequential_plan = await planner.create_plan(goal=planDirective)
    
    # DEBUG: output the plan steps
    # for step in sequential_plan._steps:
    #     print(step.description, ":", step._state.__dict__)
    
    # Execute the plan Steps in Sequence
    logger.info("Executing the plan...")
    planContext = kernel.create_new_context(variables=ContextVariables(variables={"userinput": query}))
    assistantResponse = await sequential_plan.invoke(query, planContext)

    # Transform the result into a JSON object
    logger.info("Transmogrifying ( Shaping ) the result...")
    data_dict = json.loads(assistantResponse.result)
    assistantAction = AssistantAction(**data_dict)
    chatTurnResponse = assistantAction.records
    logger.info("Chat Turn Complete! Returning the response...")
      
    return chatTurnResponse   
 
@app.route("/")
def root():
    return "Hello. chat API here to help you!"
   
@app.route("/query", methods=["POST"])
async def query():
    body = request.get_json()
    query = body.get("query", None)
   
    output = await processQuery(query)
    
    if output is None:
        response = {
            "success": False,
            "error": "An error occurred while processing the query"
        }
    
    else:
        response = {
            "success": True,
            "result": output
        }
    
    return jsonify(response)