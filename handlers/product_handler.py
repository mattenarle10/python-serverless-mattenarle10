import json, boto3
from models.product_model import ProductModel
from models.event_model import EventModel
from utils.decimal_encoder import DecimalEncoder
from utils.logger import logger
from datetime import datetime
import os
from decimal import Decimal

product_model = ProductModel()
event_model = EventModel()
event_bus_name = os.getenv('EVENT_BUS_NAME')

def get_all_products(event, context):
    return_body = product_model.get_all_products() 
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
    price = Decimal(str(body.get('price'))) if body.get('price') is not None else None
    product_id = body.get('product_id')

    if not all([product_name, quantity, price, product_id]):
        return {
            'statusCode': 400,
            'body': json.dumps({'message': 'Missing required fields'})
        }

    create_response = product_model.create_product(product_name, quantity, price, product_id)
    
    # Send event to EventBridge
    try:
        event_entry = {
            'Source': 'custom.products.mattenarle',
            'DetailType': 'product-created',
            'Detail': json.dumps({
                'product_id': product_id,
                'product_name': product_name,
                'quantity': quantity,
                'price': price,
                'timestamp': datetime.now().isoformat()
            }, cls=DecimalEncoder),
            'EventBusName': event_bus_name
        }
        event_model.eventbridge.put_events([event_entry])
        logger.info(f"Product created event sent: {product_name}, ID: {product_id}")
    except Exception as e:
        logger.error(f"Failed to send product created event: {str(e)}")

    # Also send to SQS for backward compatibility
    try:
        sqs = boto3.resource('sqs', region_name='us-east-2')
        queue = sqs.get_queue_by_name(QueueName='products-queue-matt-sqs')
        queue.send_message(MessageBody=json.dumps(body, cls=DecimalEncoder))
    except Exception as e:
        logger.error(f"Failed to send message to SQS: {str(e)}")

    return create_response

def get_product(event, context):
    product_id = event['pathParameters']['product_id']
    return_body = product_model.get_product(product_id)
    
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
    delete_response = product_model.delete_product(product_id)
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

    modify_response = product_model.modify_product(product_id, product_name, quantity, price)
    
    # Send event to EventBridge
    try:
        event_entry = {
            'Source': 'custom.products.mattenarle',
            'DetailType': 'product-updated',
            'Detail': json.dumps({
                'product_id': product_id,
                'product_name': product_name,
                'quantity': quantity,
                'price': price,
                'timestamp': datetime.now().isoformat()
            }),
            'EventBusName': event_bus_name
        }
        event_model.eventbridge.put_events([event_entry])
        logger.info(f"Product updated event sent: {product_name}, ID: {product_id}")
    except Exception as e:
        logger.error(f"Failed to send product updated event: {str(e)}")

    return modify_response

def batch_create_products(event, context):
    try:
        logger.info("File uploaded trigger for creation")
        logger.debug(event)
        
        response = product_model.batch_create_products(event)
        
        return {"statusCode": 200, "body": response['body']}
    
    except Exception as e:
        logger.error(f"Error processing batch create: {str(e)}")
        return {"statusCode": 500, "body": f"Error processing batch create: {str(e)}"}

def batch_delete_products(event, context):
    try:
        logger.info("File uploaded trigger for deletion")
        logger.debug(event)
        
        # Delegate the work to ProductModel
        response = product_model.batch_delete_products(event)
        
        return {"statusCode": 200, "body": response['body']}
    
    except Exception as e:
        logger.error(f"Error processing batch delete: {str(e)}")
        return {"statusCode": 500, "body": f"Error processing batch delete: {str(e)}"}
    
def add_stocks_to_product(event, context):
    try:
        body = json.loads(event['body'])
    except json.JSONDecodeError as e:
        return {
            'statusCode': 400,
            'body': json.dumps({'message': 'Invalid JSON in request body', 'error': str(e)})
        }

    product_id = body.get('product_id')  
    quantity = body.get('quantity')
    remarks = body.get('remarks', '')

    if not product_id or quantity is None:
        return {
            'statusCode': 400,
            'body': json.dumps({'message': 'Missing required fields: product_id or quantity'})
        }

    response = product_model.add_stock_entry(product_id, quantity, remarks)
    return response
