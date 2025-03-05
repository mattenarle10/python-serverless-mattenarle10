from gateways.dynamo_gateway import get_dynamodb_items, create_product_in_dynamodb, get_product_from_dynamodb, delete_product_from_dynamodb, modify_product_in_dynamodb, batch_create_products_in_dynamodb, batch_delete_products_from_dynamodb

def get_all_products_model():
    table_name = "products-matt-2"
    items = get_dynamodb_items(table_name)
    return {
        "items": items,
        "status": "success"
    }

def create_product_model(product_name, quantity, price, product_id):
    table_name = "products-matt-2"
    create_response = create_product_in_dynamodb(table_name, product_name, quantity, price, product_id)
    return create_response

def get_product_model(product_id):
    table_name = "products-matt-2"
    product = get_product_from_dynamodb(table_name, product_id)
    return product

def delete_product_model(product_id):
    table_name = "products-matt-2"
    delete_response = delete_product_from_dynamodb(table_name, product_id)
    return delete_response

def modify_product_model(product_id, product_name, quantity, price):
    table_name = "products-matt-2"
    modify_response = modify_product_in_dynamodb(table_name, product_id, product_name, quantity, price)
    return modify_response


def batch_create_products_model(products_data):
    """
    Create products in batch by interacting with DynamoDB.
    `products_data` should be a list of dictionaries with keys like:
    ['product_name', 'quantity', 'price', 'product_id']
    """
    table_name = "products-matt-2"
    
    create_responses = []
    
    # Loop through the products_data and create each product in DynamoDB
    for product in products_data:
        # Call the DynamoDB function to insert product
        create_response = create_product_in_dynamodb(
            table_name,
            product['product_name'],
            product['quantity'],
            product['price'],
            product['product_id']
        )
        create_responses.append(create_response)
    
    return {
        "status": "success",
        "created_products": create_responses
    }

def batch_delete_products_model(product_ids):
    """
    Delete products in batch by interacting with DynamoDB.
    `product_ids` should be a list of product_id values.
    """
    table_name = "products-matt-2"
    delete_responses = []
    
    for product_id in product_ids:
        delete_response = delete_product_from_dynamodb(table_name, product_id)
        delete_responses.append(delete_response)
    
    return {
        "status": "success",
        "deleted_products": delete_responses
    }