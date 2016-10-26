#/root/fio-2.0.9/fio ~/MLSchedulerAgent/fio/basic.fio

import subprocess
import tools

class PerformanceEvaluation():


    fio_path = "/root/fio-2.0.9/fio"

    fio_test_path = "/root/MLSchedulerAgent/fio/"

    fio_test_name = 'basic.fio'

    volume_path = '/media/volume1/'

    current_vm_id = '2aac4553-7feb-4326-9028-bf923c3c88c3'

    cinder_client_path = '/root/python-cinderclient/cinder.py'

    def __init__(self):

        pass

    def run_fio_test(self):

        with open(self.fio_test_path + self.fio_test_name, 'r') as myfile:

            data = myfile.read().split('\n')

            data[1] = "directory=" + self.volume_path

            thefile = open(self.volume_path + self.fio_test_name, 'w')

            for item in data:

                thefile.write("%s\n" % item)

            thefile.close()

            p = subprocess.Popen(['/root/fio-2.0.9/fio', '/media/volume1/basic.fio'],
                                 # [fio_path, volume_path + fio_test_name],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)

        out, err = p.communicate()

        print out

    def report_available_iops(self):

        pass

#directory=/media/volume1/

#/root/fio-2.0.9/fio /root/MLSchedulerAgent/fio/basic.fio --directory=/media/volume1/

# nova volume-attach 2aac4553-7feb-4326-9028-bf923c3c88c3 4233f033-6118-4abb-b5fe-4973c0aafd70

# mkdir /media/volume2
# sudo mkfs -t ext3 /dev/vdc
# mount /dev/vdc /media/volume2

if __name__ == "__main__":

    p = PerformanceEvaluation

    # p.run_fio_test()

    id = tools.grep_d(
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

    print(id)