# Package Imports
import semantic_kernel as sk
import platform
import asyncio
import sys
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from azure.core.credentials import AzureKeyCredential
from semantic_kernel.connectors.ai.open_ai import ( AzureTextCompletion, AzureTextEmbedding )


# local imports
from plugins.library.query_index.native_function import QueryIndexPlugin
from services.logger_service import logger_proxy

if platform.system() == "Windows" and sys.version_info >= (3, 8, 0):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
# Service Injection
logger_svc= logger_proxy.get_logger_service()

# Globals
useAzureOpenAI = True

class kernel_service:
    def __init__(self):
        
        global logger_svc     
        
        logger_svc.logger.info("Initializing Semantic Kernel==0.5.1.dev0")
        self.kernel = sk.Kernel()
        
        deployment, api_key, endpoint  = sk.azure_openai_settings_from_dot_env()
        self.kernel.add_chat_service("gpt", AzureChatCompletion(deployment_name=deployment, api_key=api_key, base_url=f"{endpoint}openai/"))    
        #self.kernel.add_text_completion_service("dv", AzureTextCompletion(deployment_name="text-embedding-ada-002", api_key=api_key, endpoint=endpoint))
        #self.kernel.add_text_embedding_generation_service("ada",AzureTextEmbedding(deployment_name="text-embedding-ada-002", endpoint=endpoint,api_key=api_key))

        # Register the memory store with the kernel
        api_key, url = sk.azure_aisearch_settings_from_dot_env()

        # create a new AzureKeyCredential object
        #credential = AzureKeyCredential(api_key)
        #connector = AzureCognitiveSearchMemoryStore(azure_credentials=credential, vector_size=1536, search_endpoint=url) 
        #self.kernel.register_memory_store(memory_store=connector)
        
        # self.kernel.register_memory_store(memory_store=sk.memory.VolatileMemoryStore())
        
         # Load the plugins
        logger_svc.logger.info("Loading Semantic and Native Plugins...")
        self.query_index_plugin = self.kernel.import_plugin(QueryIndexPlugin(), "QueryIndexPlugin")
        self.semantic_plugins = self.kernel.import_semantic_plugin_from_directory("plugins", "library") 
    
class kernel_proxy:
    
    kernel_service = kernel_service()

    @staticmethod
    def get_kernel_service():
        return kernel_proxy.kernel_service

    