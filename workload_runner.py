import sys
import argparse
import os
import tools
import time
from multiprocessing import Process
import json
import communication
from datetime import datetime
import pdb
import numpy as np
import random


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

        # tools.log(app="W_STORAGE_GEN", message="   Start test for volume: %s Time: %s" %
        #           (self.cinder_volume_id, self.last_start_time))
        self.proc.start()

    def terminate(self):
        self.proc.terminate()

    def is_terminated(self):
        return self.proc.is_alive()

    @staticmethod
    def run_workload_generator(generator_instance):

        while True:

            start_time = datetime.now()

            command = WorkloadRunner.fio_bin_path + " " + generator_instance.test_path

            # z.terminate()
            # command = "/usr/bin/ndisk/ndisk_8.4_linux_x86_64.bin -R -r 80 -b 32k -M 3 -f /media/%s/F000 -t 3600 -C 2M \n" % generator_instance.volume_id
            tools.log(
                app="W_STORAGE_GEN",
                message="   {run_f_test} Time: %s \ncommand: %s" %
                        (str(start_time), command), insert_db=False)

            out, err = tools.run_command(["sudo", WorkloadRunner.fio_bin_path, generator_instance.test_path],
                                         debug=False)

            if err != "":
                tools.log(
                    app="W_STORAGE_GEN",
                    type="ERROR",
                    code="work_gen_run_fio",
                    file_name="workload_generator.py",
                    function_name="run_workload_generator",
                    message="VOLUME: %s" % (generator_instance.volume_id),
                    exception=err)

                if "file hash not empty on exit" in err:
                    time.sleep(1)
                    continue
                else:
                    # break
                    continue

            duration = tools.get_time_difference(start_time)

            iops_measured = tools.get_iops_measures_from_fio_output(out)

            communication.insert_workload_generator(
                experiment_id=WorkloadRunner.experiment["id"],
                cinder_id=generator_instance.volume_id,
                nova_id=tools.get_current_tenant_id(),
                duration=duration,
                read_iops=iops_measured["read"],
                write_iops=iops_measured["write"],
                command=command,
                output="OUTPUT_STD:%s\n ERROR_STD: %s" % (out, err))

            if generator_instance.show_output == False:
                out = "SHOW_OUTPUT = False"

            tools.log(app="W_STORAGE_GEN", message=" DURATION: %s IOPS: %s VOLUME: %s\n OUTPUT_STD:%s\n ERROR_STD: %s" %
                                                   (
                                                       str(duration), str(iops_measured), generator_instance.volume_id,
                                                       out,
                                                       err),
                      insert_db=False)

            time.sleep(int(np.random.choice(
                generator_instance.delay_between_workload_generation[0],
                1,
                p=generator_instance.delay_between_workload_generation[1]
            )))


