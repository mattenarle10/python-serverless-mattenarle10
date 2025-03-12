import json
from models.product_model import ProductModel
from utils.decimal_encoder import DecimalEncoder
from utils.logger import logger

product_model = ProductModel()

def get_specialized_products(event, context):
    """
    Handler for retrieving specialized product data.
    If no query type is specified, returns all specialized product types in a single response.
    Otherwise, supports query types: most_expensive, least_expensive, most_stock, least_stock
    """
    try:
        # Get query type from query parameters
        query_parameters = event.get('queryStringParameters', {}) or {}
        query_type = query_parameters.get('type')
        
        # If query_type is provided, validate it
        if query_type is not None:
            valid_types = ['most_expensive', 'least_expensive', 'most_stock', 'least_stock', 'best_seller']
            if query_type not in valid_types:
                return {
                    "statusCode": 400,
                    "headers": {
                        "Content-Type": "application/json"
                    },
                    "body": json.dumps({
                        "message": f"Invalid query type. Must be one of: {', '.join(valid_types)}",
                        "valid_types": valid_types
                    })
                }
            logger.info(f"Processing specialized product query for type: {query_type}")
        else:
            logger.info("Processing request for all specialized product types")
        
        # Call the model method to get specialized products
        # If query_type is None, it will return all types in a single response
        return product_model.get_specialized_products(query_type)
        
    except Exception as e:
        logger.error(f"Error in get_specialized_products: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "message": "Error processing specialized product query",
                "error": str(e)
            }, cls=DecimalEncoder)
        }
