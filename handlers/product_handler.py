import json, urllib, boto3, csv, os
from models.product_model import get_all_products_model, create_product_model, get_product_model, delete_product_model, modify_product_model, batch_create_products_model
from utils.decimal_encoder import DecimalEncoder
from utils.logger import get_logger
from gateways.sqs_gateway import send_to_sqs


def get_all_products(event, context):
    return_body = get_all_products_model()
    logger.info("Fetching all products")
    response = {
        "statusCode": 200,
        "body": json.dumps(return_body, cls=DecimalEncoder)
    }
    
    return response

def create_product(event, context):
    try:
        body = json.loads(event['body'])
    except json.JSONDecodeError as e:
        return {
            'statusCode': 400,
            'body': json.dumps({'message': 'Invalid JSON in request body', 'error': str(e)})
        }

    product_name = body.get('product_name')
    quantity = body.get('quantity')
    price = body.get('price')
    product_id = body.get('product_id')

    if not all([product_name, quantity, price, product_id]):
        return {
            'statusCode': 400,
            'body': json.dumps({'message': 'Missing required fields'})
        }

    # Create product in the model
    create_response = create_product_model(product_name, quantity, price, product_id)

    sqs = boto3.resource('sqs', region_name='us-east-2')
    queue = sqs.get_queue_by_name(QueueName='products-queue-matt-sqs')
    logger.info(f"Product created: {product_name}, ID: {product_id}")
    
    # Create a new message
    response = queue.send_message(MessageBody=json.dumps(body, cls=DecimalEncoder))

    return create_response

def get_product(event, context):
    product_id = event['pathParameters']['product_id']
    return_body = get_product_model(product_id)
    
    if return_body:
        response = {
            "statusCode": 200,
            "body": json.dumps(return_body, cls=DecimalEncoder)
        }
    else:
        response = {
            "statusCode": 404,
            "body": json.dumps({'message': f'Product with ID {product_id} not found'})
        }
    
    return response

def delete_product(event, context):
    product_id = event['pathParameters']['product_id']
    delete_response = delete_product_model(product_id)
    
    return delete_response

def modify_product(event, context):
    try:
        body = json.loads(event['body'])
    except json.JSONDecodeError as e:
        return {
            'statusCode': 400,
            'body': json.dumps({'message': 'Invalid JSON in request body', 'error': str(e)})
        }

    product_id = event['pathParameters']['product_id']
    product_name = body.get('product_name')
    quantity = body.get('quantity')
    price = body.get('price')

    if not all([product_name, quantity, price]):
        return {
            'statusCode': 400,
            'body': json.dumps({'message': 'Missing required fields'})
        }

    modify_response = modify_product_model(product_id, product_name, quantity, price)
    return modify_response
    
logger = get_logger()

def batch_create_products(event, context):
    try:
        # Debugging print for event received
        logger.info("File uploaded trigger for creation")
        logger.debug(event)
        
        # Extract file location from event payload
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])
        
        # Check if the file is in "for_create" folder
        if not key.startswith("for_create/"):
            logger.info(f"Skipping file {key}, as it's not in 'for_create' folder")
            return {"statusCode": 200, "body": "Not in 'for_create' folder"}

        # Ensure a simple filename for the temporary file
        filename = os.path.basename(key)
        localFilename = f'/tmp/{filename}'
        
        # Initialize S3 client
        s3_client = boto3.client('s3', region_name='us-east-2')
        logger.info(f"Downloading file from S3: {bucket}/{key}")
        
        # Download file to /tmp folder
        s3_client.download_file(bucket, key, localFilename)
        
        # Read CSV file and process products
        with open(localFilename, 'r') as f:
            csv_reader = csv.DictReader(f)
            products_data = []
            
            for row in csv_reader:
                # Gather product data
                products_data.append({
                    'product_id': row['product_id'],
                    'product_name': row['product_name'],
                    'quantity': row['quantity'],
                    'price': row['price']
                })

        # Call batch_create_products_model to insert products into DynamoDB
        response = batch_create_products_model(products_data)
        logger.info(f"Batch create response: {response}")

        return {"statusCode": 200, "body": response['body']}
    
    except Exception as e:
        logger.error(f"Error processing batch create: {str(e)}")
        return {"statusCode": 500, "body": f"Error processing batch create: {str(e)}"}

        
def batch_delete_products(event, context):
    try:
        # Debugging print for event received
        logger.info("File uploaded trigger for deletion")
        logger.debug(event)
        
        # Extract file location from event payload
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])
        
        # Check if the file is in "for_delete" folder
        if not key.startswith("for_delete/"):
            logger.info(f"Skipping file {key}, as it's not in 'for_delete' folder")
            return {"statusCode": 200, "body": "Not in 'for_delete' folder"}

        # Ensure a simple filename for the temporary file
        filename = os.path.basename(key)
        localFilename = f'/tmp/{filename}'
        
        # Initialize S3 client
        s3_client = boto3.client('s3', region_name='us-east-2')
        logger.info(f"Downloading file from S3: {bucket}/{key}")
        
        # Download file to /tmp folder
        s3_client.download_file(bucket, key, localFilename)
        
        # Initialize DynamoDB client
        dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
        table_name = "products-matt-2"  # change this to your DynamoDB table name
        table = dynamodb.Table(table_name)
        
        logger.info("Reading CSV file and deleting products...")
        
        # Open and read the CSV file
        with open(localFilename, 'r') as f:
            csv_reader = csv.DictReader(f)
            
            # Loop through each row and delete the product in DynamoDB
            for row in csv_reader:
                product_id = row.get("product_id")
                if not product_id:
                    logger.warning(f"Skipping row due to missing product_id: {row}")
                    continue
                
                logger.info(f"Attempting to delete product with product_id: {product_id}")
                
                # Delete the product from DynamoDB if it exists
                response = table.get_item(Key={'product_id': product_id})
                if 'Item' in response:
                    logger.info(f"Product found. Deleting product_id: {product_id}")
                    table.delete_item(Key={'product_id': product_id})
                else:
                    logger.info(f"Product with product_id {product_id} does not exist. Skipping deletion.")
        
        logger.info("All done!")
        return {"statusCode": 200, "body": "Batch deletion completed successfully"}
    
    except Exception as e:
        logger.error(f"Error processing batch delete: {str(e)}")
        return {"statusCode": 500, "body": f"Error processing batch delete: {str(e)}"}
        

