from decimal import Decimal
from datetime import datetime
from gateways.sqs_gateway import SQSService 
from gateways.s3_gateway import S3Gateway
from gateways.dynamo_gateway import DynamoGateway
from models.event_model import EventModel
from utils.decimal_encoder import DecimalEncoder
import json, os
from dotenv import load_dotenv
from utils.logger import logger


load_dotenv()
table_name = os.getenv("TABLE_NAME")  
inventory_table_name = os.getenv("INVENTORY_TABLE_NAME")  
bucket_name = os.getenv("S3_BUCKET_NAME")  


class ProductModel:
    def __init__(self, table_name=table_name, inventory_table_name=inventory_table_name, bucket_name=bucket_name):
            self.product_table = DynamoGateway(table_name)  # For product-related operations
            self.inventory_table = DynamoGateway(inventory_table_name)  # For inventory-related operations
            self.s3_gateway = S3Gateway(bucket_name)
            self.sqs_gateway = SQSService()

    def get_all_products(self):
        try:
            items = self.product_table.get_all_items()
            return {"items": items, "status": "success"}
        except Exception as e:
            return self.handle_exception(e, "Failed to fetch products")

    def create_product(self, product_name, quantity, price, product_id):
        # Convert price to Decimal if it's not already
        if not isinstance(price, Decimal):
            price = Decimal(str(price))
        
        product = {
            "product_id": product_id,
            "product_name": product_name,
            "quantity": quantity,
            "price": price,
        }
        
        try:
            # The product is passed to DynamoDB with price as Decimal
            response = self.product_table.create_item(product)
            # Return the response directly as DynamoGateway will handle the JSON serialization
            return response
        except Exception as e:
            return self.handle_exception(e, "Failed to create product")

    def get_product(self, product_id):
        try:
            product = self.product_table.get_item({"product_id": product_id})
            if not product:
                return {"statusCode": 404, "body": {"message": "Product not found"}}

            # Get stock entries and calculate total
            stock_entries = self.inventory_table.get_stock_entries(product_id)
            total_stock = sum(int(entry["quantity"]) for entry in stock_entries) if stock_entries else product.get("quantity", 0)

            # Update product with the correct quantity
            product["quantity"] = total_stock

            # Return the product directly without wrapping in statusCode
            return product

        except Exception as e:
            return self.handle_exception(e, "Failed to fetch product")


    def delete_product(self, product_id):
        try:
            return self.product_table.delete_item({"product_id": product_id})
        except Exception as e:
            return self.handle_exception(e, "Failed to delete product")

    def modify_product(self, product_id, product_name, quantity, price):
        update_expression = "SET product_name = :name, quantity = :quantity, price = :price"
        expression_values = {
            ":name": product_name,
            ":quantity": quantity,
            ":price": price,
        }
        try:
            return self.product_table.update_item(
                key={"product_id": product_id},
                update_expression=update_expression,
                expression_values=expression_values,
            )
        except Exception as e:
            return self.handle_exception(e, "Failed to update product")

    def batch_create_products(self, event):
        try:
            # Get the file from the S3 event
            key = self.s3_gateway.get_file_key_from_event(event)
            logger.info(f"Processing file: {key}")
            
            # Validate file prefix
            if not self.s3_gateway.is_valid_file(key, "for_create/"):
                logger.info(f"Skipping file {key}, as it's not in 'for_create' folder")
                return {"statusCode": 200, "body": "Not in 'for_create' folder"}

            # Download the file and process it
            filename = os.path.basename(key)
            local_filename = f'/tmp/{filename}'
            logger.info(f"Downloading file to {local_filename}")
            self.s3_gateway.download_file(key, local_filename)

            # Read the CSV file and prepare data
            products_data = self.s3_gateway.read_csv(local_filename)
            logger.info(f"Read {len(products_data)} products from CSV")
            logger.debug(f"Products data: {json.dumps(products_data, indent=2)}")

            # Write directly to DynamoDB
            logger.info(f"Writing {len(products_data)} products to DynamoDB table {self.product_table.table_name}")
            response = self.product_table.batch_create_items(products_data)
            logger.info(f"DynamoDB response: {json.dumps(response, indent=2)}")

            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": f"Successfully processed {len(products_data)} products",
                    "response": response
                })
            }
        except Exception as e:
            logger.error(f"Error processing batch create: {str(e)}")
            return self.handle_exception(e, "Failed to create products in batch")

    def batch_delete_products(self, event):
        try:
            # Get the file from the S3 event
            key = self.s3_gateway.get_file_key_from_event(event)
            logger.info(f"Processing delete file: {key}")
            
            # Validate file prefix
            if not self.s3_gateway.is_valid_file(key, "for_delete/"):
                logger.info(f"Skipping file {key}, as it's not in 'for_delete' folder")
                return {"statusCode": 200, "body": "Not in 'for_delete' folder"}

            # Download the file and process it
            filename = os.path.basename(key)
            local_filename = f'/tmp/{filename}'
            logger.info(f"Downloading file to {local_filename}")
            self.s3_gateway.download_file(key, local_filename)

            # Read the CSV file and prepare data
            csv_data = self.s3_gateway.read_csv(local_filename)
            logger.info(f"Read {len(csv_data)} items from CSV")
            
            # Extract product IDs and prepare keys for deletion
            delete_keys = [{'product_id': row['product_id']} for row in csv_data]
            logger.info(f"Preparing to delete {len(delete_keys)} products")
            logger.debug(f"Products to delete: {json.dumps(delete_keys, indent=2)}")

            # Delete directly from DynamoDB
            logger.info(f"Deleting {len(delete_keys)} products from DynamoDB table {self.product_table.table_name}")
            response = self.product_table.batch_delete_items(delete_keys)
            logger.info(f"DynamoDB response: {json.dumps(response, indent=2)}")

            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": f"Successfully deleted {len(delete_keys)} products",
                    "response": response
                })
            }
        except Exception as e:
            logger.error(f"Error processing batch delete: {str(e)}")
            return self.handle_exception(e, "Failed to delete products in batch")
    
    def validate_product_fields(self, fields):
        missing = [field for field, value in fields.items() if not value]
        if missing:
            return {"statusCode": 400, "body": json.dumps({"message": f"Missing required fields: {', '.join(missing)}"})}
        return None

    def handle_exception(self, e, custom_message="An error occurred"):
        logger.error(f"{custom_message}: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps(
                {"message": custom_message, "error": str(e)},
                cls=DecimalEncoder
            )
        }
    
    def add_stock_entry(self, product_id, quantity, remarks):
        try:
            # Get current product details
            product = self.product_table.get_item({"product_id": product_id})
            if not product:
                return {
                    "statusCode": 404,
                    "body": json.dumps({"message": f"Product with ID {product_id} not found"})
                }

            # Add stock entry to the inventory table
            self.inventory_table.add_stock_entry(product_id, quantity, remarks)

            # Fetch current stock entries and calculate the total quantity
            stock_entries = self.inventory_table.get_stock_entries(product_id)
            total_stock = sum(int(entry["quantity"]) for entry in stock_entries)  # Convert Decimal to int

            # Ensure total_stock doesn't go negative
            if total_stock < 0:
                logger.warning(f"Stock adjustment would result in negative inventory for product {product_id}")
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "message": "Cannot reduce stock below 0",
                        "current_stock": total_stock - quantity,
                        "requested_reduction": abs(quantity)
                    })
                }

            # Update the product table with the new total quantity
            update_expression = "SET quantity = :quantity"
            expression_values = {
                ":quantity": total_stock
            }
            
            # Update product quantity
            self.product_table.update_item(
                key={"product_id": product_id},
                update_expression=update_expression,
                expression_values=expression_values
            )

            # Send event to EventBridge
            event_model = EventModel()
            event_entry = {
                'Source': 'custom.inventory.mattenarle',
                'DetailType': 'stock-updated',
                'Detail': json.dumps({
                    'product_id': product_id,
                    'product_name': product.get('product_name'),
                    'quantity_added': quantity,
                    'total_quantity': total_stock,
                    'remarks': remarks,
                    'timestamp': datetime.now().isoformat()
                }, cls=DecimalEncoder),
                'EventBusName': os.getenv('EVENT_BUS_NAME')
            }
            event_model.eventbridge.put_events([event_entry])

            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "Stock entry added successfully",
                    "product_id": product_id,
                    "quantity_added": quantity,
                    "total_quantity": total_stock
                })
            }

        except Exception as e:
            return self.handle_exception(e, "Failed to add stock entry")
            expression_values = {":quantity": Decimal(str(total_stock))}  # Ensure Decimal format for DynamoDB

            self.product_table.update_item(
                key={"product_id": product_id},
                update_expression=update_expression,
                expression_values=expression_values,
            )

            # Check if we need to trigger a low stock alert (threshold set to 10)
            if total_stock <= 10:
                event_model = EventModel()
                event_entry = {
                    'Source': 'custom.inventory.mattenarle',
                    'DetailType': 'low-stock-alert',
                    'Detail': json.dumps({
                        'product_id': product_id,
                        'product_name': product.get('product_name', 'Unknown'),
                        'current_quantity': total_stock,
                        'threshold': 10,
                        'timestamp': datetime.now().isoformat()
                    }),
                    'EventBusName': os.getenv('EVENT_BUS_NAME')
                }
                event_model.eventbridge.put_events([event_entry])
                logger.info(f"Low stock alert triggered for product {product_id}")

            operation = "added to" if quantity > 0 else "removed from"
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": f"Stock {operation} inventory successfully",
                    "total_quantity": total_stock,
                    "adjustment": quantity,
                    "low_stock_alert": total_stock <= 10
                })
            }

        except Exception as e:
            return self.handle_exception(e, "Failed to add stock entry")