#/root/fio-2.0.9/fio ~/MLSchedulerAgent/fio/basic.fio

import subprocess
import tools
import os
import threading
from datetime import datetime
import time


class FIOTest(threading.Thread):
    """

    """

    def __init__(self, fio_bin_path, test_path, volume_path):
        """

        :param fio_bin_path:
        :param test_path:
        :param volume_path:
        :return: IOPS{read, write}
        :return: test duration (float)
        :return: test console output
        """
        threading.Thread.__init__(self)
        self.fio_bin_path = fio_bin_path
        self.test_path = test_path
        self.volume_path = volume_path

    def run(self):
        start = datetime.now()
        print "start time: " + str(start)

        out, err = tools.run_command([self.fio_bin_path, self.test_path], debug=False)

        end = datetime.now()

        out_file = open(self.volume_path + end.strftime("%m-%d-%Y_%H-%M-%S.%f"), 'w')

        difference = (end - start)

        IOPS = {}

        for line in tools.grep(out, "iops"):
            start = line.index("iops=") + 5
            IOPS[line[2:line.index(":")]] = line[start:line.index(",", start, len(line))]

        out = out + "\nduration: " + str(difference.total_seconds())

        out_file.write(out)

        out_file.close()

        print out
        # return IOPS, difference.total_seconds(), out


class PerformanceEvaluation():

    fio_bin_path = "/root/fio-2.0.9/fio"

    fio_tests_conf_path = "/root/MLSchedulerAgent/fio/"

    fio_test_name = 'basic.fio'

    mount_base_path = '/media/'

    current_vm_id = '2aac4553-7feb-4326-9028-bf923c3c88c3'

    cinder_client_path = '/root/python-cinderclient/cinder.py'

    def __init__(self):

        pass

    def fio_test(self, volume_id, test_name):

        volume_path = "%s%s/" % (self.mount_base_path, volume_id)

        test_path = volume_path + test_name

        with open(self.fio_tests_conf_path + test_name, 'r') as myfile:
            data = myfile.read().split('\n')

            data[1] = "directory=" + volume_path

            volume_test_file = open(test_path, 'w')

            for item in data:
                volume_test_file.write("%s\n" % item)

            volume_test_file.close()

        f_test = FIOTest(fio_bin_path=self.fio_bin_path,
                         test_path=test_path,
                         volume_path=volume_path)
        f_test.start()

    def run_fio_test(self):
        for volume_id in os.walk(p.mount_base_path).next()[1]:

            self.fio_test(volume_id=volume_id,
                          test_name=self.fio_test_name)

    def report_available_iops(self):

        pass

if __name__ == "__main__":

    p = PerformanceEvaluation()

    # p.run_fio_test()

    z = """
job1: (g=0): rw=randrw, bs=4K-4K/4K-4K, ioengine=libaio, iodepth=64
fio-2.0.9
Starting 1 process

job1: (groupid=0, jobs=1): err= 0: pid=4614: Sat Oct 29 17:19:28 2016
  read : io=98676KB, bw=103979KB/s, iops=25994 , runt=   949msec
  write: io=32396KB, bw=34137KB/s, iops=8534 , runt=   949msec
  cpu          : usr=8.86%, sys=59.07%, ctx=4489, majf=0, minf=5
  IO depths    : 1=0.1%, 2=0.1%, 4=0.1%, 8=0.1%, 16=0.1%, 32=0.1%, >=64=99.8%
     submit    : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     complete  : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.1%, >=64=0.0%
     issued    : total=r=24669/w=8099/d=0, short=r=0/w=0/d=0

Run status group 0 (all jobs):
   READ: io=98676KB, aggrb=103978KB/s, minb=103978KB/s, maxb=103978KB/s, mint=949msec, maxt=949msec
  WRITE: io=32396KB, aggrb=34136KB/s, minb=34136KB/s, maxb=34136KB/s, mint=949msec, maxt=949msec

Disk stats (read/write):
  vdb: ios=23390/7699, merge=0/0, ticks=37236/14632, in_queue=51856, util=90.00%

duration: 1.268539
    """
    IOPS = {}

    print len(z)

    for line in tools.grep(z, "iops"):

        start = line.index("iops=") + 5
        IOPS[line[2:line.index(":")]] = line[start:line.index(",", start, len(line))]


