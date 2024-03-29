from semantic_kernel.plugin_definition import kernel_function,kernel_function_context_parameter
from semantic_kernel.orchestration.kernel_context import KernelContext
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
import tiktoken
import os
import json
import platform
import asyncio
import sys

# local imports
from services.logger_service import logger_proxy

if platform.system() == "Windows" and sys.version_info >= (3, 8, 0):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
# Service Injection
logger_svc=logger_proxy.get_logger_service()


def current_threshold(numbers) -> float:
    
    if len(numbers) < 2:
        return None

    if numbers == None:
        threshold = None
    else:
        max_drop = float('-inf')
        threshold = float('-inf')

        for i in range(1, len(numbers)):
            drop = numbers[i-1] - numbers[i]
            if drop > max_drop:
                max_drop = drop
                threshold = numbers[i]

    return threshold

class QueryIndexPlugin:
    def __init__(self):
        self.index_name = os.getenv("RECORDS_INDEX_NAME")
        self.api_key = os.getenv("AZURE_AISEARCH_API_KEY")
        self.semntic_config = os.getenv("AZURE_SEARCH_SEMANTIC_CONFIG")
        self.endpoint = os.getenv("AZURE_AISEARCH_URL")
        self.doc_path = os.getenv("DOCUMENT_PATH")
        self.credential = AzureKeyCredential(self.api_key)
        self.tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
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
            
            global logger_svc
            
            #logger_svc = logger_proxy.get_logger_service()
            
            logger_svc.logger.info(f"Querying the index for: {context['input']}...")
            results = self.client.search(search_text=context["input"],
                                         include_total_count=True,
                                         search_fields=["keyphrases","content"],  
                                         select=["metadata_creation_date","metadata_storage_name"],
                                         top=100,
                                         query_caption="extractive",
                                         query_caption_highlight=True,
                                         query_answer="extractive",
                                         search_mode="any",
                                         query_type="semantic",
                                         query_answer_count=3,
                                         query_speller="lexicon",
                                         query_language="en",
                                         semantic_configuration_name=self.semntic_config)
           
 
            # Extract the results and create a dynamic threshold from the reranker scores
            results_list = list(results)
            # reranker_scores = [float(result.get("@search.reranker_score",float('-inf'))) for result in results_list]
            # threshold = current_threshold(reranker_scores)
            records = []
            
            for result in results_list:
                # Filter out results with a reranker score below the threshold
                # Remove this if you want to return all results
                # if threshold is None or result.get("@search.reranker_score") > threshold:
                
                    filename = result.get("metadata_storage_name")
                    captions_summary = ""
                    answers_summary = ""
                    
                    if '@search.captions' in result:
                        captions = result['@search.captions']
                        texts = [caption.text for caption in captions]
                        highlights = [caption.highlights for caption in captions]
                        captions_text = ', '.join(texts)
                        captions_highlights = ', '.join(highlights)
                        captions_summary = captions_highlights if captions_highlights else captions_text
                    
                    if '@search.answers' in result:
                        answers = result['@search.answers']
                        texts = [answer.text for answer in answers]
                        highlights = [answer.highlights for answer in answers]
                        answers_text = ', '.join(texts)
                        answers_highlights = ', '.join(highlights)
                        answers_summary = answers_highlights if answers_highlights else answers_text
                    
                    record = {
                        "publisheddate": result.get("metadata_creation_date"),
                        "filename": filename,
                        "rankedscore": result.get("@search.reranker_score"),
                        "path": self.doc_path,
                        "answers": answers_summary,
                        "captions": captions_summary,
                    }
                    
                    records.append(record)

            recordsObject = {
                "records": records
            }
            
            logger_svc.logger.info(f"formatting results from index...")
            retresultstr = json.dumps(recordsObject)
            logger_svc.logger.info(f"return results from index...")
            #tokens_count = len(list(self.tokenizer.encode(retresultstr)))
            #logger_svc.logger.warn(f"Tokens Count of Payload: {tokens_count + 116} tokens.")
            return retresultstr
        except Exception as e:
            logger_svc.logger.error(f"Error occurred while querying the index: {e}")
            return json.dumps({"error": str(e)})