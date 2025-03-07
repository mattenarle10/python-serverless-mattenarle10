from gateways.eventbridge_gateway import EventBridgeGateway
from gateways.dynamo_gateway import DynamoGateway
from utils.logger import logger
from utils.decimal_encoder import DecimalEncoder
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
table_name = os.getenv("TABLE_NAME")

class EventModel:
    def __init__(self, region_name="us-east-2"):
        self.eventbridge = EventBridgeGateway(region_name)
        self.product_table = DynamoGateway(table_name)

    def schedule_inventory_check(self, schedule_expression):
        """
        Schedule regular inventory checks using EventBridge.
        Note: Scheduled events must use the default event bus.
        """
        try:
            logger.info(f"Setting up inventory check schedule: {schedule_expression}")
            
            # Get the Lambda function ARN from environment or construct it
            function_name = "python-serverless-mattenarle10-dev-checkLowInventory"
            region = os.getenv('AWS_REGION', 'us-east-2')
            account_id = os.getenv('AWS_ACCOUNT_ID', '272898481162')
            lambda_arn = f"arn:aws:lambda:{region}:{account_id}:function:{function_name}"
            
            # Create the rule on the default event bus
            response = self.eventbridge.create_rule(
                name="inventory-check-schedule-mattenarle",
                schedule_expression=schedule_expression,
                description="Regular inventory check for low stock products - mattenarle",
                event_bus_name="default"  # Use default event bus for scheduled events
            )
            
            # Add target to the rule
            target_response = self.eventbridge.add_targets_to_rule(
                rule_name="inventory-check-schedule-mattenarle",
                targets=[
                    {
                        'Id': 'InventoryCheckTarget',
                        'Arn': lambda_arn,
                        'Input': json.dumps({
                            'threshold': 10  # Default threshold
                        })
                    }
                ]
            )
            
            logger.info(f"Successfully set up inventory check schedule: {json.dumps(response, indent=2)}")
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "Inventory check schedule created",
                    "ruleArn": response.get("RuleArn"),
                    "targetResponse": target_response
                })
            }
        except Exception as e:
            logger.error(f"Failed to set up inventory check schedule: {str(e)}")
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "message": "Failed to set up inventory check schedule",
                    "error": str(e)
                })
            }

    def check_low_inventory(self, threshold=10):
        """
        Check for products with low inventory and send alerts
        """
        try:
            logger.info(f"Checking for products with inventory below {threshold}")
            items = self.product_table.get_all_items()
            
            low_stock_items = [
                item for item in items 
                if int(item.get("quantity", 0)) < threshold
            ]
            
            if low_stock_items:
                logger.info(f"Found {len(low_stock_items)} items with low stock")
                # Create event for each low stock item
                entries = [{
                    'Source': 'custom.inventory.mattenarle',
                    'DetailType': 'low-stock-alert',
                    'Detail': json.dumps({
                        'product_id': item['product_id'],
                        'product_name': item['product_name'],
                        'current_quantity': item['quantity'],
                        'threshold': threshold,
                        'timestamp': datetime.now().isoformat()
                    }, cls=DecimalEncoder),
                    'EventBusName': os.getenv('EVENT_BUS_NAME')
                } for item in low_stock_items]
                
                response = self.eventbridge.put_events(entries)
                logger.info(f"Successfully sent low stock alerts: {json.dumps(response, indent=2)}")
                
                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "message": f"Found {len(low_stock_items)} items with low stock",
                        "items": low_stock_items
                    }, cls=DecimalEncoder)
                }
            else:
                logger.info("No items found with low stock")
                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "message": "No items found with low stock"
                    })
                }
        except Exception as e:
            logger.error(f"Failed to check inventory: {str(e)}")
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "message": "Failed to check inventory",
                    "error": str(e)
                })
            }
            
    def send_test_event(self, source, detail_type, detail):
        """
        Send a test event to EventBridge
        """
        try:
            logger.info(f"Sending test event to EventBridge: {source} - {detail_type}")
            
            event_entry = {
                'Source': source,
                'DetailType': detail_type,
                'Detail': json.dumps(detail, cls=DecimalEncoder),
                'EventBusName': os.getenv('EVENT_BUS_NAME')
            }
            
            response = self.eventbridge.put_events([event_entry])
            logger.info(f"Successfully sent test event: {json.dumps(response, indent=2)}")
            
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "Test event sent successfully",
                    "eventBusName": os.getenv('EVENT_BUS_NAME'),
                    "response": response
                })
            }
        except Exception as e:
            logger.error(f"Failed to send test event: {str(e)}")
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "message": "Failed to send test event",
                    "error": str(e)
                })
            }
