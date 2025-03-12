from datetime import datetime, timezone
import boto3
import json
from dotenv import load_dotenv
import os
from utils.logger import logger
from utils.decimal_encoder import DecimalEncoder

load_dotenv()
region_name = os.getenv("AWS_REGION")


class DynamoGateway:
    def __init__(self, table_name: str, region_name: str = region_name):
        logger.info(f"Initializing DynamoGateway with table: {table_name}, region: {region_name}")
        self.table_name = table_name
        self.dynamodb = boto3.resource("dynamodb", region_name=region_name)
        self.table = self.dynamodb.Table(self.table_name)
        logger.info(f"DynamoDB table initialized: {self.table.table_name}")

    def get_all_items(self):
        try:
            logger.info(f"Fetching all items from table: {self.table_name}")
            items = []
            response = self.table.scan()
            items.extend(response.get("Items", []))

            while "LastEvaluatedKey" in response:
                response = self.table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
                items.extend(response.get("Items", []))

            logger.info(f"Fetched {len(items)} items from table: {self.table_name}")
            return items
        except Exception as e:
            error_msg = f"Error fetching items: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg)

    def create_item(self, item: dict):
        try:
            logger.info(f"Creating item in table: {self.table_name}")
            logger.debug(f"Item preview: {json.dumps(item, indent=2, cls=DecimalEncoder)}")
            self.table.put_item(Item=item)
            logger.info(f"Item created successfully in table: {self.table_name}")
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({"message": "Item created successfully"}, cls=DecimalEncoder),
            }
        except Exception as e:
            error_msg = f"Failed to create item: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "statusCode": 500,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({"message": "Failed to create item", "error": str(e)}, cls=DecimalEncoder),
            }

    def get_item(self, key: dict):
        try:
            logger.info(f"Fetching item from table: {self.table_name} with key: {key}")
            response = self.table.get_item(Key=key)
            item = response.get("Item", None)
            logger.info(f"Fetched item from table: {self.table_name} with key: {key}")
            return item
        except Exception as e:
            error_msg = f"Error fetching item: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg)

    def delete_item(self, key: dict):
        try:
            logger.info(f"Deleting item from table: {self.table_name} with key: {key}")
            self.table.delete_item(Key=key)
            logger.info(f"Item deleted successfully from table: {self.table_name} with key: {key}")
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({"message": "Item deleted successfully"}, cls=DecimalEncoder),
            }
        except Exception as e:
            error_msg = f"Failed to delete item: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "statusCode": 500,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({"message": "Failed to delete item", "error": str(e)}, cls=DecimalEncoder),
            }

    def update_item(self, key: dict, update_expression: str, expression_values: dict):
        try:
            logger.info(f"Updating item in table: {self.table_name} with key: {key}")
            logger.debug(f"Update expression: {update_expression}")
            logger.debug(f"Expression values: {json.dumps(expression_values, indent=2, cls=DecimalEncoder)}")
            self.table.update_item(
                Key=key,
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
            )
            logger.info(f"Item updated successfully in table: {self.table_name} with key: {key}")
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({"message": "Item updated successfully"}, cls=DecimalEncoder),
            }
        except Exception as e:
            error_msg = f"Failed to update item: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "statusCode": 500,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({"message": "Failed to update item", "error": str(e)}, cls=DecimalEncoder),
            }

    def batch_create_items(self, items: list):
        try:
            logger.info(f"Starting batch create operation for {len(items)} items in table {self.table_name}")
            logger.debug(f"First item preview: {json.dumps(items[0] if items else 'No items', indent=2, cls=DecimalEncoder)}")
            
            successful_items = 0
            failed_items = []
            
            with self.table.batch_writer() as batch:
                for idx, item in enumerate(items, 1):
                    try:
                        logger.debug(f"Writing item {idx}/{len(items)}: {item.get('product_id', 'unknown')}")
                        batch.put_item(Item=item)
                        successful_items += 1
                    except Exception as item_error:
                        logger.error(f"Failed to write item {idx}: {str(item_error)}")
                        failed_items.append({"item": item, "error": str(item_error)})
            
            if failed_items:
                logger.warning(f"Batch create completed with {len(failed_items)} failures")
                logger.debug(f"Failed items: {json.dumps(failed_items, indent=2, cls=DecimalEncoder)}")
            
            logger.info(f"Batch create completed. Success: {successful_items}, Failed: {len(failed_items)}")
            
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "message": f"{successful_items} items created successfully",
                    "failed_items": len(failed_items),
                    "details": failed_items if failed_items else None
                }, cls=DecimalEncoder)
            }
        except Exception as e:
            error_msg = f"Error in batch create: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg)

    def batch_delete_items(self, keys: list):
        try:
            logger.info(f"Starting batch delete operation for {len(keys)} items in table {self.table_name}")
            logger.debug(f"First key preview: {json.dumps(keys[0] if keys else 'No keys', indent=2, cls=DecimalEncoder)}")
            
            successful_items = 0
            failed_items = []
            
            with self.table.batch_writer() as batch:
                for idx, key in enumerate(keys, 1):
                    try:
                        logger.debug(f"Deleting item {idx}/{len(keys)}: {key.get('product_id', 'unknown')}")
                        batch.delete_item(Key=key)
                        successful_items += 1
                    except Exception as item_error:
                        logger.error(f"Failed to delete item {idx}: {str(item_error)}")
                        failed_items.append({"key": key, "error": str(item_error)})
            
            if failed_items:
                logger.warning(f"Batch delete completed with {len(failed_items)} failures")
                logger.debug(f"Failed items: {json.dumps(failed_items, indent=2, cls=DecimalEncoder)}")
            
            logger.info(f"Batch delete completed. Success: {successful_items}, Failed: {len(failed_items)}")
            
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "message": f"{successful_items} items deleted successfully",
                    "failed_items": len(failed_items),
                    "details": failed_items if failed_items else None
                }, cls=DecimalEncoder)
            }
        except Exception as e:
            error_msg = f"Error in batch delete: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg)
        
    def add_stock_entry(self, product_id, quantity, remarks):
        """Adds a stock entry for a product with a timestamp."""
        timestamp = datetime.now(timezone.utc).isoformat() 

        try:
            logger.info(f"Adding stock entry for product: {product_id}")
            logger.debug(f"Stock entry details: product_id={product_id}, quantity={quantity}, remarks={remarks}")
            self.table.put_item(
                Item={
                    "product_id": product_id,
                    "datetime": timestamp,
                    "quantity": quantity,
                    "remarks": remarks,
                }
            )
            logger.info(f"Stock entry added successfully for product: {product_id}")
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({"message": "Stock entry added successfully"}, cls=DecimalEncoder),
            }
        except Exception as e:
            error_msg = f"Failed to add stock entry: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "statusCode": 500,
                "body": json.dumps({"message": "Failed to add stock entry", "error": str(e)}, cls=DecimalEncoder),
            }
        
    def get_stock_entries(self, product_id):
        """Fetch stock entries for a given product_id."""
        try:
            logger.info(f"Fetching stock entries for product: {product_id}")
            response = self.table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key("product_id").eq(product_id)
            )
            items = response.get("Items", [])
            logger.info(f"Fetched {len(items)} stock entries for product: {product_id}")
            return items
        except Exception as e:
            error_msg = f"Error fetching stock entries: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg)
            
    def search_products_by_name(self, product_name):
        """Search for products by name using a scan with filter expression and in-memory filtering."""
        try:
            logger.info(f"Searching for products with name containing: {product_name}")
            # Convert to lowercase for case-insensitive search
            search_term = product_name.lower().strip()
            
            # Get all products first, then filter in memory for case-insensitive matching
            # This is more reliable than depending on DynamoDB's case-sensitive filtering
            logger.info(f"Getting all products to perform case-insensitive search")
            response = self.table.scan()
            all_products = response.get("Items", [])
            
            # Continue scanning if there are more items (pagination)
            while 'LastEvaluatedKey' in response:
                response = self.table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                all_products.extend(response.get("Items", []))
            
            logger.info(f"Retrieved {len(all_products)} total products for filtering")
            
            # Perform in-memory filtering for case-insensitive matching
            filtered_products = []
            for product in all_products:
                product_name_value = product.get("product_name", "")
                if product_name_value and search_term in product_name_value.lower():
                    # Add the product to our filtered list
                    filtered_products.append(product)
            
            # Sort products by relevance (items that have the search term closer to the beginning are more relevant)
            if filtered_products:
                filtered_products.sort(key=lambda x: x.get("product_name", "").lower().find(search_term))
            
            # Further sort by exact beginning matches first
            exact_beginning_matches = []
            other_matches = []
            
            for product in filtered_products:
                product_name_value = product.get("product_name", "").lower()
                if product_name_value.startswith(search_term):
                    exact_beginning_matches.append(product)
                else:
                    other_matches.append(product)
            
            # Combine the results with exact beginning matches first
            sorted_products = exact_beginning_matches + other_matches
            
            logger.info(f"Found {len(sorted_products)} products matching '{product_name}'")
            return sorted_products
        except Exception as e:
            error_msg = f"Error searching for products by name: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg)
