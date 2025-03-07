import boto3
import json
from utils.logger import logger
from dotenv import load_dotenv
import os

load_dotenv()

class EventBridgeGateway:
    def __init__(self, region_name="us-east-2"):
        self.client = boto3.client('events', region_name=region_name)
        self.event_bus_name = os.environ.get('EVENT_BUS_NAME', 'default')
        logger.info(f"Initialized EventBridge gateway in region {region_name} using event bus: {self.event_bus_name}")

    def put_events(self, entries):
        """
        Put events to EventBridge
        entries: List of event entries to put
        """
        try:
            # Ensure all entries have the EventBusName set
            for entry in entries:
                if 'EventBusName' not in entry:
                    entry['EventBusName'] = self.event_bus_name
            
            logger.info(f"Putting {len(entries)} events to EventBridge bus: {self.event_bus_name}")
            logger.debug(f"Event entries: {json.dumps(entries, indent=2)}")
            
            response = self.client.put_events(Entries=entries)
            logger.info(f"Successfully put events. Response: {json.dumps(response, indent=2)}")
            return response
        except Exception as e:
            logger.error(f"Failed to put events: {str(e)}", exc_info=True)
            raise

    def create_rule(self, name, schedule_expression, description="", state="ENABLED", event_bus_name=None):
        """
        Create a scheduled rule
        name: Rule name
        schedule_expression: Schedule expression (rate or cron)
        event_bus_name: Optional event bus name, defaults to self.event_bus_name
        """
        try:
            # Use provided event bus name or fall back to default
            bus_name = event_bus_name or self.event_bus_name
            logger.info(f"Creating rule '{name}' with schedule {schedule_expression} on event bus {bus_name}")
            
            # For scheduled rules, we need to use the default event bus
            if schedule_expression.startswith('rate(') or schedule_expression.startswith('cron('):
                bus_name = 'default'
                logger.info(f"Using default event bus for scheduled rule as required by EventBridge")
            
            response = self.client.put_rule(
                Name=name,
                ScheduleExpression=schedule_expression,
                State=state,
                Description=description,
                EventBusName=bus_name
            )
            logger.info(f"Successfully created rule. Response: {json.dumps(response, indent=2)}")
            return response
        except Exception as e:
            logger.error(f"Failed to create rule: {str(e)}", exc_info=True)
            raise
            
    def put_single_event(self, source, detail_type, detail):
        """
        Helper method to put a single event to EventBridge
        source: Event source
        detail_type: Detail type of the event
        detail: Event detail (dictionary)
        """
        try:
            entry = {
                'Source': source,
                'DetailType': detail_type,
                'Detail': json.dumps(detail),
                'EventBusName': self.event_bus_name
            }
            
            logger.info(f"Putting event to EventBridge bus: {self.event_bus_name}")
            logger.debug(f"Event entry: {json.dumps(entry, indent=2)}")
            
            return self.put_events([entry])
        except Exception as e:
            logger.error(f"Failed to put event: {str(e)}", exc_info=True)
            raise
            
    def create_event_pattern_rule(self, name, event_pattern, targets, description="", state="ENABLED"):
        """
        Create a rule with an event pattern
        name: Rule name
        event_pattern: Event pattern as dictionary
        targets: List of targets for the rule
        """
        try:
            logger.info(f"Creating rule '{name}' with event pattern on event bus {self.event_bus_name}")
            logger.debug(f"Event pattern: {json.dumps(event_pattern, indent=2)}")
            
            # Create the rule
            rule_response = self.client.put_rule(
                Name=name,
                EventPattern=json.dumps(event_pattern),
                State=state,
                Description=description,
                EventBusName=self.event_bus_name
            )
            
            # Add targets to the rule
            targets_response = self.client.put_targets(
                Rule=name,
                EventBusName=self.event_bus_name,
                Targets=targets
            )
            
            logger.info(f"Successfully created rule and targets")
            logger.debug(f"Rule response: {json.dumps(rule_response, indent=2)}")
            logger.debug(f"Targets response: {json.dumps(targets_response, indent=2)}")
            
            return {
                'RuleResponse': rule_response,
                'TargetsResponse': targets_response
            }
        except Exception as e:
            logger.error(f"Failed to create rule with event pattern: {str(e)}", exc_info=True)
            raise
            
    def add_targets_to_rule(self, rule_name, targets, event_bus_name=None):
        """
        Add targets to an existing rule
        rule_name: Name of the rule to add targets to
        targets: List of target configurations
        event_bus_name: Optional event bus name, defaults to self.event_bus_name
        """
        try:
            bus_name = event_bus_name or self.event_bus_name
            logger.info(f"Adding {len(targets)} targets to rule '{rule_name}' on event bus {bus_name}")
            logger.debug(f"Targets: {json.dumps(targets, indent=2)}")
            
            response = self.client.put_targets(
                Rule=rule_name,
                EventBusName=bus_name,
                Targets=targets
            )
            
            logger.info(f"Successfully added targets. Response: {json.dumps(response, indent=2)}")
            return response
        except Exception as e:
            logger.error(f"Failed to add targets to rule: {str(e)}", exc_info=True)
            raise
