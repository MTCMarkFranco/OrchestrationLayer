import os
import json
import logging
from typing import List
from attr import dataclass
from semantic_kernel.plugin_definition import kernel_function,kernel_function_context_parameter
from semantic_kernel.orchestration.kernel_context import KernelContext
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from flask import jsonify

# Set up logging
logging.basicConfig(filename='app.log', level=logging.INFO)

class QueryIndexPlugin:
    def __init__(self):
        self.service_name = os.getenv("AZURE_SEARCH_SERVICE")
        self.index_name = os.getenv("AZURE_SEARCH_INDEX")
        self.api_key = os.getenv("AZURE_SEARCH_API_KEY")
        self.semntic_config = os.getenv("AZURE_SEARCH_SEMANTIC_CONFIG")
        self.endpoint = f"https://{self.service_name}.search.windows.net/"
        self.credential = AzureKeyCredential(self.api_key)
        self.client = SearchClient(endpoint=self.endpoint,
                                   index_name=self.index_name,
                                   credential=self.credential)

    @kernel_function(
        description="This function interacts with the Azure Search Library index. It sends a query to the index, retrieves the relevant documents based on the query, and processes the results. The function is designed to work with Azure's search service, which allows for efficient search and retrieval of information stored in an Azure index.",
        name="get_library_query_results",
        input_description="The specific query for which the librarian requires additional information."
    )
    @kernel_function_context_parameter(
        name="output",
        description="A JSON object containing a list of documents referenced in the library index that match the query, along with a summary of each document. The JSON object is structured as follows: {\"records\": [{\"publisheddate\": \"2021-01-01\", \"filename\": \"document1.txt\", \"summary\": \"This is a summary of document1.txt\"}, {\"publisheddate\": \"2021-01-02\", \"filename\": \"document2.txt\", \"summary\": \"This is a summary of document2.txt\"}]}"
    )
    def get_library_query_results(self, context: KernelContext) -> str:
        try:
            results = self.client.search(search_text=context["userinput"],
                                         include_total_count=True,
                                         search_fields=["keyphrases"],  
                                         select=["metadata_creation_date","metadata_storage_name","summary"],
                                         top=10,
                                         query_type="semantic",
                                         semantic_configuration_name=self.semntic_config)
            #result_list = [result for result in results]
            records = []
            for result in results:
                # Extract the desired properties from the result
                    
                    record = {
                        "publisheddate": result.get("metadata_creation_date"),
                        "filename": result.get("metadata_storage_name"),
                        "summary": result.get("summary")
                    }
                    
                    records.append(record)

            assistantAction = {
                "records": records,
                "question": context["userinput"]
            }
            
            retresultstr = json.dumps(assistantAction)
            #.encode('utf-8').decode('unicode_escape')
            os.system('cls' if os.name == 'nt' else 'clear')
            print (retresultstr)
            return retresultstr
        except Exception as e:
            logging.error(f"Error occurred while querying the index: {e}")
            return jsonify({"error": str(e)})