class WorkloadRunner:
    fio_bin_path = os.path.expanduser("~/fio-2.0.9/fio")
    fio_tests_conf_path = os.path.expanduser("~/MLSchedulerAgent/fio/")
    mount_base_path = '/media/'
    experiment = communication.Communication.get_current_experiment()

    def __init__(self,
                 current_vm_id,
                 fio_test_name,
                 delay_between_workload_generation,
                 volume_id,
                 volume_life_seconds):

        self.current_vm_id = current_vm_id
        self.fio_test_name = fio_test_name
        self.delay_between_workload_generation = delay_between_workload_generation
        self.volume_id = volume_id
        self.volume_life_seconds = volume_life_seconds

    def run_storage_workload_generator(self, volume_id):

        volume_path = "%s%s/" % (WorkloadRunner.mount_base_path, volume_id)
        test_path = volume_path + self.fio_test_name

        # WorkloadRunner.storage_workload_generator_instances.append(generator)

        try:
            if True or os.path.isfile(test_path) == False:

                with open(WorkloadRunner.fio_tests_conf_path + self.fio_test_name, 'r') as myfile:
                    data = myfile.read().split('\n')

                    data[1] = "directory=" + volume_path

                    volume_test_file = open(test_path, 'w')

                    for item in data:
                        volume_test_file.write("%s\n" % item)

                    volume_test_file.close()
        except Exception as err:
            # todo !important make sure the consistency of cached volume ides

            tools.log(
                app="W_RUNNER",
                type="ERROR",
                code="work_gen_concurrent_bug",
                file_name="workload_generator.py",
                function_name="run_storage_workload_generator",
                message="could not create the fio test file for workload generator",
                exception=err)

            return None

        generator = StorageWorkloadGenerator(
            volume_id=volume_id,
            workload_type="",
            delay_between_workload_generation=self.delay_between_workload_generation,
            show_output=False,
            test_path=test_path)

        generator.start()

        return generator

    def attach_volume(self, instance_id, volume_id):

        '''

        :param instance_id:
        :param volume_id:
        :return:    result.volumeId: the same volume id
                    result.device: the device in the tenant operation system that the volume is attached to
        '''

        # wait until the volume is ready
        if tools.cinder_wait_for_volume_status(volume_id, status="available") is False:
            self._delete_volume(volume_id=volume_id)

            tools.log(
                app="W_RUNNER",
                type="WARNING",
                code="work_gen_concurrent_bug",
                file_name="workload_generator.py",
                function_name="attach_volume",
                message="VOLUME DELETED because status is 'error' id: %s" % volume_id)

            return None

        print("attach_volume instance_id=%s volume_id=%s", instance_id, volume_id)

        nova = tools.get_nova_client()

        result = nova.volumes.create_server_volume(instance_id, volume_id)

        return result

    def mount_volume(self, device_from_openstack_not_used, volume_id, base_path="/media/"):
        '''

        :param device: not used because openstack returns wrong device sometimes. So, nby comparing fdisk -l it finds the latest attached device
        :param volume: it must be an instance of volume object in the cinderclient
        :return:
        '''

        # todo I know there is a case that two volumes get attached at same time, therefore two devices gets ready and it only picks one of them this can cause testing/writing to a wrong volume since device maps the underlying attachment process. Therore must detach and remove the volume.

        already_attached_devices = tools.get_attached_devices()

        # todo define a timeout !important
        # make sure the device is ready to be mounted
        while True:
            new_device = tools.get_attached_devices() - already_attached_devices

            if len(new_device) > 0:
                if len(new_device) > 1:
                    tools.log(
                        app="W_RUNNER",
                        type="WARNING",
                        code="work_gen_concurrent_bug",
                        file_name="workload_generator.py",
                        function_name="mount_volume",
                        message="already_attached_devices: %s \nnew_devic: %s \ntwo devices attached at the same time, can not identify which one should be mounted to which volume." % (
                            already_attached_devices, new_device))

                    return False

                device = new_device.pop()
                break

        print("try to mount_volume device: %s volume.id: %", device, volume_id)

        log = ""

        c1 = ["sudo", 'mkfs', '-t', "ext3", device]
        out, err = tools.run_command(c1, debug=True)

        if "in use by the system" in err:
            tools.log(
                app="W_RUNNER",
                type="ERROR",
                code="work_gen_in_use",
                file_name="workload_generator.py",
                function_name="mount_volume",
                message="%s out-->%s err-->%s  \n" % (c1, out, err)
            )

            return False

        log = "%s %s out-->%s err-->%s  \n" % (log, c1, out, err)

        mount_to_path = base_path + volume_id

        c2 = ["sudo", 'mkdir', mount_to_path]
        out, err = tools.run_command(c2, debug=True)

        if err != "":
            tools.log(
                app="W_RUNNER",
                type="ERROR",
                code="work_gen_mount_mkdir",
                file_name="workload_generator.py",
                function_name="mount_volume",
                message="%s out-->%s err-->%s  \n" % (c2, out, err)
            )

            return False

        log = "%s %s out-->%s err-->%s  \n" % (log, c2, out, err)

        c3 = ["sudo", 'mount', device, mount_to_path]
        out, err = tools.run_command(c3, debug=True)

        if err != "":
            tools.log(
                app="W_RUNNER",
                type="ERROR",
                code="work_gen_mount_mount",
                file_name="workload_generator.py",
                function_name="mount_volume",
                message="%s out-->%s err-->%s  \n" % (c3, out, err)
            )

            return False

        log = "%s %s out-->%s err-->%s  \n" % (log, c3, out, err)

        tools.log(
            app="W_RUNNER",
            type="INFO",
            code="work_gen_mount_report",
            file_name="workload_generator.py",
            function_name="mount_volume",
            message=log
        )

        return True

    def detach_delete_volume(self, cinder_volume_id, is_deleted=1):

        self.detach_volume(cinder_volume_id)
        self.delete_volume(
            cinder_volume_id=cinder_volume_id,
            is_deleted=is_deleted
        )

    def detach_volume(self, cinder_volume_id):

        device = tools.check_is_device_mounted_to_volume(cinder_volume_id)

        tools.umount_device(device)

        device = tools.check_is_device_mounted_to_volume(cinder_volume_id)

        if device == '':
            # detach volume

            if self._detach_volume(self.current_vm_id, cinder_volume_id) == "volume-not-exists":
                pass

        else:
            tools.log(
                app="W_RUNNER",
                type="ERROR",
                code="work_gen_concurrent_bug",
                file_name="workload_generator.py",
                function_name="detach_volume",
                message="the volume is not unmounted. Device: %s Volume_id: %s" %
                        (str(device), cinder_volume_id)
            )

            # raise Exception("ERROR [detach_volume] the volume is not unmounted. Device: %s Volume_id: %s" %
            #                 (str(device), cinder_volume_id))

            return False

        return True

    def delete_volume(self, cinder_volume_id, is_deleted=1, mount_path="/media/"):

        cinder = tools.get_cinder_client()

        while True:

            vol_reload = cinder.volumes.get(cinder_volume_id)

            if vol_reload.status != 'detaching':
                break

        if vol_reload.status == 'available':
            cinder.volumes.delete(cinder_volume_id)

            communication.delete_volume(
                cinder_id=cinder_volume_id,
                is_deleted=is_deleted
            )

            # remove the path that volume were mounted to. Because the workload generator will keep using ndisk to consistantly write data into the disk
            tools.run_command(["sudo", "rm", "-d", "-r", mount_path + cinder_volume_id])

    def _delete_volume(self, volume_id, is_deleted=1):
        cinder = tools.get_cinder_client()

        cinder.volumes.delete(volume_id)

        communication.delete_volume(
            cinder_id=volume_id,
            is_deleted=is_deleted)

    def _detach_volume(self, nova_id, volume):
        cinder = tools.get_cinder_client()
        nova = tools.get_nova_client()

        if isinstance(volume, basestring):
            volume_id = volume
        else:
            volume_id = volume.id

        try:
            vol = cinder.volumes.get(volume_id)
        except Exception as err:
            tools.log(
                app="W_RUNNER",
                type="WARNING",
                code="work_gen",
                file_name="workload_generator.py",
                function_name="_detach_volume",
                message="attempt to delete a volume that does not exists. Probably [nova volume-attachment] returned a volume that does not exists",
                exception=err)

            return "volume-not-exists"

        if vol.status == "in-use":

            nova.volumes.delete_server_volume(nova_id, volume_id)

        else:
            tools.log(
                app="W_RUNNER",
                type="ERROR",
                code="work_gen",
                file_name="workload_generator.py",
                function_name="_detach_volume",
                message="attempted to detach, but volume status is not 'in-use' it is %s. volume_id: %s"
                        % (vol.status, volume_id))

            # raise Exception("ERROR [_detach_volume] volume status is not 'in-use' it is %s volume_id: %s" %
            #                 (vol.status, volume_id))

    def attach_volume_then_mount(self, instance_id, volume_id):

        attach_result = self.attach_volume(instance_id, volume_id)

        if attach_result is not None:

            tools.log(
                app="W_RUNNER",
                type="INFO",
                code="work_gen",
                file_name="workload_generator.py",
                function_name="create_attach_volume",
                message="going to mount volume. cinder_reported_device: %s volume: %s" % (
                    attach_result.device, volume_id)
            )

            if self.mount_volume(
                    device_from_openstack_not_used=attach_result.device,
                    volume_id=volume_id) is False:
                tools.log(
                    app="W_RUNNER",
                    type="WARNING",
                    code="work_gen_mount_failed",
                    file_name="workload_generator.py",
                    function_name="create_attach_volume",
                    message="cinder_reported_device:%s volume_id: %s" % (attach_result.device, volume_id)
                )
                # detach and remove the volume if mount failed

                self.detach_delete_volume(
                    cinder_volume_id=volume_id,
                    is_deleted=2
                )

                return False
        else:
            return False

        return True

    def start_simulation(self):

        result = self.attach_volume_then_mount(
            instance_id=self.current_vm_id,
            volume_id=self.volume_id
        )

        create_time = datetime.now()

        if result:

            # generator = self.run_storage_workload_generator(self.volume_id)

            while True:

                time.sleep(1)

                if tools.get_time_difference(create_time) > \
                        int(np.random.choice(
                            self.volume_life_seconds[0],
                            1,
                            p=self.volume_life_seconds[1])):

                    # generator.terminate()

                    self.detach_delete_volume(self.volume_id)

                    break

                # if generator.is_terminated() is True:
                #
                #     lg = tools.log(
                #         app="W_RUNNER",
                #         type="ERROR",
                #         code="early_terminated",
                #         file_name="workload_generator.py",
                #         function_name="start_simulation",
                #         message="the storage workload generator is terminated unexpectedly. volume: %s" % ( self.volume_id))
                #
                #     raise Exception(lg)


        else:
            # todo save log that  it failed
            pass

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Synthetic workload generator.')

    parser.add_argument('commands', type=str, nargs='+',
                        choices=['start'],
                        help=""
                        )

    temp_required = False

    parser.add_argument('--fio_test_name', default="workload_generator.fio", metavar='', type=str,
                        required=temp_required, help='Test name for fio')

    parser.add_argument('--volume_id', type=str, metavar='', required=temp_required,
                        help='Specify volume id to do operation on.')

    parser.add_argument('--delay_between_workload_generation', default='[]', metavar='', type=str,
                        required=temp_required,
                        help='wait before generation - seconds. example:[[500, 750, 1000], [0.5, 0.3, 0.2]]. will be fed to numpy.random.choice')

    parser.add_argument('--volume_life_seconds', default='[]', metavar='', type=str, required=temp_required,
                        help='delete a volume after th specified second upon its creation. example:[[500, 750, 1000], [0.5, 0.3, 0.2]]. will be fed to numpy.random.choice')

    args = parser.parse_args()

    wg = WorkloadRunner(
        current_vm_id=tools.get_current_tenant_id(),
        fio_test_name=args.fio_test_name,
        volume_id=args.volume_id,
        delay_between_workload_generation=json.loads(args.delay_between_workload_generation),
        volume_life_seconds=json.loads(args.volume_life_seconds),
    )

    if "start" in args.commands:
        wg.start_simulation()
