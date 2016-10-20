#/root/fio-2.0.9/fio ~/MLSchedulerAgent/fio/basic.fio

import subprocess

fio_path = "/root/fio-2.0.9/fio"

fio_test_path = "/root/MLSchedulerAgent/fio/"

fio_test_name = 'basic.fio'

volume_path = '/media/volume1/'

with open(fio_test_path + fio_test_name, 'r') as myfile:

    data=myfile.read().split('\n')

    data[1] = "directory="+volume_path

    thefile = open(volume_path + fio_test_name, 'w')

    for item in data:

        thefile.write("%s\n" % item)

    thefile.close()

#directory=/media/volume1/

#/root/fio-2.0.9/fio /root/MLSchedulerAgent/fio/basic.fio --directory=/media/volume1/

p = subprocess.Popen(['/root/fio-2.0.9/fio', '/media/volume1/basic.fio'],#[fio_path, volume_path + fio_test_name],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE)

out, err = p.communicate()

print out
