import tools
import threading
from datetime import datetime
import communication
import time
import os
from multiprocessing import Process, Array
import pdb

# class FIOTest(threading.Thread):
class FIOTest:
    """

    """

    def __init__(self, fio_bin_path, test_path, volume_path, cinder_volume_id):
        """

        :param fio_bin_path:
        :param test_path:
        :param volume_path:
        :return: IOPS{read, write}
        :return: test duration (float)
        :return: test console output
        """
        # threading.Thread.__init__(self)
        self.fio_bin_path = fio_bin_path
        self.test_path = test_path
        self.volume_path = volume_path
        self.cinder_volume_id = cinder_volume_id

        tmp = type('', (object,),{'value': ''})()

        self.last_start_time = tmp
        self.last_end_time = tmp
        self.last_terminate_time = tmp
        self.proc = None

    def get_last_start_time(self):
        return tools.convert_string_datetime(self.last_start_time.value)

    def get_last_end_time(self):
        return tools.convert_string_datetime(self.last_end_time.value)

    def get_last_terminate_time(self):
        return tools.convert_string_datetime(self.last_terminate_time.value)

    def start(self):
        self.last_start_time = Array('c', str(datetime.now()))
        self.last_end_time = Array('c', " " * 26)
        self.last_terminate_time = Array('c', " " * 26)

        self.proc = Process(
            target=FIOTest.run_f_test,
            args=(self,
                  self.last_start_time,
                  self.last_end_time,
                  self.last_terminate_time, ))

        # tools.log("   Start test for volume: %s Time: %s" %
        #           (self.cinder_volume_id, self.last_start_time))
        self.proc.start()

        # print("ZZZZZZZZZZZZZZZZZ" + self.last_end_time.value)

    def terminate(self):
        self.last_end_time = Array('c', " " * 26)
        self.last_terminate_time = Array('c', str(datetime.now()))

        tools.log("   {terminate} Terminate test for volume: %s Time: %s" %
                  (self.cinder_volume_id, self.last_terminate_time.value))

        self.proc.terminate()

    def is_alive(self):
        if self.proc == None:

            return False

        return self.proc.is_alive()

    @staticmethod
    def run_f_test(test_instance, last_start_time, last_end_time, last_terminate_time):

        tools.log(
            "   {run_f_test} Time: %s \ncommand: %s" %
            (str(test_instance.last_start_time.value), test_instance.fio_bin_path + " " + test_instance.test_path))

        out, err = tools.run_command([test_instance.fio_bin_path, test_instance.test_path], debug=False)
        # out, err = tools.run_command2(self.fio_bin_path + " " + self.test_path, debug=False)
        # out, err = tools.run_command2("/root/fio-2.0.9/fio")

        end_time = datetime.now()

        iops_measured = {}

        for line in tools.grep(out, "iops"):
            start_index = line.index("iops=") + 5
            iops_measured[line[2:line.index(":")].strip()] = int(line[start_index:line.index(",", start_index, len(line))])

        # print "test_instance.last_end_time:" + last_end_time.value
        last_end_time.value = str(datetime.now())

        duration = tools.get_time_difference(last_start_time.value, last_end_time.value)

        out = out + "\nduration: " + str(duration)

        communication.insert_volume_performance_meter(
            experiment_id=1,
            cinder_volume_id=test_instance.cinder_volume_id,
            read_iops=iops_measured["read"],
            write_iops=iops_measured["write"],
            duration=float(duration),
            io_test_output=out)

        # todo have switch for either saving test results or not
        if False:
            out_file = open(test_instance.volume_path + end_time.strftime("%m-%d-%Y_%H-%M-%S.%f"), 'w')
            out_file.write(out)
            out_file.close()

        tools.log("    IOPS %s: duration: %s" %
                  (iops_measured, str(duration)))
        # return IOPS, difference.total_seconds(), out


class PerformanceEvaluation():

    fio_bin_path = "/root/fio-2.0.9/fio"

    fio_tests_conf_path = "/root/MLSchedulerAgent/fio/"

    fio_test_name = 'basic.fio'

    mount_base_path = '/media/'

    current_vm_id = '2aac4553-7feb-4326-9028-bf923c3c88c3'

    cinder_client_path = '/root/python-cinderclient/cinder.py'

    f_test_instances = {}

    def __init__(self):

        pass

    def fio_test(self, cinder_volume_id, test_name):

        # outside if the if statement, in case the test is changed
        volume_path = "%s%s/" % (self.mount_base_path, cinder_volume_id)
        test_path = volume_path + test_name

        if self.f_test_instances.has_key(cinder_volume_id) == False:

            f_test = FIOTest(fio_bin_path=self.fio_bin_path,
                             test_path=test_path,
                             volume_path=volume_path,
                             cinder_volume_id=cinder_volume_id)

            self.f_test_instances[cinder_volume_id] = f_test

        f_test = self.f_test_instances[cinder_volume_id]

        if f_test.is_alive():
            difference = tools.get_time_difference(f_test.get_last_start_time())
            # difference = (datetime.now() - f_test.last_start_time).total_seconds()
            # tools.log(" [terminate] because taking more than %s seconds" % difference)

            if difference > 2000:
                f_test.terminate()

                communication.insert_volume_performance_meter(
                    experiment_id=1,
                    cinder_volume_id=cinder_volume_id,
                    read_iops=0,
                    write_iops=0,
                    duration=0,
                    terminate_wait=float(difference),
                    io_test_output="")

        else:

            last_end_time = f_test.get_last_end_time()
            last_terminate_time = f_test.get_last_terminate_time()

            # if last_end_time is not None:
            #     tools.log("  ***[f_test.last_end_time DIFFERENCE] %s" %
            #               str(tools.get_time_difference(last_end_time)))

            # have 40 seconds gap between restarting the tests
            if last_end_time is not None and tools.get_time_difference(last_end_time) < 10:
                return

            # if terminated wait for 4 seconds then start the process
            if last_terminate_time is not None and tools.get_time_difference(last_terminate_time) < 4:
                return

            # make sure the test file [*.fio] exists
            if True or os.path.isfile(test_path) == False:

                with open(self.fio_tests_conf_path + test_name, 'r') as myfile:
                    data = myfile.read().split('\n')

                    data[1] = "directory=" + volume_path

                    volume_test_file = open(test_path, 'w')

                    for item in data:
                        volume_test_file.write("%s\n" % item)

                    volume_test_file.close()
            # pdb.set_trace()
            f_test.start()

    def run_fio_test(self):

        while True:

            for volume in tools.get_all_attached_volumes(self.current_vm_id):

                self.fio_test(cinder_volume_id=volume.id,
                              test_name=self.fio_test_name)

            time.sleep(2)

    def report_available_iops(self):

        pass

if __name__ == "__main__":

    p = PerformanceEvaluation()

    p.run_fio_test()

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

    # print len(z)

    for line in tools.grep(z, "iops"):

        start = line.index("iops=") + 5
        IOPS[line[2:line.index(":")]] = line[start:line.index(",", start, len(line))]


