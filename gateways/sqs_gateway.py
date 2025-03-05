import boto3
import json
import string
import random
import csv

sqs_client = boto3.client('sqs')
queue_url = "https://sqs.us-east-2.amazonaws.com/272898481162/products-queue-matt-sqs"

def send_to_sqs(product_data):
    try:
        response = sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(product_data)
        )
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Product created and message sent to SQS', 'response': response})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'Error sending message to SQS', 'error': str(e)})
        }


def generate_code(prefix, string_length):
  letters = string.ascii_uppercase
  return prefix + ''.join(random.choice(letters) for i in range(string_length))

def receive_message_from_sqs(event, context):
    print("file uploaded trigger")
    print(event)
    
    fieldnames=["product_id", "product_name", "price", "quantity"]
    
    file_randomized_prefix = generate_code("pycon_", 8)
    file_name = f'/tmp/product_created_{file_randomized_prefix}.csv'
    bucket = "products-sqs-s3bucket-matt"
    object_name = f'product_created_{file_randomized_prefix}.csv'
    
    
    with open(file_name, 'w') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        for payload in event["Records"]:
            json_payload = json.loads(payload["body"])
            writer.writerow(json_payload)

   
    s3_client = boto3.client('s3')
    response = s3_client.upload_file(file_name, bucket, object_name)
        
    print("All done!")
    return {}