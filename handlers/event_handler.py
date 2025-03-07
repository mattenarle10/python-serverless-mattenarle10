from models.event_model import EventModel
from utils.logger import logger
import json

event_model = EventModel()

def setup_inventory_check(event, context):
    """
    Setup a scheduled inventory check
    Example event:
    {
        "schedule": "rate(1 day)"  # or "cron(0 12 * * ? *)" for noon every day
    }
    """
    try:
        body = json.loads(event.get('body', '{}'))
        schedule = body.get('schedule', 'rate(1 day)')
        
        logger.info(f"Setting up inventory check with schedule: {schedule}")
        return event_model.schedule_inventory_check(schedule)
    except Exception as e:
        logger.error(f"Failed to setup inventory check: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": "Failed to setup inventory check",
                "error": str(e)
            })
        }

def check_low_inventory(event, context):
    """
    Check for products with low inventory
    This function can be triggered by EventBridge schedule or called directly via API
    Example event for API:
    {
        "threshold": 10  # Optional, defaults to 10
    }
    """
    try:
        # Handle both EventBridge and API Gateway events
        if 'body' in event:
            # API Gateway event
            body = json.loads(event.get('body', '{}'))
            threshold = int(body.get('threshold', 10))
        else:
            # EventBridge event
            threshold = int(event.get('threshold', 10))
        
        logger.info(f"Checking inventory with threshold: {threshold}")
        return event_model.check_low_inventory(threshold)
    except Exception as e:
        logger.error(f"Failed to check inventory: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": "Failed to check inventory",
                "error": str(e)
            })
        }

def test_event_trigger(event, context):
    """
    Test function to manually trigger EventBridge events
    Example event:
    {
        "source": "custom.products.mattenarle",
        "detail_type": "product-created",
        "detail": {
            "product_id": "test-123",
            "product_name": "Test Product",
            "quantity": 50,
            "price": 29.99
        }
    }
    """
    try:
        body = json.loads(event.get('body', '{}'))
        source = body.get('source', 'custom.test.mattenarle')
        detail_type = body.get('detail_type', 'test-event')
        detail = body.get('detail', {'message': 'This is a test event'})
        
        logger.info(f"Triggering test event: {source} - {detail_type}")
        return event_model.send_test_event(source, detail_type, detail)
    except Exception as e:
        logger.error(f"Failed to trigger test event: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": "Failed to trigger test event",
                "error": str(e)
            })
        }
