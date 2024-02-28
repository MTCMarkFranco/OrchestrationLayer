# Package Imports
import websockets
from geventwebsocket.handler import WebSocketHandler
from dotenv import dotenv_values
import asyncio
import sys
import platform
import json

# local imports
from models.data_models import Action
from services.kernel_service import kernel_proxy
from services.logger_service import logger_proxy

if platform.system() == "Windows" and sys.version_info >= (3, 8, 0):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
# Service Injection
kernel_svc = kernel_proxy.get_kernel_service()
logger_svc= logger_proxy.get_logger_service()

# Initialize configuration via .env file
config = dotenv_values(".env")

def generateSynthesis(records):
    global kernel_svc
    global logger_svc

    # Get the response stream from the last step in the plan
    return kernel_svc.semantic_plugins["generate_synthesis"].invoke_stream(input=json.dumps(records))

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
 

async def chat(websocket, path):
    async for payload in websocket:
        payload_string = json.loads(payload)
        
        if(payload_string is not None and payload_string['generate_synthesis'] == True):
            try:
                answer = generateSynthesis(payload_string['records'])
                async for message in answer:
                    print(str(message[0]))
                    await websocket.send(str(message[0]))
            except Exception as e:
                print(e)
                await websocket.send({'error': 'Error Getting results from Index'})    
        else:
            query = message['messages'][0]['text']
            output = await processQuery(query)
            if output is None:
                await websocket.send('error', {'error': 'Error Getting results from Index'})
            else:
                await websocket.send(output)

# Initialize the webserver
logger_svc.logger.info("Starting webSockets on port 5000...")  
start_server = websockets.serve(chat, "localhost", 5000)
logger_svc.logger.info("Starting webSockets on port 5000...done! Listening for connections...")    
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()