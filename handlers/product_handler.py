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
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(return_body, cls=DecimalEncoder)
    }
    
    return response

def create_product(event, context):
    try:
        body = json.loads(event['body'])
    except json.JSONDecodeError as e:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'message': 'Invalid JSON in request body', 'error': str(e)})
        }

    product_name = body.get('product_name')
    quantity = body.get('quantity')
    price = Decimal(str(body.get('price'))) if body.get('price') is not None else None
    product_id = body.get('product_id')

    if not all([product_name, quantity, price, product_id]):
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json'
            },
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
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps(return_body, cls=DecimalEncoder)
        }
    else:
        response = {
            "statusCode": 404,
            "headers": {
                "Content-Type": "application/json"
            },
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
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'message': 'Invalid JSON in request body', 'error': str(e)})
        }

    product_id = event['pathParameters']['product_id']
    product_name = body.get('product_name')
    quantity = int(body.get('quantity')) if body.get('quantity') is not None else None
    price = Decimal(str(body.get('price'))) if body.get('price') is not None else None

    if not all([product_name, quantity, price]):
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json'
            },
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
            }, cls=DecimalEncoder),
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
        
        # Check if response is already a string or needs to be serialized
        if isinstance(response, dict) and 'body' in response:
            # Add headers if not present
            if 'headers' not in response:
                response['headers'] = {
                    'Content-Type': 'application/json'
                }
            return response
        else:
            return {
                "statusCode": 200, 
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps(response, cls=DecimalEncoder)
            }
    
    except Exception as e:
        logger.error(f"Error processing batch create: {str(e)}")
        return {
            "statusCode": 500, 
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({"message": f"Error processing batch create: {str(e)}"}, cls=DecimalEncoder)
        }

def batch_delete_products(event, context):
    try:
        logger.info("File uploaded trigger for deletion")
        logger.debug(event)
        
        # Delegate the work to ProductModel
        response = product_model.batch_delete_products(event)
        
        # Check if response is already a string or needs to be serialized
        if isinstance(response, dict) and 'body' in response:
            # Add headers if not present
            if 'headers' not in response:
                response['headers'] = {
                    'Content-Type': 'application/json'
                }
            return response
        else:
            return {
                "statusCode": 200, 
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps(response, cls=DecimalEncoder)
            }
    
    except Exception as e:
        logger.error(f"Error processing batch delete: {str(e)}")
        return {
            "statusCode": 500, 
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({"message": f"Error processing batch delete: {str(e)}"}, cls=DecimalEncoder)
        }
    
def add_stocks_to_product(event, context):
    try:
        body = json.loads(event['body'])
    except json.JSONDecodeError as e:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'message': 'Invalid JSON in request body', 'error': str(e)}, cls=DecimalEncoder)
        }

    product_id = body.get('product_id')  
    remarks = body.get('remarks', '')
    
    # Convert quantity to integer, handling string input from Freshchat
    try:
        quantity = int(body.get('quantity'))
    except (ValueError, TypeError) as e:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'message': 'Invalid quantity value. Must be a number.',
                'error': str(e)
            }, cls=DecimalEncoder)
        }

    if not product_id:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'message': 'Missing required field: product_id'}, cls=DecimalEncoder)
        }

    response = product_model.add_stock_entry(product_id, quantity, remarks)
    return response

def search_products_by_name(event, context):
    """
    Handler for searching products by name
    """
    try:
        # Get the product name from query parameters
        query_parameters = event.get('queryStringParameters', {})
        if not query_parameters or 'name' not in query_parameters:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({'message': 'Missing required query parameter: name'})
            }
        
        product_name = query_parameters.get('name')
        logger.info(f"Searching for products with name: {product_name}")
        
        # Call the model function to search for products
        response = product_model.search_products_by_name(product_name)
        
        # Return the response directly as it's already properly formatted
        return response
        
    except Exception as e:
        logger.error(f"Error searching for products by name: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'message': 'Error searching for products', 
                'error': str(e)
            }, cls=DecimalEncoder)
        }

