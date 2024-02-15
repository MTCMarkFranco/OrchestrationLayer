# Package Imports
from flask import Flask, request
from flask_session import Session
from dotenv import dotenv_values
from semantic_kernel.orchestration.context_variables import ContextVariables
import json

# local imports
from models.data_models import Action
from services.cache_service import cache_service

# Initialize the webserver  
app = Flask(__name__, template_folder="templates", static_folder="static")
app.config['SESSION_TYPE'] = 'in_memory'
Session(app)

# Initialize services
@app.before_first_request
def initialize_services():
    cache_service.initialize_services()

# Initialize configuration via .env file
config = dotenv_values(".env")

async def processQuery(query):
   
    chatTurnResponse = None
    assistantResponse = None
   
    # adding current question to the chat history
    await cache_service.get_chat_history_service.add_message("User1", message={
		"role": "user",
		"content": query
	})
    
    # debug output
    cache_service.get_logger_service.logger.debug(await cache_service.get_chat_history_service.get_messages_str("User1"))
    
    # Building the Kernel Context for plugins to use
    kc = cache_service.get_kernel_service.kernel.create_new_context(variables=ContextVariables(variables={"history": await cache_service.get_chat_history_service.get_messages_str("User1")}))
        
    # Step 1. Get the action to take from the semantic plugin
    resultAction = await cache_service.get_kernel_service.semantic_plugins["determine_steps"].invoke(input=query, context=kc)
    action_dict = json.loads(resultAction.result)
    action = Action(**action_dict)
        
    # Step 2 - Take the action
    if action.action == "search":
        # Get the response from the last step in the plan
        assistantResponse = (await cache_service.get_kernel_service.query_index_plugin["get_library_query_results"].invoke(input=query, context=kc)).result
    
    if action.action == "synthesize":
        # Get the response from the last step in the plan
        lastQueryResultsJson = await cache_service.get_chat_history_service.get_last_assistant_response("User1")
        assistantResponse = (await cache_service.get_kernel_service.semantic_plugins["generate_synthesis"].invoke(input=lastQueryResultsJson)).result
        cache_service.get_chat_history_service.clear_history("User1")

    if action.action == "None":
        cache_service.get_chat_history_service.clear_history("User1")
        assistantResponse = json.dumps({ "None": {}} )
                               
    # Get the response from the action above and prepare for return...
    chatTurnResponse = assistantResponse
    cache_service.get_logger_service.logger.debug(chatTurnResponse)
    cache_service.get_logger_service.logger.info("Chat Turn Complete! Returning the response...")
            
    # Adding current response to the chat history
    if action.action != "None":
         cache_service.get_chat_history_service.add_message("User1", message={
            "role": "assistant",
            "content": chatTurnResponse
        })
      
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

app.run(debug=True)
