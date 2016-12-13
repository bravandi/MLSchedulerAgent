from shutil import copyfile
import tools
from datetime import datetime
import communication
import os
from multiprocessing import Process, Array
import pdb


# class PerformanceEvaluationFIOTest(threading.Thread):
class PerformanceEvaluationFIOTest:
    """

    """

    def __init__(self, test_path, test_name, volume_path, cinder_volume_id, show_output=False):
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
        self.test_name = test_name
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
        if self.is_alive() is True:
            return False

        self.last_start_time = Array('c', str(datetime.now()))
        self.last_end_time = Array('c', " " * 26)
        self.last_terminate_time = Array('c', " " * 26)

        self.proc = Process(
            target=PerformanceEvaluationFIOTest.run_f_test,
            args=(self,
                  self.last_start_time,
                  self.last_end_time,
                  self.last_terminate_time,))

        # tools.sou "   Start test for volume: %s Time: %s" %
        #           (self.cinder_volume_id, self.last_start_time))
        self.proc.start()

        return True
        # print("ZZZZZZZZZZZZZZZZZ" + self.last_end_time.value)

    def terminate_ftest(self, after_seconds=-1, time_out=False):
        self.last_end_time = Array('c', " " * 26)
        self.last_terminate_time = Array('c', str(datetime.now()))

        self.proc.terminate()

        if time_out is True:

            tools.log(
                app="perf_eval",
                type="WARNING",
                volume_cinder_id=self.cinder_volume_id,
                code="terminate_time_out",
                file_name="performance_evaluation.py",
                function_name="terminate",
                message="TERMINATE After %s seconds Time: %s" %
                        (str(after_seconds), self.last_terminate_time.value))

        else:
            tools.log(
                app="perf_eval",
                type="INFO",
                volume_cinder_id=self.cinder_volume_id,
                code="terminate_from_work_gen",
                file_name="performance_evaluation.py",
                function_name="terminate",
                message="Workload generator called terminate"
            )

    def is_alive(self):
        if self.proc is None:
            return False

        return self.proc.is_alive()

    @staticmethod
    def run_f_test(test_instance, last_start_time, last_end_time, last_terminate_time):

        out = ""
        err = ""
        p = None

        try:
            command = ["sudo", "docker", "run", "-v",
                       test_instance.volume_path + ":/tmp/fio-data",
                       "-e", "JOBFILES=" + test_instance.test_name, "clusterhq/fio-tool"]

            tools.log(
                app="perf_eval",
                type="INFO",
                volume_cinder_id=test_instance.cinder_volume_id,
                code="perf_run_eval_fio",
                file_name="performance_evaluation.py",
                function_name="run_f_test",
                message="Time: %s Command: %s" % (str(test_instance.last_start_time.value), " ".join(command))
                # ,insert_db=False
            )

            out, err, p = tools.run_command(command, debug=False)

            if err != "":
                tools.log(
                    app="perf_eval",
                    type="ERROR",
                    volume_cinder_id=test_instance.cinder_volume_id,
                    code="perf_fio_std_err",
                    file_name="performance_evaluation.py",
                    function_name="run_workload_generator",
                    message="command: %s | stdout: %s" %
                            (" ".join(command), out),
                    exception=err
                )

                # tools.kill_proc(p.pid)
                if "Cannot connect to the Docker daemon" in err:
                    tools.run_command2("sudo systemctl start docker")

                return

        except Exception as err_ex:

            tools.log(
                app="perf_eval",
                type="ERROR",
                volume_cinder_id=test_instance.cinder_volume_id,
                code="run_perf_fio_failed",
                file_name="performance_evaluation.py",
                function_name="run_workload_generator",
                message="failed to run fio for perf test. command: " + command,
                exception=err_ex
            )

            # tools.kill_proc(p.pid)
            if "Cannot connect to the Docker daemon" in str(err_ex):
                tools.run_command2("sudo systemctl start docker")

            return

        iops_measured = tools.get_iops_measures_from_fio_output(out)

        # print "test_instance.last_end_time:" + last_end_time.value
        last_end_time.value = str(datetime.now())
        duration = round(tools.get_time_difference(last_start_time.value, last_end_time.value), 2)

        communication.insert_volume_performance_meter(
            experiment_id=PerformanceEvaluation.experiment["id"],
            sla_violation_id=1,  # 1 means no violation
            nova_id=tools.get_current_tenant_id(),
            cinder_volume_id=test_instance.cinder_volume_id,
            read_iops=iops_measured["read"],
            write_iops=iops_measured["write"],
            duration=float(duration),
            io_test_output="OUTPUT_STD:%s\n ERROR_STD: %s" % (out, err))

        if test_instance.show_output is False:
            out = "SHOW_OUTPUT = False"

        tools.log(
            app="perf_eval",
            type="INFO",
            volume_cinder_id=test_instance.cinder_volume_id,
            code="iops_perf",
            file_name="performance_evaluation.py",
            function_name="run_f_test",
            message="DURATION: %s read: %s write: %s\n OUTPUT_STD:%s\n ERROR_STD: %s" %
                    (str(duration), iops_measured["read"], iops_measured["write"], out, err)
            # ,insert_db=False
        )


