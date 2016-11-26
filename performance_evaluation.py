import argparse
import tools
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

    def __init__(self, test_path, volume_path, cinder_volume_id, show_output=False):
        """

        :param test_path:
        :param volume_path:
        :param cinder_volume_id:
        :return: IOPS{read, write}
        :return: test duration (float)
        :return: test console output
        """
        # threading.Thread.__init__(self)
        self.test_path = test_path
        self.volume_path = volume_path
        self.cinder_volume_id = cinder_volume_id

        tmp = type('', (object,), {'value': ''})()

        self.last_start_time = tmp
        self.last_end_time = tmp
        self.last_terminate_time = tmp
        self.proc = None
        self.show_output = show_output

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
                  self.last_terminate_time,))

        # tools.log("   Start test for volume: %s Time: %s" %
        #           (self.cinder_volume_id, self.last_start_time))
        self.proc.start()

        # print("ZZZZZZZZZZZZZZZZZ" + self.last_end_time.value)

    def terminate(self, after_seconds):
        self.last_end_time = Array('c', " " * 26)
        self.last_terminate_time = Array('c', str(datetime.now()))

        tools.log(
            type="INFO",
            code="perfeval",
            file_name="performance_evaluation.py",
            function_name="terminate",
            message="TERMINATE After %s seconds VOLUME: %s Time: %s" %
                    (str(after_seconds), self.cinder_volume_id, self.last_terminate_time.value))

        self.proc.terminate()

    def is_alive(self):
        if self.proc == None:
            return False

        return self.proc.is_alive()

    @staticmethod
    def run_f_test(test_instance, last_start_time, last_end_time, last_terminate_time):

        tools.log(
            "   {run_f_test} Time: %s \ncommand: %s" %
            (str(test_instance.last_start_time.value),
             PerformanceEvaluation.fio_bin_path + " " + test_instance.test_path), insert_db=False)

        out, err = tools.run_command(
            ["sudo", PerformanceEvaluation.fio_bin_path, test_instance.test_path], debug=False)

        iops_measured = tools.get_iops_measures_from_fio_output(out)

        # print "test_instance.last_end_time:" + last_end_time.value
        last_end_time.value = str(datetime.now())
        duration = tools.get_time_difference(last_start_time.value, last_end_time.value)

        communication.insert_volume_performance_meter(
            experiment_id=PerformanceEvaluation.experiment["id"],
            sla_violation_id=1,  # 1 means no violation
            nova_id=tools.get_current_tenant_id(),
            cinder_volume_id=test_instance.cinder_volume_id,
            read_iops=iops_measured["read"],
            write_iops=iops_measured["write"],
            duration=float(duration),
            io_test_output="OUTPUT_STD:%s\n ERROR_STD: %s" % (out, err))

        # todo have switch for either saving test results or not
        # if False:
        #     out_file = open(test_instance.volume_path + end_time.strftime("%m-%d-%Y_%H-%M-%S"), 'w')
        #     out_file.write(out)
        #     out_file.close()

        if test_instance.show_output == False:
            out = "SHOW_OUTPUT = False"

        tools.log(" DURATION: %s IOPS: %s VOLUME: %s\n OUTPUT_STD:%s\n ERROR_STD: %s" %
                  (str(duration), str(iops_measured), test_instance.cinder_volume_id, out, err), insert_db=False)
        tools.log("    IOPS %s: duration: %s" % (iops_measured, str(duration)), insert_db=False)
        # return IOPS, difference.total_seconds(), out


