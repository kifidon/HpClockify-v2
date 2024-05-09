import logging

def setup_background_logger(log_level='DEBUG'):
    logger = logging.getLogger('background_tasks')
    logger.setLevel(log_level)

    return logger


def setup_server_logger(log_level='DEBUG'):
    # Create a logger for the ServerLog file
    logger = logging.getLogger('server')
    logger.setLevel(log_level)
    
    return logger
# Call the setup function when the module is imported