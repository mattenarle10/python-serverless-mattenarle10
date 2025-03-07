import boto3
import json
import string
import random
import csv
import os
from utils.logger import logger
from dotenv import load_dotenv
from gateways.dynamo_gateway import DynamoGateway

load_dotenv()

SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")  
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")  
TABLE_NAME = os.getenv("TABLE_NAME")  

class SQSService:
    def __init__(self, region="us-east-2"):
        self.sqs_client = boto3.client('sqs', region_name=region)
        self.queue_url = SQS_QUEUE_URL

    def send_to_sqs(self, data):
        try:
            response = self.sqs_client.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(data)
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

    def receive_message_from_sqs(self, event, context):
        try:
            logger.info("=== Starting SQS message processing ===")
            logger.info(f"Environment check - TABLE_NAME: {TABLE_NAME}")
            logger.info(f"Received event with {len(event.get('Records', []))} records")
            
            fieldnames = ["product_id", "product_name", "price", "quantity"]
            file_randomized_prefix = self.generate_code("pycon_", 8)
            file_name = f'/tmp/product_created_{file_randomized_prefix}.csv'
            bucket = S3_BUCKET_NAME
            object_name = f'product_created_{file_randomized_prefix}.csv'
            
            # Initialize DynamoDB gateway
            logger.info(f"Initializing DynamoDB gateway with table: {TABLE_NAME}")
            dynamo_gateway = DynamoGateway(TABLE_NAME)
            
            # Collect all products to be created
            all_products = []
            
            # Process messages and write to CSV
            logger.info("Starting message processing...")
            with open(file_name, 'w') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for idx, payload in enumerate(event["Records"], 1):
                    logger.info(f"Processing record {idx}")
                    try:
                        json_payload = json.loads(payload["body"])
                        logger.debug(f"Message payload: {json.dumps(json_payload)}")
                        
                        if isinstance(json_payload, list):
                            logger.info(f"Found batch of {len(json_payload)} products")
                            for product in json_payload:
                                logger.debug(f"Processing product: {product.get('product_id', 'unknown')}")
                                all_products.append(product)
                                writer.writerow(product)
                        else:
                            logger.debug(f"Processing single product: {json_payload.get('product_id', 'unknown')}")
                            all_products.append(json_payload)
                            writer.writerow(json_payload)
                    except json.JSONDecodeError as je:
                        logger.error(f"Failed to parse message body: {str(je)}")
                        continue
            
            # Write to DynamoDB
            if all_products:
                logger.info(f"Writing {len(all_products)} products to DynamoDB table: {TABLE_NAME}")
                try:
                    batch_response = dynamo_gateway.batch_create_items(all_products)
                    logger.info(f"DynamoDB response: {json.dumps(batch_response)}")
                except Exception as db_error:
                    logger.error(f"DynamoDB write failed: {str(db_error)}")
                    raise db_error
            else:
                logger.warning("No products found to write to DynamoDB")
            
            # Upload CSV to S3
            logger.info(f"Uploading CSV to S3: {bucket}/{object_name}")
            s3_client = boto3.client('s3')
            s3_client.upload_file(file_name, bucket, object_name)
            
            logger.info(f"Successfully processed {len(all_products)} products")
            logger.info("=== SQS message processing completed ===")
            return {}
            
        except Exception as e:
            logger.error(f"Error in receive_message_from_sqs: {str(e)}", exc_info=True)
            return {"statusCode": 500, "body": f"Error: {str(e)}"}

    def generate_code(self, prefix, string_length):
        letters = string.ascii_uppercase
        return prefix + ''.join(random.choice(letters) for i in range(string_length))
