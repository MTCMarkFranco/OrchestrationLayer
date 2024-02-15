from flask import g
import json

class chat_history_service:
    def __init__(self):
        self.index = "history"
        self.kernel = g.sk.kernel
    
    async def add_message(self, user_id: str, message):
        
        # TODO: add_message working nicely
        # do the same for the rest of the methods
        collections = await  self.kernel.memory.get_collections()
        if self.index in collections:
            current_message = (await  self.kernel.memory.get(self.index,user_id)).text
            if (current_message is not None):
                current_message_obj = json.loads(current_message)
                current_message_obj.append(message)
            else:
                current_message_obj = [message]
            res = await  self.kernel.memory.save_information(self.index, id=user_id, text=json.dumps(current_message_obj))
        else:
            res = await  self.kernel.memory.save_information(self.index, id=user_id, text=json.dumps([message]))
           
    def get_last_assistant_response(self):
        for i in range(len(self.history) - 1, -1, -1):
            if self.history[i]["role"] == "assistant":
                return self.history[i]["content"]
            
    def get_messages(self):
        return json.dumps(self.history)
    
    def clear_history(self):
        self.history.clear()
        self.history = []   