import json
import logging
import os
import requests
from dotenv import load_dotenv

logger = logging.getLogger()
logger.setLevel(logging.INFO)

load_dotenv()
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

def params_to_dict(p):
    if isinstance(p, dict):
        return p
    if isinstance(p, list):
        return {d.get("name"): d.get("value") for d in p if isinstance(d, dict)}
    return {}

def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event, indent=2)}")

    action_group = event.get("actionGroup")
    api_path = event.get("apiPath")
    http_method = event.get("httpMethod")
    operation_id = "searchWeb"

    logger.info(f"Extracted from event - Action Group: {action_group}, API Path: {api_path}, HTTP Method: {http_method}")
    logger.info(f"Using hardcoded OperationId: {operation_id}")

    query = "complex physics formula"
    try:
        request_body = event.get('requestBody', {})
        content = request_body.get('content', {})
        application_json_content = content.get('application/json', {})
        properties_list = application_json_content.get('properties', [])

        extracted_query = None
        for prop in properties_list:
            if isinstance(prop, dict) and prop.get('name') == 'query':
                extracted_query = prop.get('value')
                break

        if extracted_query:
            query = extracted_query
        elif event.get("parameters"):
            fallback_query = params_to_dict(event.get("parameters")).get("query")
            if fallback_query:
                query = fallback_query
    except Exception as e:
        logger.error(f"Error extracting query from event: {e}")

    logger.info(f"Determined query (for logging): {query}")

    # 呼叫 Serper API
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {"q": query}
    try:
        serper_response = requests.post("https://google.serper.dev/search", headers=headers, json=payload)
        serper_data = serper_response.json()
        # 取前3筆結果摘要
        if "organic" in serper_data:
            results = serper_data["organic"][:5]
            summary = "\n".join([f"{item['title']}: {item['link']}" for item in results])
        else:
            summary = "查無搜尋結果"
    except Exception as e:
        logger.error(f"Serper API 呼叫失敗: {e}")
        summary = f"搜尋失敗: {e}"

    response_body_content = {
        'TEXT': {
            'body': summary
        }
    }
    logger.info(f"Constructed responseBody content: {json.dumps(response_body_content)}")

    action_group_result = {
        "actionGroupName": action_group,
        "apiPath": api_path,
        "httpMethod": http_method,
        "function": operation_id,
        "functionResponse": {
            "responseBody": response_body_content
        }
    }
    logger.info(f"Constructed actionGroupResult: {json.dumps(action_group_result, indent=2)}")

    if action_group is None or api_path is None or http_method is None or operation_id is None:
        logger.warning("One or more required fields (actionGroupName, apiPath, httpMethod, operationId) are None!")

    final_response = {
        "messageVersion": "1.0",
        "response": {
            "actionGroupInvocationResults": [action_group_result]
        }
    }
    logger.info(f"Final response for API Schemas: {json.dumps(final_response, indent=2)}")

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(final_response)
    }

if __name__ == "__main__":
    with open("test_event.json", "r", encoding="utf-8") as f:
        event = json.load(f)
    result = lambda_handler(event, None)
    # 直接印出 body 裡的內容
    body = json.loads(result["body"])
    text = body["response"]["actionGroupInvocationResults"][0]["functionResponse"]["responseBody"]["TEXT"]["body"]
    print(text)
