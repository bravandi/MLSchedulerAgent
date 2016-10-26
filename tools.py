#babak
import subprocess
# import spur
import pdb
from keystoneauth1.identity import v3
from keystoneauth1 import session

from cinderclient import client as c_client
from novaclient import client as n_client
import re

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
    out, err = run_command(['ls', path])

    max_folder_count = 0

    if out != '':

        folders = grep(out, openstack=False)

        for folder in folders:

            split_folder = folder.split("_")

            if len(split_folder) == 2:
                if int(split_folder[1]) > max_folder_count:
                    max_folder_count = int(split_folder[1])

    create_path = '/media/' + folder_name + str(max_folder_count + 1)
    out, err = run_command(['mkdir', create_path])

def run_command(parameters, debug=False):
    # shell = spur.SshShell(
    #     hostname="10.18.75.153",
    #     username="root",
    #     private_key_file="/root/keys/vm-test.pem"
    # )
    #
    # result = shell.run(["echo", "-n", "hello"])
    # print(result.output)  # prints hello


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
    out, err = run_command(["df"], debug=False)

    mounted = grep(out, volume_id, openstack=False)

    if len(mounted) > 0:
        # print mounted[0].replace("  ", " ")
        # print mounted[0].split(r' ', mounted[0].replace("  ", " "))
        # print re.split(r' ', mounted[0].strip(' '))
        return mounted[0].split(' ')[0]

    return ''


def umount_device(device, debug= False):
    out, err = run_command(["umount", device], debug=False)

    if debug:
        print ("\nrun_command:\n" + "umount " + device + "\nOUT -->" + out)

    if err == "":

        return False

    return True


def grep(input, match = "", openstack = True):
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

if __name__ == "__main__":

    # p.run_fio_test()

    id = grep(
"""
+--------------------------------+--------------------------------------+
| Property                       | Value                                |
+--------------------------------+--------------------------------------+
| attachments                    | []                                   |
| availability_zone              | nova                                 |
| bootable                       | false                                |
| consistencygroup_id            | None                                 |
| created_at                     | 2016-10-20T14:33:33.000000           |
| description                    | None                                 |
| encrypted                      | False                                |
| id                             | 4233f033-6118-4abb-b5fe-4973c0aafd70 |
| metadata                       | {}                                   |
| migration_status               | None                                 |
| multiattach                    | False                                |
| name                           | vol2                                 |
| os-vol-host-attr:host          | None                                 |
| os-vol-mig-status-attr:migstat | None                                 |
| os-vol-mig-status-attr:name_id | None                                 |
| os-vol-tenant-attr:tenant_id   | 666da5edb7dd4ac1a642a1fdd0f0f8f0     |
| replication_status             | disabled                             |
| size                           | 1                                    |
| snapshot_id                    | None                                 |
| source_volid                   | None                                 |
| status                         | creating                             |
| updated_at                     | None                                 |
| user_id                        | 275716005ea14ce8a8e1c4a7c05c6ccc     |
| volume_type                    | None                                 |
+--------------------------------+--------------------------------------+
""", "id")

    # print(id[1].split('|')[2].strip())

    print id