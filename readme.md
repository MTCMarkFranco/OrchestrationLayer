# Semantic Kernel API with Microsoft AI Search

This repository contains the source code for an API that leverages Semantic Kernel and Microsoft AI Search to provide advanced search capabilities. The API is designed to deliver high-quality search results and insights by understanding the semantics of the search queries.

## Prerequisites

Before you begin, ensure you have met the following requirements:

* You have installed the latest version of [Node.js](https://nodejs.org/en/download/)
* You have a Windows/Linux/Mac machine.
* You have a basic understanding of JavaScript and Node.js.

## Environment Variables

This project uses environment variables for configuration. These are the environment variables you need to set, which are also listed in the `.env-structure` file:

AZURE_OPENAI_DEPLOYMENT_NAME="" AZURE_OPENAI_ENDPOINT="https://.openai.azure.com/" AZURE_OPENAI_API_KEY="YOUR_KEY" AZURE_AISEARCH_URL="https://.search.windows.net/" RECORDS_INDEX_NAME="" AZURE_SEARCH_SEMANTIC_CONFIG="" AZURE_AISEARCH_API_KEY="YOUR_KEY" DOCUMENT_PATH="https://.blob.core.windows.net/"

Replace the placeholders with your actual data.

## Building the API

To install dependencies, follow these steps:

```bash
npm install
This will install all the necessary dependencies listed in the package.json file.

Running the API
To start the server, follow these steps:

npm start

The server will start running at http://localhost:3000. You can make requests to this server using tools like Postman or curl.

API Endpoints
The API has the following endpoints:

/search: This endpoint accepts POST requests with a JSON body containing the search query. It returns a list of search results.
Contributing to the Project
If you want to contribute to the project, please fork the repository and create a pull request. For major changes, please open an issue first to discuss what you would like to change.

Contact
If you want to contact me you can reach me at <your_email@domain.com>.

License
This project uses the following license: <license_name>.

```

Please replace the placeholders with your actual data.

