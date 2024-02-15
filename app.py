# Package Imports
from flask import Flask, request, g
from dotenv import dotenv_values
from semantic_kernel.orchestration.context_variables import ContextVariables
import json

# local imports
from models.data_models import Action
from services.logger_service import logger_service
from services.kernel_service import kernel_service
from chat_history_service import chat_history_service
 
# Initialize configuration via .env file
config = dotenv_values(".env")

# Initialize the webserver  
app = Flask(__name__, template_folder="templates", static_folder="static")

# Services Confguration
@app.before_request
def startup():
    if 'g.logger' not in g:
        g.logger = logger_service()
    if 'g.semantic_kernel' not in g:
        g.semantic_kernel = kernel_service()
    if 'g.chat_history' not in g:
        g.chat_history = chat_history_service()

async def processQuery(query):
   
    useAzureOpenAI = True
    chatTurnResponse = None
           
    # Load the plugins
    g.sk.load_plugins()
   
    # adding current question to the chat history
    await g.chathistory.add_message("User1", message={
		"role": "user",
		"content": query
	})
    
    # debug output
    g.logger.debug(g.chathistory.get_messages("User1"))
    
    # Building the Kernel Context for plugins to use
    assistantResponse = None
    kc = g.semantic_kernel.create_new_context(variables=ContextVariables(variables={"history": g.chat_history.get_messages("User1")}))
        
    # Step 1. Get the action to take from the semantic plugin
    resultAction = await  g.semantic_kernel.semantic_plugins["determine_steps"].invoke(input=query, context=kc)
    action_dict = json.loads(resultAction.result)
    action = Action(**action_dict)
        
    # Step 2 - Take the action
    if action.action == "search":
        # Get the response from the last step in the plan
        searchRecords = (await  g.semantic_kernel.query_index_plugin["get_library_query_results"].invoke(input=query, context=kc)).result
        assistantResponse = (await  g.semantic_kernel.semantic_plugins["send_response"].invoke(input=searchRecords, context=kc)).result
    
    if action.action == "synthesize":
        # Get the response from the last step in the plan
        lastQueryResultsJson =  g.chat_history.get_last_assistant_response("User1")
        assistantResponse = (await g.semantic_kernel.semantic_plugins["generate_synthesis"].invoke(input=lastQueryResultsJson)).result
        g.chat_history.clear_history("User1")

    if action.action == "None":
        g.chat_history.clear_history("User1")
        assistantResponse = json.dumps({ "None": {}} )
                               
    # Get the response from the action above and prepare for return...
    chatTurnResponse = assistantResponse
    g.logger.debug(chatTurnResponse)
    g.logger.info("Chat Turn Complete! Returning the response...")
            
    # Adding current response to the chat history
    if action.action != "None":
         g.chat_history.add_message("User1", message={
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