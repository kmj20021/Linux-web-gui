import boto3
import json

client = boto3.client("bedrock-runtime", region_name="us-east-1")

# 반드시 foundation-model ID가 아닌 inference profile ID 사용 (us. 접두사)
MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

# --- Converse API (권장) ---
response = client.converse(
    modelId=MODEL_ID,
    messages=[{"role": "user", "content": [{"text": "안녕, 자기소개 해줘"}]}],
    inferenceConfig={"maxTokens": 512, "temperature": 0.7},
)
print(response["output"]["message"]["content"][0]["text"])

# --- InvokeModel API ---
body = {
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 512,
    "messages": [{"role": "user", "content": "안녕, 자기소개 해줘"}],
}
response = client.invoke_model(
    modelId=MODEL_ID,
    body=json.dumps(body),
    contentType="application/json",
    accept="application/json",
)
result = json.loads(response["body"].read())
print(result["content"][0]["text"])