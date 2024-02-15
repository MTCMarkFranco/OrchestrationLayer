# Package Imports
from flask import Flask, request
from dotenv import dotenv_values
from semantic_kernel.orchestration.context_variables import ContextVariables
import json
import asyncio
import sys
import platform

# local imports
from models.data_models import Action
from services.kernel_service import kernel_proxy
from services.chat_history_service import chat_history_proxy
from services.logger_service import logger_proxy

# Initialize the webserver  
app = Flask(__name__, template_folder="templates", static_folder="static")

if platform.system() == "Windows" and sys.version_info >= (3, 8, 0):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
# Service Injection
kernel_svc = kernel_proxy.get_kernel_service()
chat_history_svc=chat_history_proxy.get_chat_history_service()
logger_svc= logger_proxy.get_logger_service()

# Initialize configuration via .env file
config = dotenv_values(".env")

async def processQuery(query):
   
    chatTurnResponse = None
    assistantResponse = None
    
    global kernel_svc
    global chat_history_svc
    global logger_svc
   
    # adding current question to the chat history
    await chat_history_svc.add_message("User1", message={
		"role": "user",
		"content": query
	})
    
    # Debug output
    logger_svc.logger.debug(await chat_history_svc.get_messages_str("User1"))
    
    # Building the Kernel Context for plugins to use
    kc = kernel_svc.kernel.create_new_context(variables=ContextVariables(variables={"history": await chat_history_svc.get_messages_str("User1")}))
        
    # Step 1. Get the action to take from the semantic plugin
    resultAction = await kernel_svc.semantic_plugins["determine_steps"].invoke(input=query, context=kc)
    action_dict = json.loads(resultAction.result)
    action = Action(**action_dict)
        
    # Step 2 - Take the action
    if action.action == "search":
        # Get the response from the last step in the plan
        chatTurnAPIResponse = (await kernel_svc.query_index_plugin["get_library_query_results"].invoke(input=query, context=kc)).result
        # Adding current response to the chat history
        await chat_history_svc.add_message("User1", message={
            "role": "assistant",
            "content": chatTurnAPIResponse
        })
    
    if action.action == "synthesize":
        # Get the response from the last step in the plan
        lastQueryResultsJson = await chat_history_svc.get_last_assistant_response("User1")
        chatTurnAPIResponse = (await kernel_svc.semantic_plugins["generate_synthesis"].invoke(input=lastQueryResultsJson)).result
        await chat_history_svc.clear_history("User1")

    if action.action == "None":
        await chat_history_svc.clear_history("User1")
        chatTurnAPIResponse = json.dumps({ "None": {}} )
                               
    # Get the response from the action above and prepare for return...
    logger_svc.logger.debug(chatTurnAPIResponse)
    logger_svc.logger.info("Chat Turn Complete! Returning the response...")
           
      
    return chatTurnAPIResponse
 
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
