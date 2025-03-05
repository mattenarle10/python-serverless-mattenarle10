import boto3
from decimal import Decimal
import json

def get_dynamodb_items(table_name):
    dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
    table = dynamodb.Table(table_name)
    response = table.scan()
    return response.get('Items', [])

def create_product_in_dynamodb(table_name, product_name, quantity, price, product_id):
    dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
    table = dynamodb.Table(table_name)
    
    try:
        table.put_item(
            Item={
                'product_id': product_id,
                'product_name': product_name,
                'quantity': quantity,
                'price': price,
            }
        )
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Product created successfully'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'Failed to create product', 'error': str(e)})
        }

def get_product_from_dynamodb(table_name, product_id):
    dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
    table = dynamodb.Table(table_name)
    try:
        response = table.get_item(Key={'product_id': product_id})
        return response.get('Item', None)
    except Exception as e:
        return None

def delete_product_from_dynamodb(table_name, product_id):
    dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
    table = dynamodb.Table(table_name)
    
    try:
        table.delete_item(Key={'product_id': product_id})
        return {
            'statusCode': 200,
            'body': json.dumps({'message': f'Product {product_id} deleted successfully'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'Failed to delete product', 'error': str(e)})
        }

def modify_product_in_dynamodb(table_name, product_id, product_name, quantity, price):
    dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
    table = dynamodb.Table(table_name)
    
    try:
        table.update_item(
            Key={'product_id': product_id},
            UpdateExpression="SET product_name = :product_name, quantity = :quantity, price = :price",
            ExpressionAttributeValues={
                ':product_name': product_name,
                ':quantity': quantity,
                ':price': price
            }
        )
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Product updated successfully'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'Failed to update product', 'error': str(e)})
        }

def batch_create_products_in_dynamodb(table_name, products_data):
    dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
    table = dynamodb.Table(table_name)
    
    with table.batch_writer() as batch:
        for product in products_data:
            batch.put_item(
                Item={
                    'product_id': product['product_id'],
                    'product_name': product['product_name'],
                    'quantity': product['quantity'],
                    'price': product['price']
                }
            )
    return {
        'statusCode': 200,
        'body': json.dumps({'message': f'{len(products_data)} products created successfully'})
    }

def batch_delete_products_from_dynamodb(table_name, product_ids):
    dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
    table = dynamodb.Table(table_name)
    
    with table.batch_writer() as batch:
        for product_id in product_ids:
            batch.delete_item(Key={'product_id': product_id})
    
    return {
        'statusCode': 200,
        'body': json.dumps({'message': f'{len(product_ids)} products deleted successfully'})
    }

