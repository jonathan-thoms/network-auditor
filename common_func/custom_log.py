import logging


class Custom_Log:
    def __init__(self, log_file='test_custom_logs.txt', activity='', level=logging.DEBUG):
        log = logging.getLogger(__name__)
        log.setLevel(level)
        fh = logging.FileHandler(log_file)
        formatter = logging.Formatter(F'{activity} --%(asctime)s -- %(message)s')
        fh.setFormatter(formatter)
        log.addHandler(fh)
        self.log = log

    def release(self):
        for handler in self.log.handlers[:]:
            handler.close()
            self.log.removeHandler(handler)
