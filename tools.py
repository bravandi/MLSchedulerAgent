#babak
import subprocess
# import spur
import pdb
from keystoneauth1.identity import v3
from keystoneauth1 import session
from datetime import datetime
from cinderclient import client as c_client
from novaclient import client as n_client

import os.path

class Configs:

    def __init__(
            self,
            workload_gen_delay_between_workload_generation,
            workload_gen_fio_test_name,
            performance_eval_terminate_if_takes,
            performance_eval_generation_fio_test_name,
            performance_eval_restart_gap,
            performance_eval_restart_gap_after_terminate
            ):

        pass


_current_tenant_id = None

def get_current_tenant_id():
    """

    :return: nova_id        VARCHAR(36)
    """

    if _current_tenant_id is not None:
        return _current_tenant_id

    path = os.path.expanduser("~/tenantid")
    if os.path.isfile(path) == False:

        return None

    with open(path) as data_file:
        return data_file.read(36)

_current_tenant_id = get_current_tenant_id()

# import json
# class Backend():
#
#     save_path = '/root/backend'
#     specifications = {
#         "ip": "10.18.75.xx",
#         "capacity": 1,
#         "id": 0,
#         "cinder_id": "blockXX@lvm",
#         "host_name": "blockXX"
#     }
#
#     def __init__(self):
#         self.load()
#
#         # try:
#         #     if os.path.isfile(self.save_path):
#         #         self.load()
#         #
#         #     else:
#         #         self.save()
#         #
#         # except:
#         #     self.save()
#
#     def load(self):
#
#         with open(self.save_path) as data_file:
#
#             self.specifications = json.load(data_file)
#
#             return
#
#     def save(self):
#         with open(self.save_path, 'w') as outfile:
#
#             json.dump(self.specifications, outfile)

# backend_info = Backend()


def get_iops_measures_from_fio_output(out):

    iops_measured = {
        "read": -2,
        "write": -2
    }

    for line in grep(out, "iops"):
        start_index = line.index("iops=") + 5

        if line[2:line.index(":")].strip() == "read":
            iops_measured["read"] = int(line[start_index:line.index(",", start_index, len(line))])

        if line[2:line.index(":")].strip() == "write":
            iops_measured["write"] = int(line[start_index:line.index(",", start_index, len(line))])

    return iops_measured


def log(message, debug=False):

    print ("\n" + message)


def get_all_attached_volumes(virtual_machine_id, from_nova=True, mount_base_path="/media"):

    if from_nova:
        # returns volume object the volume will be ().id
        nova = get_nova_client()
        return nova.volumes.get_server_volumes(virtual_machine_id)

    else:
        # returns a list of string containing the folders names
        return os.walk(mount_base_path).next()[1]


def get_time_difference(start_time, end_time=None):
    if isinstance(start_time, basestring):
        start_time = convert_string_datetime(start_time)

    if isinstance(end_time, basestring):
        end_time = convert_string_datetime(end_time)

    if end_time is None:
        end_time = datetime.now()

    difference = (end_time - start_time)
    return difference.total_seconds()

def get_session():
    auth = v3.Password(auth_url="http://controller:35357/v3",
                       username='admin',
                       password='ADMIN_PASS',
                       project_name='admin',
                       # user_domain_id = 'default',
                       # project_domain_id = 'default',
                       user_domain_name='default',
                       project_domain_name='default'
                       )


    sess = session.Session(auth=auth, verify='/path/to/ca.cert')

    return sess

def cinder_wait_for_volume_status(volume_id, status, timeout = 0):
    '''

    :param volume_id:
    :param status: only can be one of: creating, available, attaching, in-use, deleting, error, error_deleting, backing-up, restoring-backup, error_restoring, error_extending
    :param timeout:
    :return:
    '''

    # todo validate input or create enumoration Status: creating, available, attaching, in-use, deleting, error, error_deleting, backing-up, restoring-backup, error_restoring, error_extending
    # todo add time out

    cinder = get_cinder_client()

    while True:

        vol_reload = cinder.volumes.get(volume_id)

        if vol_reload.status == status:

            return True


# todo design a proper error management when calling openstack services using client API ies
def get_cinder_client():

    return c_client.Client(2, session=get_session())