def buy_product(event, context):
    """
    Handler for buying a product (reducing inventory)
    Supports both product ID and product name
    """
    try:
        # Check if we have a product_id in the path parameters
        path_parameters = event.get('pathParameters', {})
        query_parameters = event.get('queryStringParameters', {})
        
        # Get quantity from query parameters (optional, defaults to 1)
        quantity = 1  # Default quantity
        if query_parameters and 'quantity' in query_parameters:
            try:
                quantity = int(query_parameters.get('quantity'))
            except ValueError:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json'
                    },
                    'body': json.dumps({'message': 'Invalid quantity parameter, must be a number'}, cls=DecimalEncoder)
                }
        
        # First check if we have a product_id in the path
        if path_parameters and 'product_id' in path_parameters:
            product_identifier = path_parameters.get('product_id')
            is_product_id = True
            logger.info(f"Processing purchase for product ID: {product_identifier}, quantity: {quantity}")
        # Then check if we have a product_name in the query parameters
        elif query_parameters and 'product_name' in query_parameters:
            product_identifier = query_parameters.get('product_name')
            is_product_id = False
            logger.info(f"Processing purchase for product name: {product_identifier}, quantity: {quantity}")
        # If neither, return an error
        else:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'message': 'Missing required parameter: either product_id in path or product_name in query'
                }, cls=DecimalEncoder)
            }
        
        # Call the appropriate model function based on what we received
        if is_product_id:
            response = product_model.buy_product(product_identifier, quantity)
        else:
            # Search for the product by name first
            search_response = product_model.search_products_by_name(product_identifier)
            
            # If the search was successful and returned a product
            if search_response.get('statusCode') == 200:
                search_data = json.loads(search_response.get('body', '{}'))
                if search_data.get('found', False) and search_data.get('product_id'):
                    # Use the found product_id to buy the product
                    product_id = search_data.get('product_id')
                    response = product_model.buy_product(product_id, quantity)
                else:
                    response = {
                        'statusCode': 404,
                        'headers': {
                            'Content-Type': 'application/json'
                        },
                        'body': json.dumps({
                            'message': f"No product found matching name: {product_identifier}"
                        }, cls=DecimalEncoder)
                    }
            else:
                # Pass through the search error response
                response = search_response
        
        # Return the response directly as it's already properly formatted
        return response
        
    except Exception as e:
        logger.error(f"Error processing purchase: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'message': 'Error processing purchase', 
                'error': str(e)
            }, cls=DecimalEncoder)
        }

def check_stock(event, context):
    """
    Handler for checking product stock levels
    Supports both product ID and product name
    """
    try:
        # Check if we have a product_id in the path parameters
        path_parameters = event.get('pathParameters', {})
        query_parameters = event.get('queryStringParameters', {})
        
        # First check if we have a product_id in the path
        if path_parameters and 'product_id' in path_parameters:
            product_identifier = path_parameters.get('product_id')
            is_product_id = True
            logger.info(f"Checking stock for product ID: {product_identifier}")
        # Then check if we have a product_name in the query parameters
        elif query_parameters and 'product_name' in query_parameters:
            product_identifier = query_parameters.get('product_name')
            is_product_id = False
            logger.info(f"Checking stock for product name: {product_identifier}")
        # If neither, return an error
        else:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'message': 'Missing required parameter: either product_id in path or product_name in query'
                }, cls=DecimalEncoder)
            }
        
        # Call the appropriate model function based on what we received
        if is_product_id:
            response = product_model.check_stock(product_identifier)
        else:
            # Search for the product by name first
            search_response = product_model.search_products_by_name(product_identifier)
            
            # If the search was successful and returned a product
            if search_response.get('statusCode') == 200:
                search_data = json.loads(search_response.get('body', '{}'))
                if search_data.get('found', False) and search_data.get('product_id'):
                    # Use the found product_id to check stock
                    product_id = search_data.get('product_id')
                    response = product_model.check_stock(product_id)
                else:
                    response = {
                        'statusCode': 404,
                        'headers': {
                            'Content-Type': 'application/json'
                        },
                        'body': json.dumps({
                            'message': f"No product found matching name: {product_identifier}"
                        }, cls=DecimalEncoder)
                    }
            else:
                # Pass through the search error response
                response = search_response
        
        # Return the response directly as it's already properly formatted
        return response
        
    except Exception as e:
        logger.error(f"Error checking stock: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'message': 'Error checking stock', 
                'error': str(e)
            }, cls=DecimalEncoder)
        }

def verify_admin(event, context):
    """
    Simple admin verification endpoint with fixed credentials
    """
    try:
        # Parse request body for credentials
        try:
            body = json.loads(event.get('body', '{}'))
        except json.JSONDecodeError as e:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'message': 'Invalid JSON in request body', 
                    'error': str(e)
                }, cls=DecimalEncoder)
            }
        
        # Get admin_id and password from request body
        admin_id = body.get('admin_id', '')
        password = body.get('password', '')
        
        # Fixed admin credentials - in production, use a more secure approach
        valid_admin_id = "adminEV2025"
        valid_password = "springvalley2025"
        
        # Check if credentials match
        if admin_id == valid_admin_id and password == valid_password:
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'message': 'Admin verification successful',
                    'valid': True,
                    'admin_id': admin_id,
                    'access_level': 'admin'
                }, cls=DecimalEncoder)
            }
        else:
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'message': 'Invalid admin credentials',
                    'valid': False
                }, cls=DecimalEncoder)
            }
        
    except Exception as e:
        logger.error(f"Error verifying admin: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'message': 'Error verifying admin', 
                'error': str(e)
            }, cls=DecimalEncoder)
        }
