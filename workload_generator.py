import subprocess
import fcntl
import errno
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
import sys
import random
import performance_evaluation as perf


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
        if self.proc is None:
            tools.log(
                app="W_STORAGE_GEN",
                type="ERROR",
                code="proc_null",
                file_name="workload_generator.py",
                function_name="terminate",
                message="proc is null cant terminate. maybe StorageWorkloadGenerator.start() is not called.")

            return False

        self.proc.terminate()

        return True

    def is_terminated(self):

        if self.proc is None:
            tools.log(
                app="W_STORAGE_GEN",
                type="ERROR",
                code="proc_null",
                file_name="workload_generator.py",
                function_name="is_terminated",
                message="proc is null cant call is_alive(). maybe StorageWorkloadGenerator.start() is not called.")

            return None

        return self.proc.is_alive()

    @staticmethod
    def run_workload_generator(generator_instance):

        while True:

            start_time = datetime.now()

            command = CinderWorkloadGenerator.fio_bin_path + " " + generator_instance.test_path

            tools.log(
                app="W_STORAGE_GEN",
                message="   {run_f_test} Time: %s \ncommand: %s" %
                        (str(start_time), command), insert_db=False)

            try:
                out, err = tools.run_command(
                    ["sudo", CinderWorkloadGenerator.fio_bin_path, generator_instance.test_path],
                    debug=False)

                if err != "":
                    tools.log(
                        app="W_STORAGE_GEN",
                        type="ERROR",
                        code="run_fio",
                        file_name="workload_generator.py",
                        function_name="run_workload_generator",
                        message="VOLUME: %s" % (generator_instance.volume_id),
                        exception=err)

                    time.sleep(1)

                    if "file hash not empty on exit" in err:

                        continue
                    else:
                        # break
                        continue

            except Exception as err_ex:
                tools.log(
                    app="W_STORAGE_GEN",
                    type="ERROR",
                    code="run_fio_cmd",
                    file_name="workload_generator.py",
                    function_name="run_workload_generator",
                    message="failed to run fio for VOLUME: %s" % (generator_instance.volume_id),
                    exception=err_ex)

                time.sleep(1)

                continue

            duration = tools.get_time_difference(start_time)

            iops_measured = tools.get_iops_measures_from_fio_output(out)

            communication.insert_workload_generator(
                experiment_id=CinderWorkloadGenerator.experiment["id"],
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


class CinderWorkloadGenerator:
    # fio_bin_path = os.path.expanduser("~/fio-2.0.9/fio")
    fio_bin_path = os.path.expanduser("fio")
    fio_tests_conf_path = os.path.expanduser("~/MLSchedulerAgent/fio/")
    mount_base_path = '/media/'
    experiment = communication.Communication.get_current_experiment()

    # storage_workload_generator_instances = []

    def __init__(self,
                 current_vm_id,
                 fio_test_name,
                 delay_between_workload_generation,
                 max_number_volumes,
                 volume_life_seconds,
                 volume_size,
                 request_read_iops,
                 request_write_iops,
                 wait_after_volume_rejected,
                 performance_evaluation_instance,
                 workload_id=0):
        """

        :param workload_id: if equal to 0 it will create new workload by capturing the current experiment requests
        :param current_vm_id:
        :param fio_test_name:
        :param delay_between_workload_generation:
        :return:
        """

        self.wait_after_volume_rejected = wait_after_volume_rejected
        self.request_read_iops = request_read_iops
        self.request_write_iops = request_write_iops
        self.current_vm_id = current_vm_id
        self.fio_test_name = fio_test_name
        self.delay_between_workload_generation = delay_between_workload_generation
        self.workload_id = workload_id
        self.max_number_volumes = max_number_volumes
        self.volume_size = volume_size
        self.volume_life_seconds = volume_life_seconds
        self.performance_evaluation_instance = performance_evaluation_instance

    def run_storage_workload_generator_all_volums(self):

        for volume in tools.get_all_attached_volumes(self.current_vm_id):
            self.run_storage_workload_generator(volume.id)

    def run_storage_workload_generator(self, volume_id):

        volume_path = "%s%s/" % (CinderWorkloadGenerator.mount_base_path, volume_id)
        test_path = volume_path + self.fio_test_name

        # CinderWorkloadGenerator.storage_workload_generator_instances.append(generator)

        try:
            if True or os.path.isfile(test_path) == False:

                with open(CinderWorkloadGenerator.fio_tests_conf_path + self.fio_test_name, 'r') as myfile:
                    data = myfile.read().split('\n')

                    data[1] = "directory=" + volume_path

                    volume_test_file = open(test_path, 'w')

                    for item in data:
                        volume_test_file.write("%s\n" % item)

                    volume_test_file.close()
        except Exception as err:
            # todo !important make sure the consistency of cached volume ides

            tools.log(
                app="work_gen",
                type="ERROR",
                code="concurrent_bug",
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

    def create_volume(self, size=None):
        '''

        :return: returns volume object
        '''

        if size is None:
            size = int(np.random.choice(self.volume_size[0], 1, self.volume_size[1]))

        read_iops = int(np.random.choice(self.request_read_iops[0], 1, p=self.request_read_iops[1]))
        write_iops = int(np.random.choice(self.request_write_iops[0], 1, p=self.request_write_iops[1]))

        id = communication.insert_volume_request(
            experiment_id=CinderWorkloadGenerator.experiment["id"],
            capacity=size,
            type=0,
            read_iops=read_iops,
            write_iops=write_iops
        )

        cinder = tools.get_cinder_client()

        volume = cinder.volumes.create(size, name="%s,%s" % (CinderWorkloadGenerator.experiment["id"], str(id)))

        # todo must call from scheduler it self
        # communication.add_volume(
        #     cinder_id=volume.id,
        #     backend_id=tools.Backend.specifications["id"],
        #     schedule_response=communication.ScheduleResponse.Accepted,
        #     capacity=size
        # )

        return volume

    def attach_volume(self, instance_id, volume_id):

        '''

        :param instance_id:
        :param volume_id:
        :return:    result.volumeId: the same volume id
                    result.device: the device in the tenant operation system that the volume is attached to
        '''

        # wait until the volume is ready
        if tools.cinder_wait_for_volume_status(volume_id, status="available") is False:
            self._delete_volume(volume_id=volume_id, is_deleted=2)

            tools.log(
                app="work_gen",
                type="WARNING",
                code="vol_status_error",
                file_name="workload_generator.py",
                function_name="attach_volume",
                message="VOLUME DELETED because status is 'error' id: %s" % volume_id)

            return None

        print("attach_volume instance_id=%s volume_id=%s", instance_id, volume_id)

        nova = tools.get_nova_client()

        try:
            result = nova.volumes.create_server_volume(instance_id, volume_id)
        except:
            tools.log(
                app="work_gen",
                type="WARNING",
                code="nova_attach_failed",
                file_name="workload_generator.py",
                function_name="attach_volume",
                message="attach failed. id: %s" % volume_id)
            return None

        return result

    def mount_volume(self, device_from_openstack_not_used, volume, base_path="/media/"):
        '''

        :param device: not used because openstack returns wrong device sometimes. So, nby comparing fdisk -l it finds the latest attached device
        :param volume: it must be an instance of volume object in the cinderclient
        :return:
        '''

        # todo I know there is a case that two volumes get attached at same time, therefore two devices gets ready and it only picks one of them this can cause testing/writing to a wrong volume since device maps the underlying attachment process. Therore must detach and remove the volume.

        already_attached_devices = None
        try:
            already_attached_devices = tools.get_attached_devices()
        except Exception as err:
            tools.log(
                app="work_gen",
                type="ERROR",
                code="get_attached_devices",
                file_name="workload_generator.py",
                function_name="mount_volume",
                message="failed to get already_attached_devices. must try again but for now return false",
                exception=err
            )
            return False

        # todo define a timeout !important
        # make sure the device is ready to be mounted
        while True:
            try:
                new_device = tools.get_attached_devices() - already_attached_devices
            except Exception as err:
                tools.log(
                    app="work_gen",
                    type="WARNING",
                    code="get_attached_devices",
                    file_name="workload_generator.py",
                    function_name="mount_volume",
                    message="failed to get attached devices. will retry in the while true loop.",
                    exception=err
                )

                continue

            if len(new_device) > 0:
                if len(new_device) > 1:
                    tools.log(
                        app="work_gen",
                        type="WARNING",
                        code="concurrent_bug",
                        file_name="workload_generator.py",
                        function_name="mount_volume",
                        message="already_attached_devices: %s \nnew_devic: %s \ntwo devices attached at the same time, can not identify which one should be mounted to which volume." % (
                            already_attached_devices, new_device))

                    return False

                device = new_device.pop()
                break

        print("try to mount_volume device: %s volume.id: %", device, volume.id)

        log = ""
        try:
            c1 = ["sudo", 'mkfs', '-t', "ext3", device]
            out, err = tools.run_command(c1, debug=True)
            if "in use by the system" in err:
                tools.log(
                    app="work_gen",
                    type="ERROR",
                    code="in_use",
                    file_name="workload_generator.py",
                    function_name="mount_volume",
                    message="cannot mount because it is in use. %s out-->%s err-->%s  \n" % (c1, out, err)
                )
                return False
            log = "%s %s out-->%s err-->%s  \n" % (log, c1, out, err)
        except Exception as err:
            tools.log(
                app="work_gen",
                type="WARNING",
                code="mkfs_failed",
                file_name="workload_generator.py",
                function_name="mount_volume",
                message="failed to run mkfs. return False",
                exception=err
            )
            return False

        mount_to_path = base_path + volume.id

        try:
            c2 = ["sudo", 'mkdir', mount_to_path]
            out, err = tools.run_command(c2, debug=True)
            if err != "":
                tools.log(
                    app="work_gen",
                    type="ERROR",
                    code="mount_mkdir",
                    file_name="workload_generator.py",
                    function_name="mount_volume",
                    message="%s out-->%s err-->%s  \n" % (c2, out, err)
                )
                return False
            log = "%s %s out-->%s err-->%s  \n" % (log, c2, out, err)
        except Exception as err:
            tools.log(
                app="work_gen",
                type="WARNING",
                code="mkdir_failed",
                file_name="workload_generator.py",
                function_name="mount_volume",
                message="failed to run mkdir. return False",
                exception=err
            )
            return False

        try:
            c3 = ["sudo", 'mount', device, mount_to_path]
            out, err = tools.run_command(c3, debug=True)
            if err != "":
                tools.log(
                    app="work_gen",
                    type="ERROR",
                    code="mount_mount",
                    file_name="workload_generator.py",
                    function_name="mount_volume",
                    message="%s out-->%s err-->%s  \n" % (c3, out, err)
                )
                return False
            log = "%s %s out-->%s err-->%s  \n" % (log, c3, out, err)
        except Exception as err:
            tools.log(
                app="work_gen",
                type="WARNING",
                code="mount_failed",
                file_name="workload_generator.py",
                function_name="mount_volume",
                message="failed to run mount. return False",
                exception=err
            )
            return False

        tools.log(
            app="work_gen",
            type="INFO",
            code="mount_done",
            file_name="workload_generator.py",
            function_name="mount_volume",
            message="mount done. " + log
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
                app="work_gen",
                type="ERROR",
                code="concurrent_bug",
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

        if cinder_volume_id is None:
            return False

        cinder_volume_id = cinder_volume_id.encode('ascii', 'ignore')

        try:
            cinder = tools.get_cinder_client()

            while True:
                vol_reload = cinder.volumes.get(cinder_volume_id)

                if vol_reload.status != 'detaching':
                    break
                time.sleep(0.2)

            while True:
                vol_reload = cinder.volumes.get(cinder_volume_id)
                if vol_reload.status != 'creating':
                    break
                time.sleep(0.2)

            if vol_reload.status == 'available':
                self._delete_volume(
                    volume_id=cinder_volume_id,
                    is_deleted=is_deleted
                )

                tools.run_command(["sudo", "rm", "-d", "-r", mount_path + cinder_volume_id])

                return True
        except Exception as err:
            tools.log(
                app="work_gen",
                type="WARNING",
                code="del_vol_failed",
                file_name="workload_generator.py",
                function_name="delete_volume",
                message="error in delete volume. maybe failed to run 'rm' command because of memory shortage",
                exception=err)
            return False

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
                app="work_gen",
                type="WARNING",
                code="del_vol_not_exists",
                file_name="workload_generator.py",
                function_name="_detach_volume",
                message="attempt to delete a volume that does not exists. Probably [nova volume-attachment] returned a volume that does not exists",
                exception=err)

            return "volume-not-exists"

        if vol.status == "in-use":

            nova.volumes.delete_server_volume(nova_id, volume_id)

        else:
            tools.log(
                app="work_gen",
                type="ERROR",
                code="detach_failed",
                file_name="workload_generator.py",
                function_name="_detach_volume",
                message="attempted to detach, but volume status is not 'in-use' it is %s. volume_id: %s"
                        % (vol.status, volume_id))

            # raise Exception("ERROR [_detach_volume] volume status is not 'in-use' it is %s volume_id: %s" %
            #                 (vol.status, volume_id))

    def create_attach_volume(self):

        volume = self.create_volume()

        attach_result = self.attach_volume(wg.current_vm_id, volume.id)

        if attach_result is not None:

            tools.log(
                app="work_gen",
                type="INFO",
                code="mount_volume",
                file_name="workload_generator.py",
                function_name="create_attach_volume",
                message="going to mount volume. cinder_reported_device: %s volume: %s" % (
                    attach_result.device, volume.id)
            )

            mount_result = self.mount_volume(
                device_from_openstack_not_used=attach_result.device,
                volume=volume)

            if mount_result is False:
                tools.log(
                    app="work_gen",
                    type="WARNING",
                    code="mount_failed",
                    file_name="workload_generator.py",
                    function_name="create_attach_volume",
                    message="cinder_reported_device:%s volume_id: %s" % (attach_result.device, volume.id)
                )
                # remove the volume
                self.detach_delete_volume(
                    cinder_volume_id=volume.id,
                    is_deleted=2
                )

                return None
        else:
            return None

        return volume.id

    def detach_delete_all_volumes(self, mount_path="/media/"):
        """

        :param mount_path: must end with /
        :return:
        """

        print("detach_delete_all_volumes()")

        cinder = tools.get_cinder_client()

        nova = tools.get_nova_client()

        volumes = nova.volumes.get_server_volumes(self.current_vm_id)

        for volume in volumes[:]:
            # first umount
            device = tools.check_is_device_mounted_to_volume(volume.id)

            tools.umount_device(device)

            # to check the umount was successful
            device = tools.check_is_device_mounted_to_volume(volume.id)

            if device == '':

                self._detach_volume(self.current_vm_id, volume.id)


            # for any reason cannot umount therefor do not attempt to detach because it will mess the device value returned form the "nova volume-attach"
            else:

                volumes.remove(volume)

        # wait until all volumes are detached then attempt to remove them

        while len(volumes) > 0:

            for volume in volumes[:]:
                # Detaching
                try:
                    vol_reload = cinder.volumes.get(volume.id)
                except Exception as err:

                    tools.log(
                        app="work_gen",
                        type="ERROR",
                        code="del_vol_not_exists",
                        file_name="workload_generator.py",
                        function_name="detach_delete_all_volumes",
                        message="attempt to delete a volume that does not exists. Probably [nova volume-attachment] returned a volume that does not exists.",
                        exception=err)

                    volumes.remove(volume)
                    continue

                if vol_reload.status == 'detaching' or vol_reload.status == 'deleting':
                    continue

                if vol_reload.status == 'available':
                    self._delete_volume(volume.id)

                    try:
                        tools.run_command(["sudo", "rm", "-d", "-r", mount_path + volume.id])
                    except Exception as err:
                        tools.log(
                            app="work_gen",
                            type="WARNING",
                            code="failed_rm_dir",
                            file_name="workload_generator.py",
                            function_name="detach_delete_all_volumes",
                            message="failed to remove mounted directory. vol: " + volume.id,
                            exception=err)
                        return False

                    volumes.remove(volume)

        try:
            tools.run_command(["sudo", "rm", "-d", "-r", mount_path + "*"])
        except Exception as err:
            tools.log(
                app="work_gen",
                type="WARNING",
                code="failed_rm_all",
                file_name="workload_generator.py",
                function_name="detach_delete_all_volumes",
                message="failed to remove all mounted directories.",
                exception=err)
            return False

    def remove_all_available_volumes(self):
        print("remove_all_available_volumes()")

        cinder = tools.get_cinder_client()

        for volume in cinder.volumes.list():
            if volume.status == 'available':
                self._delete_volume(volume.id)

    def start_simulation(self):
        # self.detach_delete_all_volumes()

        volumes = []

        while True:

            if len(volumes) < int(np.random.choice(self.max_number_volumes[0], 1, p=self.max_number_volumes[1])):

                volume_id = self.create_attach_volume()

                if volume_id is None:
                    continue

                workload_generator = wg.run_storage_workload_generator(volume_id)

                volume_create_time = datetime.now()

                volumes.append({
                    "id": volume_id,
                    "generator": workload_generator,
                    "create_time": volume_create_time
                })

            for volume in volumes[:]:

                if tools.get_time_difference(volume["create_time"]) > \
                        int(np.random.choice(
                            self.volume_life_seconds[0],
                            1,
                            p=self.volume_life_seconds[1])):
                    # terminate fio tests on the performance eval instance
                    try:
                        volume["generator"].terminate()
                    except Exception as err:
                        tools.log(
                            app="work_gen",
                            type="ERROR",
                            code="failed_terminate_generator",
                            file_name="workload_generator.py",
                            function_name="start_simulation",
                            message="failed to terminate the volume workload generator. volume:" + volume["id"],
                            exception=err)

                    try:
                        self.performance_evaluation_instance.terminate_fio_test(volume["id"])
                    except Exception as err:
                        tools.log(
                            app="work_gen",
                            type="ERROR",
                            code="failed_terminate_perf_eval",
                            file_name="workload_generator.py",
                            function_name="start_simulation",
                            message="failed to terminate the performance evaluator. volume:" + volume["id"],
                            exception=err)

                    try:
                        self.detach_delete_volume(volume["id"])
                    except Exception as err:
                        tools.log(
                            app="work_gen",
                            type="ERROR",
                            code="failed_detach_delete_volume",
                            file_name="workload_generator.py",
                            function_name="start_simulation",
                            message="failed to detach delete volume. volume:" + volume["id"],
                            exception=err)

                    volumes.remove(volume)

            self.performance_evaluation_instance.run_fio_test()

            time.sleep(0.5)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Synthetic workload generator.')

    parser.add_argument('commands', type=str, nargs='+',
                        choices=['det-del', 'del-avail', 'start', 'storage', 'add'],
                        help=
                        """define what is the main function command:
                        [add -> attach and mount a new volume]
                        [storage -> generatore fio workload only on the current attached volumes. If no volume, exit]
                        [start -> start the simulation by constantly adding and removing volumes and simulate storage workload using fio]
                        [del-avail -> deletes all available volums]
                        [det-del -> detach and delete all volumes attached to the current server. Id --volume is given only detach and delete the single volume.]
                        """
                        )

    temp_required = False

    parser.add_argument('--fio_test_name', default="workload_generator.fio", metavar='', type=str,
                        required=temp_required, help='Test name for fio')

    parser.add_argument('--volume', type=str, metavar='', required=False,
                        help='Specify volume id to do operation on. For example for det-del a single volume.')

    parser.add_argument('--request_read_iops', default='[]', metavar='', type=str, required=temp_required,
                        help='example:[[500, 750, 1000], [0.5, 0.3, 0.2]]. will be fed to numpy.random.choice')

    parser.add_argument('--request_write_iops', default='[]', metavar='', type=str, required=temp_required,
                        help='example:[[500, 750, 1000], [0.5, 0.3, 0.2]]. will be fed to numpy.random.choice')

    parser.add_argument('--delay_between_workload_generation', default='[]', metavar='', type=str,
                        required=temp_required,
                        help='wait before generation - seconds. example:[[500, 750, 1000], [0.5, 0.3, 0.2]]. will be fed to numpy.random.choice')

    parser.add_argument('--max_number_volumes', default='[]', metavar='', type=str, required=temp_required,
                        help='maximum number of volumes to be created. example:[[500, 750, 1000], [0.5, 0.3, 0.2]]. will be fed to numpy.random.choice')

    parser.add_argument('--volume_life_seconds', default='[]', metavar='', type=str, required=temp_required,
                        help='delete a volume after th specified second upon its creation. example:[[500, 750, 1000], [0.5, 0.3, 0.2]]. will be fed to numpy.random.choice')

    parser.add_argument('--volume_size', default='[]', type=str, metavar='', required=temp_required,
                        help='Specify volume id to do operation on. For example for det-del a single volume. example:[[500, 750, 1000], [0.5, 0.3, 0.2]]. will be fed to numpy.random.choice')

    parser.add_argument('--wait_after_volume_rejected', default='[[30], [1.0]]', type=str, metavar='',
                        required=temp_required,
                        help='volume rejected wait before request for new volume. For example for det-del a single volume. example:[[500, 750, 1000], [0.5, 0.3, 0.2]]. will be fed to numpy.random.choice')
    # Performance Evaluation Parameters

    parser.add_argument('--perf_fio_test_name', default="resource_evaluation.fio", metavar='', type=str,
                        required=False,
                        help='Test name for fio')

    parser.add_argument('--perf_terminate_if_takes', metavar='', type=int, required=False, default=150,
                        help='terminates an evaluation if takes more than specified seconds')

    parser.add_argument('--perf_restart_gap', metavar='', type=int, required=False, default=20,
                        help='gap between restarting each fio test')

    parser.add_argument('--perf_restart_gap_after_terminate', metavar='', type=int, required=False, default=50,
                        help='If terminated because of the TERMINATE_IF_TAKES, then restart after specified seconds')

    parser.add_argument('--perf_show_fio_output', type=str, metavar='', required=False, default='False',
                        help='show fio test output')

    # Performance Evaluation Parameters


    args = parser.parse_args()

    p = perf.PerformanceEvaluation(
        current_vm_id=tools.get_current_tenant_id(),

        fio_test_name=args.perf_fio_test_name,
        terminate_if_takes=args.perf_terminate_if_takes,
        restart_gap=args.perf_restart_gap,
        restart_gap_after_terminate=args.perf_restart_gap_after_terminate,
        show_fio_output=tools.str2bool(args.perf_show_fio_output)
    )

    wg = CinderWorkloadGenerator(
        current_vm_id=tools.get_current_tenant_id(),
        fio_test_name=args.fio_test_name,

        wait_after_volume_rejected=json.loads(args.wait_after_volume_rejected),
        request_read_iops=json.loads(args.request_read_iops),
        request_write_iops=json.loads(args.request_write_iops),
        delay_between_workload_generation=json.loads(args.delay_between_workload_generation),
        max_number_volumes=json.loads(args.max_number_volumes),
        volume_life_seconds=json.loads(args.volume_life_seconds),
        volume_size=json.loads(args.volume_size),
        performance_evaluation_instance=p
    )

    if "det-del" in args.commands:

        if args.volume:
            tools.log("det-del volume: %s" % args.volume, insert_db=False)
            wg.detach_delete_volume(args.volume)

        else:
            tools.log("det-del all volumes", insert_db=False)
            wg.detach_delete_all_volumes()

    elif "del-avail" in args.commands:
        tools.log("delete all available volumes", insert_db=False)
        wg.remove_all_available_volumes()

    elif "add" in args.commands:
        # tools.log("add,attach and mount a new volume", insert_db=False)
        # volume = wg.create_volume()
        # attach_result = wg.attach_volume(wg.current_vm_id, volume.id)
        #
        # if attach_result is not None:
        #     wg.mount_volume(attach_result.device, volume)
        pass

    elif "storage" in args.commands:
        # volume_id = "e48b41a6-c181-42eb-9b48-e04bcff02289"

        wg.run_storage_workload_generator_all_volums()

    elif "start" in args.commands:
        wg.start_simulation()
