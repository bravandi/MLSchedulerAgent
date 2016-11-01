import requests
from enum import Enum
from datetime import datetime
import uuid
import json

__server_url = 'http://CinderDevelopmentEnv:8888/'

def insert_volume_request(workload_id, capacity, type, read_iops, write_iops, create_clock = 0, create_time = datetime.now()):

    data = {
        "workload_id": workload_id,
        "capacity": capacity,
        "type": type,
        "read_iops": read_iops,
        "write_iops": write_iops,
        "create_clock": create_clock,
        "create_time": create_time
    }

    return _parse_response(requests.post(__server_url + "insert_volume_request", data=data))


def _parse_response(response):

    return int(response.content)



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
    # print add_volume(
    #     cinder_id=uuid.uuid1(),
    #     backend_id=1,
    #     schedule_response=ScheduleResponse.Accepted,
    #     capacity=1)

    # print add_volume_request(
    #     workload_id=1,
    #     capacity=1,
    #     type=0,
    #     read_iops=500,
    #     write_iops=500
    # )

    q = requests.get(__server_url, data={"zz": 12})

    print q.content

    pass