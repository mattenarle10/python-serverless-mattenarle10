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
            # Add a lowercase version of product_name for case-insensitive search
            "product_name_lower": product_name.lower() if product_name else "",
            # Initialize sales_count to track best sellers
            "sales_count": 0
        }
        
        try:
            # The product is passed to DynamoDB with price as Decimal
            response = self.product_table.create_item(product)
            
            # Create an enhanced response with the created product details
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "message": "Product created successfully",
                    "product": {
                        "product_id": product_id,
                        "product_name": product_name,
                        "quantity": quantity,
                        "price": price,
                        "created_at": datetime.now().isoformat()
                    },
                    "status": "success"
                }, cls=DecimalEncoder)
            }
        except Exception as e:
            return self.handle_exception(e, "Failed to create product")

    def get_product(self, product_id):
        try:
            product = self.product_table.get_item({"product_id": product_id})
            if not product:
                return {
                    "statusCode": 404, 
                    "headers": {
                        "Content-Type": "application/json"
                    },
                    "body": json.dumps({"message": "Product not found"})
                }

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
            # First get the product to capture its name before deleting
            product = self.product_table.get_item({"product_id": product_id})
            
            if not product:
                return {
                    "statusCode": 404,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({
                        "message": f"Product with ID {product_id} not found"
                    }, cls=DecimalEncoder)
                }
                
            product_name = product.get('product_name', 'Unknown')
            
            # Delete the product
            self.product_table.delete_item({"product_id": product_id})
            
            # Return a more detailed response with the deleted product information
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "message": "Product deleted successfully",
                    "deleted_product": {
                        "product_id": product_id,
                        "product_name": product_name
                    }
                }, cls=DecimalEncoder)
            }
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
            # Update the product
            self.product_table.update_item(
                key={"product_id": product_id},
                update_expression=update_expression,
                expression_values=expression_values,
            )
            
            # Return a more detailed response with the updated product information
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "message": "Product updated successfully",
                    "product": {
                        "product_id": product_id,
                        "product_name": product_name,
                        "quantity": quantity,
                        "price": price
                    }
                }, cls=DecimalEncoder)
            }
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
            return {
                "statusCode": 400, 
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({"message": f"Missing required fields: {', '.join(missing)}"})
            }
        return None
        
    def search_products_by_name(self, product_name):
        """
        Search for products by name and return detailed information.
        Format is optimized for Freshchat integration.
        Returns the most relevant single result to avoid duplicates.
        """
        try:
            logger.info(f"Searching for products with name: {product_name}")
            
            # Use the DynamoDB gateway to search for products by name
            # The gateway now returns results sorted by relevance
            products = self.product_table.search_products_by_name(product_name)
            
            if not products:
                logger.info(f"No products found matching name: {product_name}")
                return {
                    "statusCode": 404,
                    "headers": {
                        "Content-Type": "application/json"
                    },
                    "body": json.dumps({"message": f"No products found matching '{product_name}'"})
                }
            
            # Get the most relevant product (first in the sorted list)
            most_relevant_product = products[0]
            product_id = most_relevant_product.get("product_id")
            
            # Get stock entries and calculate total for the most relevant product
            if product_id:
                stock_entries = self.inventory_table.get_stock_entries(product_id)
                # Handle potential Decimal values properly
                try:
                    total_stock = sum(float(entry["quantity"]) for entry in stock_entries) if stock_entries else float(most_relevant_product.get("quantity", 0))
                except (ValueError, TypeError):
                    # Fallback if conversion fails
                    total_stock = most_relevant_product.get("quantity", 0)
                
                # Update product with the correct quantity
                most_relevant_product["quantity"] = total_stock
            
            # For Freshchat compatibility, we'll still include all products in the response
            # but highlight the most relevant one
            enhanced_products = []
            for product in products:
                if product.get("product_id") != product_id:  # Skip the most relevant one as we already processed it
                    pid = product.get("product_id")
                    if pid:
                        stock_entries = self.inventory_table.get_stock_entries(pid)
                        total_stock = sum(int(entry["quantity"]) for entry in stock_entries) if stock_entries else product.get("quantity", 0)
                        product["quantity"] = total_stock
                    enhanced_products.append(product)
            
            # Add the most relevant product at the beginning
            enhanced_products.insert(0, most_relevant_product)
            
            logger.info(f"Found {len(enhanced_products)} products matching '{product_name}', returning most relevant: {most_relevant_product.get('product_name')}")
            
            # Create a response that's easier to use with Freshchat conditions
            # and focuses on the single most relevant result
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    # Include all products for reference, but the first one is the most relevant
                    "products": enhanced_products,
                    "count": len(enhanced_products),
                    "search_term": product_name,
                    # Focus on the most relevant product for Freshchat
                    "product_id": most_relevant_product.get("product_id", ""),
                    "product_name": most_relevant_product.get("product_name", ""),
                    "price": most_relevant_product.get("price", 0),
                    "quantity": most_relevant_product.get("quantity", 0),
                    # Add more specific details about the matched product
                    "matched_product": {
                        "id": most_relevant_product.get("product_id", ""),
                        "name": most_relevant_product.get("product_name", ""),
                        "price": most_relevant_product.get("price", 0),
                        "quantity": most_relevant_product.get("quantity", 0),
                        "available": int(most_relevant_product.get("quantity", 0)) > 0,
                        "price_formatted": f"${float(most_relevant_product.get('price', 0)):,.2f}"
                    },
                    "exact_match": product_name.lower() in most_relevant_product.get("product_name", "").lower(),
                    # Convert array to string for Freshchat compatibility
                    "search_keywords_string": ",".join([p.get("product_name", "").lower() for p in enhanced_products]),
                    # Keep original array for backward compatibility
                    "search_keywords": [p.get("product_name", "").lower() for p in enhanced_products],
                    # Add direct string match for Freshchat comparison
                    "matched_term": product_name,
                    # Add a simple boolean flag for conditions
                    "found": True,
                    # Add a flag indicating this is the most relevant result
                    "is_best_match": True
                }, cls=DecimalEncoder)
            }
            
        except Exception as e:
            return self.handle_exception(e, f"Failed to search for products with name '{product_name}'")

    def handle_exception(self, e, custom_message="An error occurred"):
        logger.error(f"{custom_message}: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps(
                {"message": custom_message, "error": str(e)},
                cls=DecimalEncoder
            )
        }
        
    def buy_product(self, product_id, quantity=1):
        """
        Buy a product by reducing its inventory quantity.
        Returns total cost and updated stock information.
        """
        try:
            # Get current product details
            product = self.product_table.get_item({"product_id": product_id})
            if not product:
                return {
                    "statusCode": 404,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"message": f"Product with ID {product_id} not found"})
                }
            
            # Ensure quantity is a positive number
            quantity = abs(int(quantity))
            if quantity <= 0:
                quantity = 1  # Default to 1 if invalid quantity provided
                
            # Get current stock directly from the product table
            # This ensures consistency when buying by name or ID
            current_stock = int(product.get("quantity", 0))
            
            # Check if enough stock is available
            if current_stock < quantity:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({
                        "message": "Not enough stock available",
                        "available": current_stock,
                        "requested": quantity
                    }, cls=DecimalEncoder)
                }
            
            # Calculate total cost
            price = float(product.get("price", 0))
            total_cost = price * quantity
            
            # Update the product directly with the new quantity and increment sales_count
            new_stock = current_stock - quantity
            
            # Get current sales count or default to 0 if not present
            current_sales = int(product.get("sales_count", 0))
            new_sales = current_sales + quantity
            
            # Update both quantity and sales_count
            update_expression = "SET quantity = :quantity, sales_count = :sales_count"
            expression_values = {
                ":quantity": new_stock,
                ":sales_count": new_sales
            }
            
            # Update product quantity directly
            self.product_table.update_item(
                key={"product_id": product_id},
                update_expression=update_expression,
                expression_values=expression_values
            )
            
            # Add a record of this purchase to the inventory table
            self.inventory_table.add_stock_entry(product_id, -quantity, f"Purchase of {quantity} units")
            
            # Return success response with details
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "message": "Purchase successful",
                    "product": {
                        "product_id": product_id,
                        "product_name": product.get("product_name"),
                        "quantity_purchased": quantity,
                        "price_per_unit": price,
                        "total_cost": total_cost,
                        "remaining_stock": new_stock
                    }
                }, cls=DecimalEncoder)
            }
            
        except Exception as e:
            return self.handle_exception(e, "Failed to process purchase")
    
    def get_specialized_products(self, query_type=None):
        """
        Get specialized product data.
        If query_type is None, returns all specialized product types in a single response.
        Otherwise, returns data for the specified query_type.
        Supported query_types: 'most_expensive', 'least_expensive', 'most_stock', 'least_stock'
        Format is optimized for Freshchat integration.
        """
        try:
            # Get all products
            all_products = self.product_table.get_all_items()
            
            if not all_products:
                return {
                    "statusCode": 404,
                    "headers": {
                        "Content-Type": "application/json"
                    },
                    "body": json.dumps({"message": "No products found"})
                }
            
            # If query_type is None, return all specialized product types
            if query_type is None:
                logger.info("Getting all specialized product data types")
                
                # Create a response with all specialized product types
                result = {}
                
                # Most expensive product
                price_sorted_desc = sorted(all_products, key=lambda x: float(x.get('price', 0)), reverse=True)
                most_expensive = price_sorted_desc[0] if price_sorted_desc else None
                
                # Least expensive product
                price_sorted_asc = sorted(all_products, key=lambda x: float(x.get('price', 0)))
                least_expensive = price_sorted_asc[0] if price_sorted_asc else None
                
                # Most stocked product
                quantity_sorted_desc = sorted(all_products, key=lambda x: int(x.get('quantity', 0)), reverse=True)
                most_stock = quantity_sorted_desc[0] if quantity_sorted_desc else None
                
                # Least stocked product
                quantity_sorted_asc = sorted(all_products, key=lambda x: int(x.get('quantity', 0)))
                least_stock = quantity_sorted_asc[0] if quantity_sorted_asc else None
                
                # Best seller product (highest sales_count)
                sales_sorted = sorted(all_products, key=lambda x: int(x.get('sales_count', 0)), reverse=True)
                best_seller = sales_sorted[0] if sales_sorted else None
                
                # Format the response with all specialized product types
                return {
                    "statusCode": 200,
                    "headers": {
                        "Content-Type": "application/json"
                    },
                    "body": json.dumps({
                        "most_expensive": {
                            "label": "Most Expensive Product",
                            "product": most_expensive,
                            "product_id": most_expensive.get("product_id", "") if most_expensive else "",
                            "product_name": most_expensive.get("product_name", "") if most_expensive else "",
                            "price": most_expensive.get("price", 0) if most_expensive else 0,
                            "quantity": most_expensive.get("quantity", 0) if most_expensive else 0,
                            "price_formatted": f"${float(most_expensive.get('price', 0)):,.2f}" if most_expensive else "$0.00"
                        },
                        "least_expensive": {
                            "label": "Least Expensive Product",
                            "product": least_expensive,
                            "product_id": least_expensive.get("product_id", "") if least_expensive else "",
                            "product_name": least_expensive.get("product_name", "") if least_expensive else "",
                            "price": least_expensive.get("price", 0) if least_expensive else 0,
                            "quantity": least_expensive.get("quantity", 0) if least_expensive else 0,
                            "price_formatted": f"${float(least_expensive.get('price', 0)):,.2f}" if least_expensive else "$0.00"
                        },
                        "most_stock": {
                            "label": "Most Stocked Product",
                            "product": most_stock,
                            "product_id": most_stock.get("product_id", "") if most_stock else "",
                            "product_name": most_stock.get("product_name", "") if most_stock else "",
                            "price": most_stock.get("price", 0) if most_stock else 0,
                            "quantity": most_stock.get("quantity", 0) if most_stock else 0,
                            "price_formatted": f"${float(most_stock.get('price', 0)):,.2f}" if most_stock else "$0.00"
                        },
                        "least_stock": {
                            "label": "Least Stocked Product",
                            "product": least_stock,
                            "product_id": least_stock.get("product_id", "") if least_stock else "",
                            "product_name": least_stock.get("product_name", "") if least_stock else "",
                            "price": least_stock.get("price", 0) if least_stock else 0,
                            "quantity": least_stock.get("quantity", 0) if least_stock else 0,
                            "price_formatted": f"${float(least_stock.get('price', 0)):,.2f}" if least_stock else "$0.00"
                        },
                        "best_seller": {
                            "label": "Best Selling Product",
                            "product": best_seller,
                            "product_id": best_seller.get("product_id", "") if best_seller else "",
                            "product_name": best_seller.get("product_name", "") if best_seller else "",
                            "price": best_seller.get("price", 0) if best_seller else 0,
                            "quantity": best_seller.get("quantity", 0) if best_seller else 0,
                            "sales_count": best_seller.get("sales_count", 0) if best_seller else 0,
                            "price_formatted": f"${float(best_seller.get('price', 0)):,.2f}" if best_seller else "$0.00"
                        }
                    }, cls=DecimalEncoder)
                }
            
            # If query_type is specified, process as before
            logger.info(f"Getting specialized product data: {query_type}")
            
            # Process products based on query_type
            if query_type == 'most_expensive':
                # Sort by price in descending order
                sorted_products = sorted(all_products, key=lambda x: float(x.get('price', 0)), reverse=True)
                result_label = "Most Expensive Product"
            elif query_type == 'least_expensive':
                # Sort by price in ascending order
                sorted_products = sorted(all_products, key=lambda x: float(x.get('price', 0)))
                result_label = "Least Expensive Product"
            elif query_type == 'most_stock':
                # Sort by quantity in descending order
                sorted_products = sorted(all_products, key=lambda x: int(x.get('quantity', 0)), reverse=True)
                result_label = "Most Stocked Product"
            elif query_type == 'least_stock':
                # Sort by quantity in ascending order
                sorted_products = sorted(all_products, key=lambda x: int(x.get('quantity', 0)))
                result_label = "Least Stocked Product"
            elif query_type == 'best_seller':
                # Sort by sales_count in descending order
                sorted_products = sorted(all_products, key=lambda x: int(x.get('sales_count', 0)), reverse=True)
                result_label = "Best Selling Product"
            else:
                return {
                    "statusCode": 400,
                    "headers": {
                        "Content-Type": "application/json"
                    },
                    "body": json.dumps({"message": f"Invalid query type: {query_type}"})
                }
            
            # Get the top result
            top_product = sorted_products[0] if sorted_products else None
            
            if not top_product:
                return {
                    "statusCode": 404,
                    "headers": {
                        "Content-Type": "application/json"
                    },
                    "body": json.dumps({"message": "No matching products found"})
                }
            
            # Format response for Freshchat compatibility
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "query_type": query_type,
                    "result_label": result_label,
                    "product": top_product,
                    "product_id": top_product.get("product_id", ""),
                    "product_name": top_product.get("product_name", ""),
                    "price": top_product.get("price", 0),
                    "quantity": top_product.get("quantity", 0),
                    "price_formatted": f"${float(top_product.get('price', 0)):,.2f}"
                }, cls=DecimalEncoder)
            }
            
        except Exception as e:
            return self.handle_exception(e, f"Failed to get specialized product data: {query_type}")
    
    def check_stock(self, product_id):
        """
        Check the current stock level of a product.
        """
        try:
            # Get current product details
            product = self.product_table.get_item({"product_id": product_id})
            if not product:
                return {
                    "statusCode": 404,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"message": f"Product with ID {product_id} not found"})
                }
            
            # Get current stock directly from the product table for consistency
            current_stock = int(product.get("quantity", 0))
            
            # Get availability status
            availability = "In Stock"
            if current_stock <= 0:
                availability = "Out of Stock"
            elif current_stock <= 10:
                availability = "Low Stock"
            
            # Return stock information
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "product": {
                        "product_id": product_id,
                        "product_name": product.get("product_name"),
                        "current_stock": current_stock,
                        "price": product.get("price"),
                        "availability": availability,
                        "formatted_price": f"${float(product.get('price', 0)):,.2f}"
                    }
                }, cls=DecimalEncoder)
            }
            
        except Exception as e:
            return self.handle_exception(e, "Failed to check stock")
    
    def add_stock_entry(self, product_id, quantity, remarks):
        try:
            # Get current product details
            product = self.product_table.get_item({"product_id": product_id})
            if not product:
                return {
                    "statusCode": 404,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"message": f"Product with ID {product_id} not found"}, cls=DecimalEncoder)
                }
            
            # Get current stock before making changes
            current_stock_entries = self.inventory_table.get_stock_entries(product_id)
            current_total_stock = sum(int(entry["quantity"]) for entry in current_stock_entries) if current_stock_entries else int(product.get("quantity", 0))
            
            # For purchases (negative quantity), check if there's enough stock
            if quantity < 0 and current_total_stock < abs(quantity):
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({
                        "message": "Not enough stock available",
                        "available": current_total_stock,
                        "requested": abs(quantity)
                    }, cls=DecimalEncoder)
                }

            # Add stock entry to the inventory table
            self.inventory_table.add_stock_entry(product_id, quantity, remarks)

            # Fetch updated stock entries and calculate the new total quantity
            stock_entries = self.inventory_table.get_stock_entries(product_id)
            total_stock = sum(int(entry["quantity"]) for entry in stock_entries) if stock_entries else 0

            # Ensure total_stock doesn't go negative (extra safety check)
            if total_stock < 0:
                logger.warning(f"Stock adjustment would result in negative inventory for product {product_id}")
                # Revert the entry we just added by adding the opposite quantity
                self.inventory_table.add_stock_entry(product_id, -quantity, f"Reverting invalid stock adjustment: {remarks}")
                
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({
                        "message": "Cannot reduce stock below 0",
                        "current_stock": current_total_stock,
                        "requested_reduction": abs(quantity)
                    }, cls=DecimalEncoder)
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

            # Get product name for the response
            product_name = product.get('product_name', 'Unknown')
            
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "message": "Stock entry added successfully",
                    "product_id": product_id,
                    "product_name": product_name,
                    "quantity_added": quantity,
                    "remarks": remarks, 
                    "total_quantity": total_stock
                }, cls=DecimalEncoder)
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