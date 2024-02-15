import json
import asyncio
import sys
import platform

#local imports
from services.logger_service import logger_proxy
from services.kernel_service import kernel_proxy

if platform.system() == "Windows" and sys.version_info >= (3, 8, 0):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
logger_svc=logger_proxy.get_logger_service()
kernel_svc=kernel_proxy.get_kernel_service()

class chat_history_service:
    def __init__(self):
        self.index = "history"
            
    async def add_message(self, user_id: str, message):
                
        global logger_svc
        global kernel_svc
                
        try:
            current_message = (await kernel_svc.kernel.memory.search(self.index,user_id))[0].text
            current_message_obj = json.loads(current_message)
            current_message_obj.append(message)
        except:
            current_message_obj = [message]
        
        try:
            await  kernel_svc.kernel.memory.save_information(self.index, id=user_id, text=json.dumps(current_message_obj))
        except:
            logger_svc.logger.error(f"Error saving chat history for {user_id}.")
           
    async def get_last_assistant_response(self,user_id: str):
        
        message_history_obj = await self.get_messages(user_id)               
        
        for i in range(len(message_history_obj) - 1, -1, -1):
            if message_history_obj[i]["role"] == "assistant":
                return message_history_obj[i]["content"]
            
    async def get_messages(self,user_id: str):
        
        global logger_svc
        global kernel_svc
        
        try:
            message_history = (await kernel_svc.kernel.memory.search(self.index,user_id))[0].text
            message_history_obj = json.loads(message_history)
            
            
        except:
            message_history_obj = [{}]
                
        return message_history_obj
    
    async def get_messages_str(self,user_id: str):
        
        message_history_obj = await self.get_messages(user_id)
                
        return json.dumps(message_history_obj)
    
    async def clear_history(self,user_id: str):
        
        global logger_svc
        global kernel_svc
        
        try:
            await  kernel_svc.kernel.memory.save_information(self.index, id=user_id, text="[]")
            logger_svc.logger.info(f"Chat history for {user_id} has been cleared.")
        except(Exception):
            logger_svc.logger.warn(f"Chat history excetion: {Exception}.")

class chat_history_proxy:
    
    chat_history_service = chat_history_service()

    @staticmethod
    def get_chat_history_service():
        return chat_history_proxy.chat_history_service

    