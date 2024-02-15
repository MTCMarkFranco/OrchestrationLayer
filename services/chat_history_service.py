import json
from services.logger_service import logger_proxy
from services.kernel_service import kernel_proxy

logger_svc=logger_proxy.get_logger_service()
kernel_svc=kernel_proxy.get_kernel_service()

class chat_history_service:
    def __init__(self):
        self.index = "history"
            
    async def add_message(self, user_id: str, message):
                

        collections = await  kernel_svc.kernel.memory.get_collections()
        if self.index in collections:
            try:
                current_message = (await  kernel_svc.kernel.memory.get(self.index,user_id)).text
                current_message_obj = json.loads(current_message)
                current_message_obj.append(message)
            except:
                current_message_obj = [message]
            await  kernel_svc.kernel.memory.save_information(self.index, id=user_id, text=json.dumps(current_message_obj))
        else:
            await  kernel_svc.kernel.memory.save_information(self.index, id=user_id, text=json.dumps([message]))
           
    async def get_last_assistant_response(self,user_id: str):
        
        message_history_obj = await self.get_messages(user_id)               
        
        for i in range(len(message_history_obj) - 1, -1, -1):
            if message_history_obj[i]["role"] == "assistant":
                return message_history_obj[i]["content"]
            
    async def get_messages(self,user_id: str):
        
        try:
            message_history = (await  kernel_svc.kernel.memory.get(self.index,user_id)).text
            message_history_obj = json.loads(message_history)
        except:
            message_history_obj = [{}]
                
        return message_history_obj
    
    async def get_messages_str(self,user_id: str):
        
        message_history_obj = await self.get_messages(user_id)
                
        return json.dumps(message_history_obj)
    
    async def clear_history(self,user_id: str):
        
        try:
            await kernel_svc.kernel.memory.delete(self.index,user_id)
            logger_svc.logger.info(f"Chat history for {user_id} has been cleared.")
        except:
            logger_svc.logger.warn(f"Chat history for {user_id} does not exist. Nothing to do...")

class chat_history_proxy:
    
    chat_history_service = chat_history_service()

    @staticmethod
    def get_chat_history_service():
        return chat_history_proxy.chat_history_service

    