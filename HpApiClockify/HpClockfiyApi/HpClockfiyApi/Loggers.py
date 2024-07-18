import logging

def setup_background_logger(log_level='DEBUG'):
    '''
    This function maps the logging data to the /task endpoint logger file 
    '''
    logger = logging.getLogger('background_tasks')
    # logger.setLevel(log_level)

    return logger


def setup_server_logger(log_level='DEBUG'):
    '''
    This function maps the logging data to the / endpoint logger file 
    '''
    # Create a logger for the ServerLog file
    logger = logging.getLogger('server')
    # logger.setLevel(log_level)
    
    return logger
# Call the setup function when the module is imported