# Package Imports
from flask import Flask, request
from dotenv import dotenv_values
import asyncio
import sys
import platform
import json

# local imports
from models.data_models import Action
from services.kernel_service import kernel_proxy
from services.logger_service import logger_proxy

# Initialize the webserver  
app = Flask(__name__, template_folder="templates", static_folder="static")

if platform.system() == "Windows" and sys.version_info >= (3, 8, 0):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
# Service Injection
kernel_svc = kernel_proxy.get_kernel_service()
logger_svc= logger_proxy.get_logger_service()

# Initialize configuration via .env file
config = dotenv_values(".env")


async def generateSynthesis(records):

    global kernel_svc
    global logger_svc

    # Get the response from the last step in the plan
    chatTurnAPIResponse = (await kernel_svc.semantic_plugins["generate_synthesis"].invoke(input=json.dumps(records))).result
                               
    # Get the response from the action above and prepare for return...
    logger_svc.logger.debug(chatTurnAPIResponse)
    logger_svc.logger.info("Chat Turn Complete! Returning Synthesis...")
      
    return chatTurnAPIResponse

async def processQuery(query):
       
    global kernel_svc
    global logger_svc
        
    # Step 1 - Take the action
    # Get the response from the last step in the plan
    chatTurnAPIResponse = (await kernel_svc.query_index_plugin["get_library_query_results"].invoke(input=query)).result
                                   
    # Get the response from the action above and prepare for return...
    logger_svc.logger.debug(chatTurnAPIResponse)
    logger_svc.logger.info("Chat Turn Complete! Returning the records...")
      
    return chatTurnAPIResponse
 
@app.route("/")
def root():
    return "Hello. chat API here to help you!"

@app.route('/chat', methods=['OPTIONS'])
def options():
    return {'Allow' : 'GET, POST, OPTIONS'}, 200, \
    { 'Access-Control-Allow-Origin': '*', \
      'Access-Control-Allow-Methods' : 'POST, OPTIONS', \
      'Access-Control-Allow-Headers' : 'Content-Type' }
       
@app.route("/chat", methods=["POST"])
async def chat():
        
    body = request.get_json()
    records = body['records']
    
    if(records is None):
        query = body['messages'][0]['text']
        output = await processQuery(query)
    else:
        output = await generateSynthesis(records)
        
    if output is None:
        return {"error": "Error Getting results from Index" }, 400, {'Access-Control-Allow-Origin': '*'}
    else:
        return output, 200, {'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json'}