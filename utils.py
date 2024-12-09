import random
import string
import json
from bson import json_util,ObjectId

class Utils:
    def generate_code(length):
        # With combination of lower and upper case
        result_str = ''.join(random.choice(string.ascii_letters) for i in range(length))
        # print random string
        print(result_str)
        return result_str

    def encode(obj):

        #Dump loaded BSON to valid JSON string and reload it as dict
        page_sanitized = json.loads(json_util.dumps(obj=obj))
        return page_sanitized