class PerformanceEvaluation:
    fio_bin_path = os.path.expanduser("~/fio-2.0.9/fio")
    fio_tests_conf_path = os.path.expanduser("~/MLSchedulerAgent/fio/")
    mount_base_path = '/media/'
    experiment = None
    f_test_instances = {}

    def __init__(self, fio_test_name, current_vm_id, terminate_if_takes, restart_gap, restart_gap_after_terminate,
                 show_fio_output):

        self.fio_test_name = fio_test_name
        self.current_vm_id = current_vm_id
        self.terminate_if_takes = terminate_if_takes
        self.restart_gap = restart_gap
        self.restart_gap_after_terminate = restart_gap_after_terminate
        self.show_fio_output = show_fio_output

        PerformanceEvaluation.experiment = communication.Communication.get_current_experiment()

        communication.insert_tenant(
            experiment_id=PerformanceEvaluation.experiment["id"],
            description=tools.get_current_tenant_description(),
            nova_id=tools.get_current_tenant_id()
        )

        pass

    def fio_test(self, cinder_volume_id, test_name):

        # outside if the if statement, in case the test is changed
        volume_path = "%s%s/" % (PerformanceEvaluation.mount_base_path, cinder_volume_id)
        test_path = volume_path + test_name

        if PerformanceEvaluation.f_test_instances.has_key(cinder_volume_id) == False:
            f_test = FIOTest(test_path=test_path,
                             volume_path=volume_path,
                             cinder_volume_id=cinder_volume_id,
                             show_output=self.show_fio_output)

            PerformanceEvaluation.f_test_instances[cinder_volume_id] = f_test

        f_test = PerformanceEvaluation.f_test_instances[cinder_volume_id]

        if f_test.is_alive():
            difference = tools.get_time_difference(f_test.get_last_start_time())
            # difference = (datetime.now() - f_test.last_start_time).total_seconds()
            # tools.log(" [terminate] because taking more than %s seconds" % difference)

            if difference > self.terminate_if_takes:
                f_test.terminate(self.terminate_if_takes)

                communication.insert_volume_performance_meter(
                    experiment_id=PerformanceEvaluation.experiment["id"],
                    nova_id=tools.get_current_tenant_id(),
                    cinder_volume_id=cinder_volume_id,
                    read_iops=0,
                    write_iops=0,
                    duration=0,
                    terminate_wait=float(difference),
                    io_test_output="TERMINATED [terminate_if_takes: %s]" % str(self.terminate_if_takes))

        else:

            last_end_time = f_test.get_last_end_time()
            last_terminate_time = f_test.get_last_terminate_time()

            # if last_end_time is not None:
            #     tools.log("  ***[f_test.last_end_time DIFFERENCE] %s" %
            #               str(tools.get_time_difference(last_end_time)))

            # have xx seconds gap between restarting the tests
            if last_end_time is not None and tools.get_time_difference(last_end_time) < self.restart_gap:
                return

            # if terminated wait for xx seconds then start the process
            if last_terminate_time is not None and tools.get_time_difference(
                    last_terminate_time) < self.restart_gap_after_terminate:
                return

            # if volume is attached but not mounted yet, or the volume is detached
            if os.path.isdir(volume_path) == False:
                PerformanceEvaluation.f_test_instances.pop(cinder_volume_id)
                return

            try:
            # make sure the test file [*.fio] exists
                if True or os.path.isfile(test_path) == False:

                    with open(PerformanceEvaluation.fio_tests_conf_path + test_name, 'r') as myfile:
                        data = myfile.read().split('\n')
                        myfile.close()

                        data[1] = "directory=" + volume_path

                        volume_test_file = open(test_path, 'w')

                        for item in data:
                            volume_test_file.write("%s\n" % item)

                        volume_test_file.close()

                f_test.start()

            except Exception as err:
                # todo !important make sure the consistency of cached volume ides
                tools.log(
                    type="ERROR",
                    code="perfeval_concurrent_bug",
                    file_name="workload_generator.py",
                    function_name="run_storage_workload_generator",
                    message="could not create the fio test file for workload generator",
                    exception=err)
                return

    def run_fio_test(self):

        while True:

            for volume in tools.get_all_attached_volumes(self.current_vm_id):
                self.fio_test(cinder_volume_id=volume.id,
                              test_name=self.fio_test_name)

            time.sleep(2)

    def report_available_iops(self):

        pass


# print args.accumulate(args.integers)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Volumes QoS performance evaluator.')

    parser.add_argument('--fio_test_name', default="resource_evaluation.fio", metavar='', type=str,
                        required=False,
                        help='Test name for fio')

    parser.add_argument('--terminate_if_takes', metavar='', type=int, required=False, default=150,
                        help='terminates an evaluation if takes more than specified seconds')

    parser.add_argument('--restart_gap', metavar='', type=int, required=False, default=20,
                        help='gap between restarting each fio test')

    parser.add_argument('--restart_gap_after_terminate', metavar='', type=int, required=False, default=50,
                        help='If terminated because of the TERMINATE_IF_TAKES, then restart after specified seconds')

    parser.add_argument('--show_fio_output', type=str, metavar='', required=False, default='False',
                        help='show fio test output')

    args = parser.parse_args()

    p = PerformanceEvaluation(
        current_vm_id=tools.get_current_tenant_id(),

        fio_test_name=args.fio_test_name,
        terminate_if_takes=args.terminate_if_takes,
        restart_gap=args.restart_gap,
        restart_gap_after_terminate=args.restart_gap_after_terminate,
        show_fio_output=tools.str2bool(args.show_fio_output)
    )

    p.run_fio_test()