def get_nova_client():

    return n_client.Client(2, session=get_session())


def create_sequential_folder(path, folder_name):
    '''

    :param path: For example '/media'
    :param folder_name: base name for the sequence of folders. For example 'vol_'
    :return:
    '''
    out, err = run_command(["sudo", 'ls', path])

    max_folder_count = 0

    if out != '':

        folders = grep(out, openstack=False)

        for folder in folders:

            split_folder = folder.split("_")

            if len(split_folder) == 2:
                if int(split_folder[1]) > max_folder_count:
                    max_folder_count = int(split_folder[1])

    create_path = '/media/' + folder_name + str(max_folder_count + 1)
    out, err = run_command(["sudo", 'mkdir', create_path])

def run_command(parameters, debug=False):
    # shell = spur.SshShell(
    #     hostname="10.18.75.153",
    #     username="root",
    #     private_key_file="/root/keys/vm-test.pem"
    # )
    #
    # result = shell.run(["echo", "-n", "hello"])
    # print(result.output)  # prints hello
    # if parameters[0] != "sudo":
    #     parameters.insert(0, "sudo")

    p = subprocess.Popen(parameters,
                         # [fio_path, volume_path + fio_test_name],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)

    # todo create a centeralized error management here

    out, err = p.communicate()

    if debug:
        print ("\nrun_command:\n" + str(parameters) + "\nOUT -->" + out + "\nERROR --> " + err)

    return out, err


def run_command2(command, debug=False):
    task = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    out = task.stdout.read()
    assert task.wait() == 0

    if debug:
        print ("\nrun_command:\n" + command + "\nOUT -->" + out)

    return out


def check_is_device_mounted_to_volume(volume_id):
    """

    :param volume_id:
    :return: the device name if volume is mounted
    """
    out, err = run_command(["sudo", "df"], debug=False)

    mounted = grep(out, volume_id, openstack=False)

    if len(mounted) > 0:
        # print mounted[0].replace("  ", " ")
        # print mounted[0].split(r' ', mounted[0].replace("  ", " "))
        # print re.split(r' ', mounted[0].strip(' '))
        return mounted[0].split(' ')[0]

    return ''


def convert_string_datetime(input):
    input = input.strip()
    if input == '':
        return None
    else:
        return datetime.strptime(input, "%Y-%m-%d %H:%M:%S.%f")

    return input


def umount_device(device, debug= False):
    out, err = run_command(["sudo", "umount", "-f", "-l", device], debug=False)

    if debug:
        print ("\nrun_command:\n" + "umount " + device + "\nOUT -->" + out)

    if err == "":

        return False

    return True


def grep(input, match = "", openstack = False):
    """ grep equivalent for debugging in pdb """

    output = []

    if isinstance(match, basestring):
        match = [str(match)]

    # in case matchis unicode convert it to str. Openstack client api returns unicode therefore the pattern matching wont work
    if type(match) == list:
        for idx, val in enumerate(match):
            match[idx] = str(val)

    if isinstance(input, basestring):

        lines = input.split('\n')

        for line in lines:
            # if match == '':
            #     output.append(line)

            if any(x in line for x in match):# match in line:
                output.append(line)

    if type(input) is dict:

        for line in ("{" + "\n".join("{}: {}".format(k, v) for k, v in input.items()) + "}"):
            if match == '':
                output.append(line)

            elif any(x in line for x in match):
                output.append(line)

    if(openstack):

        output_properties = {}

        for line in output:

            line_parts = line.split('|')

            if(len(line_parts) > 2):

                output_properties[line_parts[1].strip()] = line_parts[2].strip()

        return output_properties

    return output


def get_mounted_devices(match="vd", debug=False):
    result = set()

    out, err = run_command(["sudo", "df"], debug=debug)
    t = grep(out, match)

    for i in t:
        spl = i.split(' ')
        result.add(spl[0])

    return result


def get_attached_devices(match="vd", debug=False):
    result = set()

    out, err = run_command(["sudo", "fdisk", "-l"], debug=debug)

    t = grep(out, match)

    for i in t:

        spl = i.split(' ')
        tmp = spl[1]

        if tmp != '':
            result.add(tmp[:len(tmp) - 1])

    return result

if __name__ == "__main__":

    print(get_attached_devices())
    pass
