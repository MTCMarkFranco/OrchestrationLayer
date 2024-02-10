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

def check_whole_numbers(lst):
    if all(int(num) == int(lst[0]) for num in lst):
        return None
    return lst

def current_threshold(numbers) -> float:
    
    if len(numbers) < 2:
        return None

    returnNumberORNone = check_whole_numbers(numbers)
    
    if returnNumberORNone == None:
        threshold = None
    else:
        max_drop = float('-inf')
        threshold = float('-inf')

        for i in range(1, len(returnNumberORNone)):
            drop = returnNumberORNone[i-1] - returnNumberORNone[i]
            if drop > max_drop:
                max_drop = drop
                threshold = returnNumberORNone[i]

    return threshold

class QueryIndexPlugin:
    def __init__(self):
        self.service_name = os.getenv("AZURE_SEARCH_SERVICE")
        self.index_name = os.getenv("AZURE_SEARCH_INDEX")
        self.api_key = os.getenv("AZURE_SEARCH_API_KEY")
        self.semntic_config = os.getenv("AZURE_SEARCH_SEMANTIC_CONFIG")
        self.endpoint = f"https://{self.service_name}.search.windows.net/"
        self.credential = AzureKeyCredential(self.api_key)
        self.logger = logging.getLogger("__CHATBOT__")
        self.client = SearchClient(endpoint=self.endpoint,
                                   index_name=self.index_name,
                                   credential=self.credential)

    @kernel_function(
        description="A Native Function to interact with the Azure Search Index to retrieve relevant documents based on the query.",
        name="get_library_query_results",
        input_description="The specific query for which the librarian requires additional information."
    )
    @kernel_function_context_parameter(
        name="output",
        description="A JSON object containing a list of documents referenced in the library index that match the query, along with a summary of each document. The JSON object is structured as follows: {\"records\": [{\"publisheddate\": \"2021-01-01\", \"filename\": \"document1.txt\", \"summary\": \"This is a summary of document1.txt\"}, {\"publisheddate\": \"2021-01-02\", \"filename\": \"document2.txt\", \"summary\": \"This is a summary of document2.txt\"}]}"
    )
    def get_library_query_results(self, context: KernelContext) -> str:
        try:
            self.logger.info(f"Querying the index for: {context['userinput']}...")
            results = self.client.search(search_text=context["userinput"],
                                         include_total_count=True,
                                         search_fields=["keyphrases"],  
                                         select=["metadata_creation_date","metadata_storage_name","summary"],
                                         top=5,
                                         query_type="semantic",
                                         semantic_configuration_name=self.semntic_config)
           
 
            results_list = list(results)
            reranker_scores = [float(result.get("@search.reranker_score",float('-inf'))) for result in results_list]
            threshold = current_threshold(reranker_scores)
            records = []
            
            for result in results_list:
                if threshold is None or result.get("@search.reranker_score") > threshold:
                
                    record = {
                        "publisheddate": result.get("metadata_creation_date"),
                        "filename": result.get("metadata_storage_name"),
                        "summary": result.get("summary"),
                        "relevance": result.get("@search.reranker_score")
                    }
                    
                    records.append(record)

            assistantAction = {
                "records": records,
                "question": context["userinput"]
            }
            
            self.logger.info(f"formatting results from index...")
            retresultstr = json.dumps(assistantAction)
            self.logger.info(f"return results from index...")
            return retresultstr
        except Exception as e:
            self.logger.error(f"Error occurred while querying the index: {e}")
            return jsonify({"error": str(e)})