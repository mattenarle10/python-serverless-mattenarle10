import logging

def get_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # You can also add a handler for logging to a file or a cloud service if needed
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger
