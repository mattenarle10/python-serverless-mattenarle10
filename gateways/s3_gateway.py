import boto3
import os
import urllib.parse
import csv
from utils.logger import logger

class S3Gateway:
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self.s3_client = boto3.client('s3', region_name='us-east-2')
    
    def download_file(self, key: str, local_filename: str):
        try:
            logger.info(f"Downloading file from S3: {self.bucket_name}/{key}")
            self.s3_client.download_file(self.bucket_name, key, local_filename)
            return local_filename
        except Exception as e:
            logger.error(f"Error downloading file from S3: {str(e)}")
            raise e
    
    def read_csv(self, local_filename: str):
        try:
            with open(local_filename, 'r') as f:
                csv_reader = csv.DictReader(f)
                return [row for row in csv_reader]
        except Exception as e:
            logger.error(f"Error reading CSV file: {str(e)}")
            raise e

    def get_file_key_from_event(self, event):
        return urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])
    
    def is_valid_file(self, key: str, prefix: str):
        return key.startswith(prefix)
