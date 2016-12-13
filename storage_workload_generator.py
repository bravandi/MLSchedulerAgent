from shutil import copyfile
from multiprocessing import Process
from datetime import datetime
import communication
import tools
import os
import pdb


class StorageWorkloadGenerator:
    # fio_bin_path = os.path.expanduser("~/fio-2.0.9/fio")
    fio_bin_path = "fio"
    fio_tests_conf_path = tools.get_path_expanduser("MLSchedulerAgent/fio/")
    mount_base_path = '/media/'

    """

    """

    def __init__(self,
                 volume_id,
                 workload_type,
                 test_path,
                 volume_path,
                 fio_test_name,
                 show_output=False,
                 delay_between_storage_workload_generation=1.0):
        """

        :param workload_type:
        :param delay_between_storage_workload_generation:
        :return:
        """

        # threading.Thread.__init__(self)
        self.volume_path = volume_path
        self.fio_test_name = fio_test_name
        self.volume_id = volume_id
        self.workload_type = workload_type
        self.delay_between_storage_workload_generation = delay_between_storage_workload_generation
        self.proc = None
        self.show_output = show_output
        self.test_path = test_path

    def start(self):
        if self.is_alive() is True:
            return False

        self.proc = Process(
            target=StorageWorkloadGenerator.run_workload_generator,
            args=(self,))

        self.proc.start()

        return True

    def terminate(self):
        pass
        # if self.proc is None:
        #     tools.log(
        #         app="W_STORAGE_GEN",
        #         type="ERROR",
        #         code="proc_null_terminate",
        #         file_name="workload_generator.py",
        #         function_name="terminate",
        #         message="proc is null cant terminate. maybe StorageWorkloadGenerator.start() is not called.")

        # return False

        # self.proc.terminate()

        # return True

    def is_alive(self):

        if self.proc is None:
            return False

        return self.proc.is_alive()

    @staticmethod
    def create_storage_workload_generator(volume_id, fio_test_name, delay_between_storage_workload_generation):

        volume_path = "%s%s/" % (StorageWorkloadGenerator.mount_base_path, volume_id)
        test_path = volume_path + fio_test_name

        # CinderWorkloadGenerator.storage_workload_generator_instances.append(generator)

        try:

            if os.path.isfile(test_path) is False:

                copyfile(StorageWorkloadGenerator.fio_tests_conf_path + fio_test_name, test_path)

                # with open(StorageWorkloadGenerator.fio_tests_conf_path + fio_test_name, 'r') as myfile:
                #     data = myfile.read().split('\n')
                #
                #     data[1] = "directory=" + volume_path
                #
                #     volume_test_file = open(test_path, 'w')
                #
                #     for item in data:
                #         volume_test_file.write("%s\n" % item)
                #
                #     volume_test_file.close()
        except Exception as err:
            tools.log(
                app="work_gen",
                type="ERROR",
                code="failed_copy_wgen_fio_file",
                file_name="storage_workload_generator.py",
                function_name="run_storage_workload_generator",
                message="could not copy the fio test file for workload generator",
                volume_cinder_id=volume_id,
                exception=err
                # ,insert_db=False
            )

            return 'failed-copy-fio-file'

        generator = StorageWorkloadGenerator(
            volume_id=volume_id,
            workload_type="",
            test_path=test_path,
            volume_path=volume_path,
            fio_test_name=fio_test_name,
            show_output=False,
            delay_between_storage_workload_generation=delay_between_storage_workload_generation,
            )

        return generator

    @staticmethod
    def run_workload_generator(generator_instance):

        # while True:

        start_time = datetime.now()

        out = ""
        err = ""
        p = None

        try:
            # command = "sudo " + StorageWorkloadGenerator.fio_bin_path + " " + generator_instance.test_path
            # out, err, p = tools.run_command(
            #     ["sudo", StorageWorkloadGenerator.fio_bin_path, generator_instance.test_path],
            #     debug=False)

            command = ["sudo", "docker", "run", "-v",
                       generator_instance.volume_path + ":/tmp/fio-data",
                       "-e", "JOBFILES=" + generator_instance.fio_test_name, "clusterhq/fio-tool"]

            tools.log(
                app="W_STORAGE_GEN",
                type="INFO",
                code="wgen_run_gen_fio",
                file_name="workload_generator.py",
                function_name="run_workload_generator",
                message="Time: %s \ncommand: %s" % (str(start_time), " ".join(command)),
                volume_cinder_id=generator_instance.volume_id
                # ,insert_db=False
            )

            out, err, p = tools.run_command(command, debug=False)

            if err != "":
                tools.log(
                    app="W_STORAGE_GEN",
                    type="ERROR",
                    code="run_fio_stderr",
                    file_name="workload_generator.py",
                    function_name="run_workload_generator",
                    message="command: %s | stdout: %s" % (" ".join(command), out),
                    volume_cinder_id=generator_instance.volume_id,
                    exception=err)

                # tools.kill_proc(p.pid)
                if "Cannot connect to the Docker daemon" in err:
                    tools.run_command2("sudo systemctl start docker")

                return

        except Exception as err_ex:
            tools.log(
                app="W_STORAGE_GEN",
                type="ERROR",
                code="run_fio_cmd",
                file_name="workload_generator.py",
                function_name="run_workload_generator",
                message="failed to run fio for storage gen. command: " + " ".join(command),
                volume_cinder_id=generator_instance.volume_id,
                exception=err_ex)

            # tools.kill_proc(p.pid)
            if "Cannot connect to the Docker daemon" in str(err_ex):
                tools.run_command2("sudo systemctl start docker")

            return

        duration = round(tools.get_time_difference(start_time), 2)

        iops_measured = tools.get_iops_measures_from_fio_output(out)

        communication.insert_workload_generator(
            experiment_id=communication.Communication.get_current_experiment()["id"],
            cinder_id=generator_instance.volume_id,
            nova_id=tools.get_current_tenant_id(),
            duration=duration,
            read_iops=iops_measured["read"],
            write_iops=iops_measured["write"],
            command=command,
            output="OUTPUT_STD:%s\n ERROR_STD: %s" % (out, err))

        if generator_instance.show_output is False:
            out = "SHOW_OUTPUT = False"

        tools.log(
            app="W_STORAGE_GEN",
            type="INFO",
            code="iops_wgen",
            file_name="workload_generator.py",
            function_name="run_workload_generator",
            message=" DURATION: %s read: %s write: %s\n OUTPUT_STD:%s\n ERROR_STD: %s" %
                    (
                        str(duration),
                        iops_measured["read"],
                        iops_measured["write"],
                        out,
                        err
                    ),
            volume_cinder_id=generator_instance.volume_id
            # ,insert_db=False
        )
