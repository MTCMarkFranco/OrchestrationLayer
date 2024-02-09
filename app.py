from semantic_kernel.orchestration.context_variables import ContextVariables
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.planning import SequentialPlanner
from flask import Flask, request, jsonify
from functools import wraps
from dotenv import dotenv_values
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
    handler.setFormatter(DurationFormatter('%(log_color)s%(levelname)s: Previous Step Time: %(duration)s(seconds). Next Step: %(message)s',
            log_colors={
                            'DEBUG': 'cyan',
                            'INFO': 'green',
                            'WARNING': 'yellow',
                            'ERROR': 'red',
                            'CRITICAL': 'red,bg_white',
                        }))
    logger: logging.Logger = colorlog.getLogger("__CHATBOT__")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
     
    # Initialize the SemanticKernel
    logger.info("Initializing Semantic Kernel==0.5.0.dev0")
    kernel = sk.Kernel()
   
    deployment, api_key, endpoint  = sk.azure_openai_settings_from_dot_env()
    kernel.add_chat_service("ChatBot-Rag", AzureChatCompletion(deployment_name=deployment, api_key=api_key, base_url=endpoint))    
           
    logger.info("Loading Semantic and Native Plugins...")
    query_index_plugin = kernel.import_plugin(QueryIndexPlugin(), "QueryIndexPlugin")
    semantic_plugins = kernel.import_semantic_plugin_from_directory("plugins", "library") 
   
    # Define the plan (Using SequentialPLanner, but note: HandleBars will replace this in the near future.)
    logger.info("Generating the plan...")      
    planner = SequentialPlanner(kernel=kernel)
    planDirective = """interact with the Azure Search Library index and retrieve relevant documents based on the user's query.
                    then, prepare a response to send back to the user in valid JSON Format.
                    """
    sequential_plan = await planner.create_plan(goal=planDirective)
    
    # Execute the plan Steps in Sequence
    logger.info("Executing the plan...")
    planContext = kernel.create_new_context(variables=ContextVariables(variables={"input": query,"userinput": query}))
    assistantResponse = None
    for currentIndex, step in enumerate(sequential_plan._steps):
        logger.info(f"Executing Step: {currentIndex+1} of {len(sequential_plan._steps)} ({step.description})")
        assistantResponse = await step.invoke(input=query, context=planContext)
    
    # Get the response from the last step in the plan
    chatTurnResponse = assistantResponse.result
    logger.info("Chat Turn Complete! Returning the response...")
      
    return chatTurnResponse  
 
@app.route("/")
def root():
    return "Hello. chat API here to help you!"

@app.route('/query', methods=['OPTIONS'])
def options():
    return {'Allow' : 'GET, POST, OPTIONS'}, 200, \
    { 'Access-Control-Allow-Origin': '*', \
      'Access-Control-Allow-Methods' : 'POST, OPTIONS', \
      'Access-Control-Allow-Headers' : 'Content-Type' }
       
@app.route("/query", methods=["POST"])
async def query():
    body = request.get_json()
    query = body['messages'][0]['text']

    output = await processQuery(query)
    
    if output is None:
        return {"html": "<p>Error Getting results from Index</p>" }, 200, {'Access-Control-Allow-Origin': '*'}
    else:
        return {"html": output }, 200, {'Access-Control-Allow-Origin': '*'}