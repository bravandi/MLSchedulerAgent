import requests
from enum import Enum
from datetime import datetime
import uuid
import json

__server_url = 'http://CinderDevelopmentEnv:8888/'

class ScheduleResponse(Enum):
    Accepted = 1,
    Capacity = 2,
    IOPS = 3,
    CapacityAndIOPS = 4


def add_volume(cinder_id, backend_id, schedule_response, capacity, create_clock = datetime.now()):

    data = {
        "cinder_id": cinder_id,
        "backend_ID": backend_id,
        "schedule_response_ID": schedule_response,
        "capacity": capacity,
        "create_clock": create_clock
    }

    return requests.post(__server_url + "insert_volume", data=data)


# payload = {'key1': 'value1', 'key2': 'value2'}
# r = requests.get('https://api.github.com/events', payload)
#
# # r.json()
#
# r = requests.post('http://httpbin.org/post', data = {'key':'value'})

# a8098c1a-f86e-11da-bd1a-00112444be1e
# 1c394670-991e-411e-bea1-40f6f22bce31


# r = requests.put('http://httpbin.org/put', data = {'key':'value'})
# r = requests.delete('http://httpbin.org/delete')
# r = requests.head('http://httpbin.org/get')
# r = requests.options('http://httpbin.org/get')

if __name__ == "__main__":
    print add_volume(cinder_id=uuid.uuid1(), backend_id=1, schedule_response=ScheduleResponse.Accepted, capacity=1)