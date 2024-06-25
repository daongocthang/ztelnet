import os
from datetime import datetime

parent_dir = os.path.join(os.environ['USERPROFILE'], "Documents")


def write(s, directory):
    path = os.path.join(parent_dir, directory)
    if not os.path.exists(path):
        os.mkdir(path)
    str_time = datetime.strftime(datetime.now(), "%Y-%m-%d, %H:%M:%S")
    s = "[{}] {}".format(str_time, s)

    with open(path + "/log.txt", "a", encoding="utf-8") as f:
        f.write(s + '\n')
