from flask import Flask, request, jsonify
from functools import wraps
from dotenv import dotenv_values
from semantic_kernel.orchestration.context_variables import ContextVariables
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion, AzureTextCompletion
from semantic_kernel.planning import SequentialPlanner
from dataclasses import dataclass
import json
import logging
from typing import List
 
app = Flask(__name__, template_folder="templates", static_folder="static")
config = dotenv_values(".env")
apiKey = config.get("API_KEY", None)
 
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
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
 
    # Initialize the SemanticKernel
    logger.info("Initializing SemanticKernel")
    kernel = sk.Kernel()
   
    deployment, api_key, endpoint  = sk.azure_openai_settings_from_dot_env()
    kernel.add_chat_service("GPT", AzureChatCompletion(deployment_name=deployment, api_key=api_key, base_url=endpoint))    
           
    native_plugins = kernel.import_native_plugin_from_directory("plugins/library", "query_index")
    semantic_plugins = kernel.import_semantic_plugin_from_directory("plugins", "library")
   
    # Define the plan
    seqPlanner = SequentialPlanner(kernel)
    planDirective = """To interact with the Azure Search Library index, 
                    retrieve relevant documents based on the user's query,
                    process the results
                    and prepare a response to send back to the librarian in valid JSON Format.
                    """
    seqPlan = await seqPlanner.create_plan_async(goal=planDirective)
    
    # DEBUG: output the plan steps
    for step in seqPlan._steps:
        print(step.description, ":", step._state.__dict__)
    planContext = kernel.create_new_context(variables=ContextVariables(variables={"userinput": query}))
    
    # execute the plan Steps in Sequence
    assistantResponse = await seqPlan.invoke_async(query, planContext)
    
    # Transform the result into a JSON object
    data_dict = json.loads(assistantResponse.result)
    assistantAction = AssistantAction(**data_dict)
    chatTurnResponse = assistantAction.records
      
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