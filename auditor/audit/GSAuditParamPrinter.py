import json

def print_param_dict(param_dict, log=None):
    """
    Prints the parameter dictionary containing logic mappings for the GS audit.
    
    Args:
        param_dict (dict): The dictionary containing parameters.
        log (Logger, optional): Optional logger object to record the action.
    """
    print(json.dumps(param_dict, indent=4))
    if log and hasattr(log, 'info'):
        log.info("Printed parameter dictionary.")
