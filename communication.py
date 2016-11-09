import requests
import json
from datetime import datetime
import pdb
__server_url = 'http://CinderDevelopmentEnv:8888/'

def insert_volume_request(
        capacity,
        type,
        read_iops,
        write_iops,
        experiment_id=0,
        workload_id=0,
        create_clock=0,
        create_time=None):

    if create_time is None:
        create_time = datetime.now()


    data = {
        "workload_id": workload_id,
        "experiment_id": experiment_id,
        "capacity": capacity,
        "type": type,
        "read_iops": read_iops,
        "write_iops": write_iops,
        "create_clock": create_clock,
        "create_time": create_time
    }

    return _parse_response(requests.post(__server_url + "insert_volume_request", data=data))


def insert_volume_performance_meter(
        experiment_id,
        nova_id,
        cinder_volume_id,
        read_iops,
        write_iops,
        duration,
        io_test_output,
        tenant_id=0,
        volume_id=0,
        backend_id=0,
        sla_violation_id=0,
        terminate_wait=0,
        create_clock=0,
        create_time=None):
    """

    :param experiment_id:
    :param nova_id: if tenant_id is 0 then the procedure will use nova_id to find the tenant id
    :param cinder_volume_id:
    :param read_iops:
    :param write_iops:
    :param duration:
    :param io_test_output:
    :param tenant_id:
    :param volume_id:
    :param backend_id:
    :param sla_violation_id:
    :param terminate_wait:
    :param create_clock:
    :param create_time:
    :return:
    """

    if create_time is None:
        create_time = datetime.now()

    data = {
        "experiment_id": experiment_id,
        "tenant_id": tenant_id,
        "nova_id": nova_id,
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


def delete_volume(
        id=0,
        cinder_id="",
        delete_clock=0,
        delete_time=None):
    """
    Delete either by record id or by the cinder volume id.
    :param id:
    :param cinder_id:
    :param delete_clock:
    :param delete_time:
    :return:
    """

    if delete_time is None:
        delete_time = datetime.now()

    data = {
        "id": id,
        "cinder_id": cinder_id,
        "delete_clock": delete_clock,
        "delete_time": delete_time
    }

    return _parse_response(requests.post(__server_url + "delete_volume", data=data))


def insert_workload_generator(
        tenant_id,
        duration,
        read_iops,
        write_iops,
        command,
        output,
        create_clock=0,
        create_time=None):

    if create_time is None:
        create_time = datetime.now()

    data = {
        "tenant_id": tenant_id,
        "duration": duration,
        "read_iops": read_iops,
        "write_iops": write_iops,
        "command": command,
        "output": output,
        "create_clock": create_clock,
        "create_time": create_time
    }

    return _parse_response(requests.post(__server_url + "insert_workload_generator", data=data))


def insert_tenant(
        experiment_id,
        nova_id,
        create_time=None):

    if create_time is None:
        create_time = datetime.now()

    data = {
        "experiment_id": experiment_id,
        "nova_id": nova_id,
        "create_time": create_time
    }

    return _parse_response(requests.post(__server_url + "insert_tenant", data=data))


def get_current_experiment():
    ex = requests.get(__server_url + "get_current_experiment")

    return json.loads(ex.text)

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

    # print delete_volume(
    #     id=0,
    #     cinder_id="218485af-f6d4-44f9-ad6b-1ee98201568f")

    insert_volume_performance_meter(
        experiment_id=1,
        nova_id="38b4d2ba-7421-4c00-9d0a-ad84137eee26",
        backend_id=0,
        volume_id=0,
        cinder_volume_id='b0705326-375d-4839-b467-a0545a312c92',
        read_iops=500,
        write_iops=500,
        duration=7.68,
        terminate_wait=0,
        sla_violation_id=0,
        io_test_output='')

    # insert_workload_generator(
    #     tenant_id=1,
    #     duration=1,
    #     read_iops=1,
    #     write_iops=1,
    #     command="",
    #     output="")

    # q = requests.get(__server_url + "get_current_experiment", data={"zz": 12})

    # print get_current_experiment()["id"]

    # insert_tenant(
    #     experiment_id=1,
    #     nova_id='38b4d2ba-7421-4c00-9d0a-ad84137eee26'
    #     )

    pass