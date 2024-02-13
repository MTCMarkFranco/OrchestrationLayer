from semantic_kernel.orchestration.context_variables import ContextVariables
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.planning import SequentialPlanner
from flask import Flask, request, jsonify
from functools import wraps
from dotenv import dotenv_values
import time
import json
import logging
import colorlog
from typing import List
from dataclasses import dataclass
import semantic_kernel as sk

from plugins.library.query_index.native_function import QueryIndexPlugin
 
app = Flask(__name__, template_folder="templates", static_folder="static")
config = dotenv_values(".env")

class ChatHistory:
    def __init__(self):
        self.history = []
    
    def add_message(self, message):
        self.history.append(message)
    
    def get_last_assistant_response(self):
        for i in range(len(self.history) - 1, -1, -1):
            if self.history[i]["role"] == "assistant":
                return self.history[i]["content"]
            
    def get_messages(self):
        return json.dumps(self.history)
    
    def clear_history(self):
        self.history = []
        
chat_history = ChatHistory()

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

import dataclasses

@dataclass
class Action:
    action: str
    

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
    logger.setLevel(logging.INFO)
     
    # Initialize the SemanticKernel
    logger.info("Initializing Semantic Kernel==0.5.0.dev0")
    kernel = sk.Kernel()
   
    deployment, api_key, endpoint  = sk.azure_openai_settings_from_dot_env()
    kernel.add_chat_service("ChatBot-Rag", AzureChatCompletion(deployment_name=deployment, api_key=api_key, base_url=endpoint))    
           
    logger.info("Loading Semantic and Native Plugins...")
    query_index_plugin = kernel.import_plugin(QueryIndexPlugin(), "QueryIndexPlugin")
    semantic_plugins = kernel.import_semantic_plugin_from_directory("plugins", "library") 
   
    # adding current question to the chat history
    chat_history.add_message({
		"role": "user",
		"content": query
	})
    
    assistantResponse = None
   
    KernelContext = kernel.create_new_context(variables=ContextVariables(variables={"history": chat_history.get_messages()}))
        
    resultAction = await semantic_plugins["determine_steps"].invoke(input=query, context=KernelContext)
    
    action_dict = json.loads(resultAction.result)
    action = Action(**action_dict)
    
    # switch statement over action.action
    if action.action == "search":
        # Get the response from the last step in the plan
        searchRecords = await query_index_plugin["get_library_query_results"].invoke(input=query, context=KernelContext)
        assistantResponse = await semantic_plugins["send_response"].invoke(input=searchRecords.result, context=KernelContext)
    
    if action.action == "synthesize":
        # Get the response from the last step in the plan
        lastQueryResultsJson = chat_history.get_last_assistant_response()
        assistantResponse = await semantic_plugins["generate_synthesis"].invoke(input=lastQueryResultsJson)

    
    # Get the response from the last step in the plan
    chatTurnResponse = assistantResponse.result
    logger.info("Chat Turn Complete! Returning the response...")
        
    chat_history.add_message({
        "role": "assistant",
        "content": chatTurnResponse
    })
        
    print(chatTurnResponse)
   
      
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
        return {"error": "Error Getting results from Index" }, 400, {'Access-Control-Allow-Origin': '*'}
    else:
        return output, 200, {'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json'}