class PerformanceEvaluation:
    # fio_bin_path = os.path.expanduser("~/fio-2.0.9/fio")
    fio_bin_path = "fio"
    agent_fio_tests_path = tools.get_path_expanduser("MLSchedulerAgent/fio/")
    mount_base_path = '/media/'
    experiment = communication.Communication.get_current_experiment()
    f_test_instances = {}

    def __init__(self,
                 fio_test_name,
                 current_vm_id,
                 terminate_if_takes,
                 restart_gap,
                 restart_gap_after_terminate,
                 show_fio_output,
                 volume_id):

        self.fio_test_name = fio_test_name
        self.current_vm_id = current_vm_id
        self.terminate_if_takes = terminate_if_takes
        self.restart_gap = restart_gap
        self.restart_gap_after_terminate = restart_gap_after_terminate
        self.show_fio_output = show_fio_output
        self.volume_id = volume_id
        self.volume_path = "%s%s/" % (PerformanceEvaluation.mount_base_path, volume_id)
        self.test_path = self.volume_path + self.fio_test_name

        self.f_test = PerformanceEvaluationFIOTest(
            test_path=self.test_path,
            test_name=self.fio_test_name,
            volume_path=self.volume_path,
            cinder_volume_id=volume_id,
            show_output=self.show_fio_output)

    def initialize(self):

        try:
            # make sure the test file [*.fio] exists
            if os.path.isfile(self.test_path) is False:
                copyfile(PerformanceEvaluation.agent_fio_tests_path + self.fio_test_name, self.test_path)

            return 'successful'

        except Exception as err:
            # cc = tools.get_volume_status(self.volume_id)
            # z = cc.status
            tools.log(
                app="perf_eval",
                type="ERROR",
                volume_cinder_id=self.volume_id,
                code="failed_copy_perf_fio_file",
                file_name="performance_evaluation.py",
                function_name="run_storage_workload_generator",
                message="could not create the fio test file for workload generator",
                exception=err)

            return 'failed-copy-perf-eval-fio-test-file'

    def run_fio_test(self):
        """

        :param cinder_volume_id:
        :param test_name:
        :return: 'test-is-in-progress', 'on-hold-restart-gap', 'on-hold-terminated-gap',
        'successful', 'failed-copy-perf-eval-fio-test-file'
        """

        if self.f_test.is_alive():
            difference = tools.get_time_difference(self.f_test.get_last_start_time())
            # difference = (datetime.now() - f_test.last_start_time).total_seconds()
            # tools.log(" [terminate] because taking more than %s seconds" % difference)

            if difference > self.terminate_if_takes:
                self.f_test.terminate_ftest(after_seconds=difference, time_out=True)

                # record termination in database
                communication.insert_volume_performance_meter(
                    experiment_id=PerformanceEvaluation.experiment["id"],
                    nova_id=tools.get_current_tenant_id(),
                    cinder_volume_id=self.volume_id,
                    read_iops=0,
                    write_iops=0,
                    duration=0,
                    terminate_wait=float(difference),
                    io_test_output="TERMINATED [terminate_if_takes: %s]" % str(self.terminate_if_takes))

                return "time-out"

            return "test-is-in-progress"
        else:

            last_end_time = self.f_test.get_last_end_time()
            last_terminate_time = self.f_test.get_last_terminate_time()

            # if last_end_time is not None:
            #     tools.log("  ***[f_test.last_end_time DIFFERENCE] %s" %
            #               str(tools.get_time_difference(last_end_time)))

            # have xx seconds gap between restarting the tests
            if last_end_time is not None and \
                            tools.get_time_difference(last_end_time) < self.restart_gap:  # + random.uniform(0.5, 2.5):
                return 'on-hold-restart-gap'

            # if terminated wait for xx seconds then start the process
            if last_terminate_time is not None and tools.get_time_difference(
                    last_terminate_time) < self.restart_gap_after_terminate:
                return 'on-hold-terminated-gap'

            # if volume is attached but not mounted yet, or the volume is detached
            if os.path.isdir(self.volume_path) is False:
                PerformanceEvaluation.f_test_instances.pop(self.volume_id)
                return 'volume-path-not-exists-try-again-next-round'

            self.f_test.start()

            return 'successful'

    def is_perf_alive(self):

        return self.f_test.is_alive()


if __name__ == "__main__":
    pass
