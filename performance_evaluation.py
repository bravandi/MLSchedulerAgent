import argparse
import tools
from datetime import datetime
import communication
import time
import os
from multiprocessing import Process, Array, Value
import pdb


# class PerformanceEvaluationFIOTest(threading.Thread):
class PerformanceEvaluationFIOTest:
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
        self.kill = False
        self.proc = None
        self.show_output = show_output

    def get_last_start_time(self):
        return tools.convert_string_datetime(self.last_start_time.value)

    def get_last_end_time(self):
        return tools.convert_string_datetime(self.last_end_time.value)

    def get_last_terminate_time(self):
        return tools.convert_string_datetime(self.last_terminate_time.value)

    def start(self):
        if self.is_alive() is True:

            return False

        self.last_start_time = Array('c', str(datetime.now()))
        self.last_end_time = Array('c', " " * 26)
        self.last_terminate_time = Array('c', " " * 26)
        self.kill = Value('i', 0)

        self.proc = Process(
            target=PerformanceEvaluationFIOTest.run_f_test,
            args=(self,
                  self.last_start_time,
                  self.last_end_time,
                  self.last_terminate_time,
                  self.kill,))

        # tools.log("   Start test for volume: %s Time: %s" %
        #           (self.cinder_volume_id, self.last_start_time))
        self.proc.start()

        return True
        # print("ZZZZZZZZZZZZZZZZZ" + self.last_end_time.value)

    def terminate(self, after_seconds=-1):
        self.last_end_time = Array('c', " " * 26)
        self.last_terminate_time = Array('c', str(datetime.now()))

        if after_seconds == -1:
            tools.log(
                app="perf_eval",
                type="INFO",
                code="terminate_from_work_gen",
                file_name="performance_evaluation.py",
                function_name="terminate",
                message="Workload generator called terminate VOLUME: %s Time: %s" %
                        (self.cinder_volume_id, self.last_terminate_time.value))
        else:
            tools.log(
                app="perf_eval",
                type="INFO",
                code="terminate",
                file_name="performance_evaluation.py",
                function_name="terminate",
                message="TERMINATE After %s seconds VOLUME: %s Time: %s" %
                        (str(after_seconds), self.cinder_volume_id, self.last_terminate_time.value))

        self.kill = Value('i', 1)

    def is_alive(self):
        if self.proc == None:
            return False

        return self.proc.is_alive()

    @staticmethod
    def run_f_test(test_instance, last_start_time, last_end_time, last_terminate_time, kill):

        if kill == 1:
            tools.log(
                app="perf_eval",
                type="DEBUG",
                code="DEBUG_check_kill",
                file_name="performance_evaluation.py",
                function_name="run_f_test",
                message="kill variable value is changed"
            )

            return

        tools.log(
            app="perf_eval",
            type="info",
            code="start_perf_fio",
            file_name="performance_evaluation.py",
            function_name="run_f_test",
            message="Time: %s Command: %s" % (
                str(test_instance.last_start_time.value),
                PerformanceEvaluation.fio_bin_path + " " + test_instance.test_path
            ),
            insert_db=False)

        out = ""
        err =""
        p = None

        try:
            out, err, p = tools.run_command(
                ["sudo", PerformanceEvaluation.fio_bin_path, test_instance.test_path], debug=False)

            if err != "":
                tools.log(
                    app="W_STORAGE_GEN",
                    type="ERROR",
                    code="run_fio",
                    file_name="workload_generator.py",
                    function_name="run_workload_generator",
                    message="failed to run fio in storage workload generator. volume: %s" % (
                        test_instance.cinder_volume_id),
                    exception=err)

                tools.kill_proc(p.pid)

        except Exception as err_ex:
            tools.log(
                app="W_STORAGE_GEN",
                type="ERROR",
                code="run_fio_cmd",
                file_name="workload_generator.py",
                function_name="run_workload_generator",
                message="failed to run fio for perf test. PID: %s VOLUME: %s" %
                        (str(p.pid), test_instance.cinder_volume_id),
                exception=err_ex)

            tools.kill_proc(p.pid)

            return

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

        tools.log(
            app="perf_eval",
            type="info",
            code="perf_fio_done",
            file_name="performance_evaluation.py",
            function_name="run_f_test",
            message=" DURATION: %s IOPS: %s VOLUME: %s\n OUTPUT_STD:%s\n ERROR_STD: %s" % (
                str(duration), str(iops_measured), test_instance.cinder_volume_id, out, err
            ),
            insert_db=False)


class PerformanceEvaluation:
    # fio_bin_path = os.path.expanduser("~/fio-2.0.9/fio")
    fio_bin_path = "fio"
    fio_tests_conf_path = tools.get_path_expanduser("MLSchedulerAgent/fio/")
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

    def terminate_fio_test(self, cinder_id):

        if PerformanceEvaluation.f_test_instances.has_key(cinder_id):
            PerformanceEvaluation.f_test_instances[cinder_id].terminate()

    def fio_test(self, cinder_volume_id, test_name):

        # outside if the if statement, in case the test is changed
        volume_path = "%s%s/" % (PerformanceEvaluation.mount_base_path, cinder_volume_id)
        test_path = volume_path + test_name

        if PerformanceEvaluation.f_test_instances.has_key(cinder_volume_id) is False:
            f_test = PerformanceEvaluationFIOTest(test_path=test_path,
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
                    app="perf_eval",
                    type="ERROR",
                    code="concurrent_bug",
                    file_name="workload_generator.py",
                    function_name="run_storage_workload_generator",
                    message="could not create the fio test file for workload generator",
                    exception=err)
                return

    def run_fio_test(self):

        attached_volumes = tools.get_all_attached_volumes(self.current_vm_id)

        for volume in attached_volumes:
            self.fio_test(cinder_volume_id=volume.id,
                          test_name=self.fio_test_name)

    def report_available_iops(self):

        pass


if __name__ == "__main__":
    pass
