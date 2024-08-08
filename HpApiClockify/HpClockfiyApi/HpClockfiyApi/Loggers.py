import logging
from .settings import LOG_LEVEL, LOGS_DIR
import os

def setup_background_logger(log_level='DEBUG'):
    '''
    This function maps the logging data to the /task endpoint logger file 
    '''
    logger = logging.getLogger('background_tasks')
    logger.setLevel(LOG_LEVEL)

    return logger


def setup_server_logger(log_level='DEBUG'):
    '''
    This function maps the logging data to the / endpoint logger file 
    '''
    # Create a logger for the ServerLog file
    logger = logging.getLogger('server')
    logger.setLevel(LOG_LEVEL)
    
    return logger

def setup_sql_logger(log_level='DEBUG'):
    '''
    This function maps the logging data to the / endpoint logger file 
    '''
    # Create a logger for the ServerLog file
    logger = logging.getLogger('sqlLogger')
    logger.setLevel(LOG_LEVEL)
    
    return logger
# Call the setup function when the module is imported