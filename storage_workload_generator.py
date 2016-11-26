import tools
import time
from multiprocessing import Process
import communication
from datetime import datetime
import pdb
import numpy as np

class StorageWorkloadGenerator:
    """

    """

    def __init__(self, volume_id, workload_type, test_path, show_output=False, delay_between_workload_generation=1.0):
        """

        :param workload_type:
        :param delay_between_workload_generation:
        :return:
        """

        # threading.Thread.__init__(self)
        self.volume_id = volume_id
        self.workload_type = workload_type
        self.delay_between_workload_generation = delay_between_workload_generation
        self.proc = None
        self.show_output = show_output
        self.test_path = test_path

    def start(self):
        self.proc = Process(
            target=StorageWorkloadGenerator.run_workload_generator,
            args=(self,))

        # tools.log("   Start test for volume: %s Time: %s" %
        #           (self.cinder_volume_id, self.last_start_time))
        self.proc.start()

    def terminate(self):
        self.proc.terminate()

    @staticmethod
    def run_workload_generator(generator_instance):

        while True:

            start_time = datetime.now()

            command = CinderWorkloadGenerator.fio_bin_path + " " + generator_instance.test_path

            # z.terminate()
            # command = "/usr/bin/ndisk/ndisk_8.4_linux_x86_64.bin -R -r 80 -b 32k -M 3 -f /media/%s/F000 -t 3600 -C 2M \n" % generator_instance.volume_id
            tools.log(
                "   {run_f_test} Time: %s \ncommand: %s" %
                (str(start_time), command), insert_db=False)

            out, err = tools.run_command(["sudo", CinderWorkloadGenerator.fio_bin_path, generator_instance.test_path],
                                         debug=False)

            if err != "":
                tools.log(
                    type="ERROR",
                    code="work_gen_run_fio",
                    file_name="workload_generator.py",
                    function_name="run_workload_generator",
                    message="VOLUME: %s" % (generator_instance.volume_id),
                    exception=err)

                break

            duration = tools.get_time_difference(start_time)

            iops_measured = tools.get_iops_measures_from_fio_output(out)

            communication.insert_workload_generator(
                experiment_id=CinderWorkloadGenerator.experiment["id"],
                nova_id=tools.get_current_tenant_id(),
                duration=duration,
                read_iops=iops_measured["read"],
                write_iops=iops_measured["write"],
                command=command,
                output="OUTPUT_STD:%s\n ERROR_STD: %s" % (out, err))

            if generator_instance.show_output == False:
                out = "SHOW_OUTPUT = False"

            tools.log(" DURATION: %s IOPS: %s VOLUME: %s\n OUTPUT_STD:%s\n ERROR_STD: %s" %
                      (str(duration), str(iops_measured), generator_instance.volume_id, out, err),
                      insert_db=False)

            time.sleep(int(np.random.choice(
                generator_instance.delay_between_workload_generation[0],
                1,
                p=generator_instance.delay_between_workload_generation[1]
            )))