import datetime
import inspect

class Logger():
    def __init__(self):
        datetime_stamp = datetime.datetime.now().strftime("%d%m%Y%H%m")
        self.logFile = open(datetime_stamp + '.log', 'w')

    def log(self, text):
        datetime_stamp = datetime.datetime.now().strftime("%d%m%Y%H%m%s")
        line = "[" + datetime_stamp + "] " + inspect.stack()[1][3] + ": " + text + "\n"
        self.logFile.write(line)

    def __del__(self):
        self.logFile.close()