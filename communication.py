import requests
from datetime import datetime

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


def insert_volume_performance_meter(experiment_id, cinder_volume_id, read_iops, write_iops, duration, io_test_output, volume_id=0, backend_id=0, sla_violation_id=0, terminate_wait=0, create_clock=0, create_time=datetime.now()):

    data = {
        "experiment_id": experiment_id,
        "backend_id": backend_id,
        "volume_id": volume_id,
        "cinder_volume_id": cinder_volume_id,
        "read_iops": read_iops,
        "write_iops": write_iops,
        "duration": duration,
        "sla_violation_id": sla_violation_id,
        "io_test_output": io_test_output,
        "terminate_wait": terminate_wait,
        "create_clock": create_clock,
        "create_time": create_time
    }

    return _parse_response(requests.post(__server_url + "insert_volume_performance_meter", data=data))


def delete_volume(id=0, cinder_id="", delete_clock=0, delete_time=datetime.now()):
    data = {
        "id": id,
        "cinder_id": cinder_id,
        "delete_clock": delete_clock,
        "delete_time": delete_time
    }

    return _parse_response(requests.post(__server_url + "delete_volume", data=data))


def _parse_response(response):

    try:
        return int(response.content)
    except ValueError:

        return response


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

    # print delete_volume(id=0, cinder_id="218485af-f6d4-44f9-ad6b-1ee98201568f")

    insert_volume_performance_meter(
        experiment_id=1,
        backend_id=0,
        volume_id=0,
        cinder_volume_id='b0705326-375d-4839-b467-a0545a312c92',
        read_iops=500,
        write_iops=500,
        duration=7.68,
        terminate_wait=0,
        sla_violation_id=0,
        io_test_output='')

    # q = requests.get(__server_url, data={"zz": 12})

    pass