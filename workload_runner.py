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
from storage_workload_generator import StorageWorkloadGenerator


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
                 device,
                 volume_life_seconds):


        self.current_vm_id = current_vm_id
        self.fio_test_name = fio_test_name
        self.delay_between_workload_generation = delay_between_workload_generation
        self.volume_id = volume_id
        self.device = device
        self.volume_life_seconds = volume_life_seconds

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

        # generator.start()

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
            self._delete_volume(volume_id=volume_id)

            tools.log(
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

    def mount_volume(self, device_from_openstack_not_used, volume, base_path="/media/"):
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
                        type="WARNING",
                        code="work_gen_concurrent_bug",
                        file_name="workload_generator.py",
                        function_name="mount_volume",
                        message="already_attached_devices: %s \nnew_devic: %s \ntwo devices attached at the same time, can not identify which one should be mounted to which volume." % (
                        already_attached_devices, new_device))

                    return False

                device = new_device.pop()
                break

        print("try to mount_volume device: %s volume.id: %", device, volume.id)

        log = ""

        c1 = ["sudo", 'mkfs', '-t', "ext3", device]
        out, err = tools.run_command(c1, debug=True)

        if "in use by the system" in err:
            tools.log(
                type="ERROR",
                code="work_gen_in_use",
                file_name="workload_generator.py",
                function_name="mount_volume",
                message="%s out-->%s err-->%s  \n" % (c1, out, err)
            )

            return False

        log = "%s %s out-->%s err-->%s  \n" % (log, c1, out, err)

        mount_to_path = base_path + volume.id

        c2 = ["sudo", 'mkdir', mount_to_path]
        out, err = tools.run_command(c2, debug=True)

        if err != "":
            tools.log(
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
                type="ERROR",
                code="work_gen_mount_mount",
                file_name="workload_generator.py",
                function_name="mount_volume",
                message="%s out-->%s err-->%s  \n" % (c3, out, err)
            )

            return False

        log = "%s %s out-->%s err-->%s  \n" % (log, c3, out, err)

        tools.log(
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
                type="ERROR",
                code="work_gen",
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
                type="INFO",
                code="work_gen",
                file_name="workload_generator.py",
                function_name="create_attach_volume",
                message="going to mount volume. cinder_reported_device: %s volume: %s" % (attach_result.device, volume.id)
            )

            if self.mount_volume(
                    device_from_openstack_not_used=attach_result.device,
                    volume=volume) is False:

                tools.log(
                    type="WARNING",
                    code="work_gen_mount_failed",
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
                        type="ERROR",
                        code="work_gen",
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

                    tools.run_command(["sudo", "rm", "-d", "-r", mount_path + volume.id])

                    volumes.remove(volume)

        tools.run_command(["sudo", "rm", "-d", "-r", mount_path + "*"])

    def start_simulation(self):
        self.detach_delete_all_volumes()

        volumes = []

        # try to reduce the chance of having concurrent attachment
        # time.sleep(round(random.uniform(0.5, 4.1), 2))

        while True:

            if len(volumes) < int(np.random.choice(self.max_number_volumes[0], 1, p=self.max_number_volumes[1])):

                volume_id = self.create_attach_volume()

                if volume_id is None:
                    # if failed to create a volume wait for xx sec then retry
                    time.sleep(
                        int(np.random.choice(
                            self.wait_after_volume_rejected[0],
                            1,
                            p=self.wait_after_volume_rejected[1]))
                    )

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
                    volume["generator"].terminate()

                    self.detach_delete_volume(volume["id"])

                    volumes.remove(volume)

            time.sleep(0.5)


if __name__ == "__main__":

    while True:
        a = 1
        pass

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

    parser.add_argument('--device', type=str, metavar='', required=temp_required,
                        help='Specify device to attach the volume to.')

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
        device=args.device,
        delay_between_workload_generation=json.loads(args.delay_between_workload_generation),
        volume_life_seconds=json.loads(args.volume_life_seconds),
    )

    if "start" in args.commands:
        wg.start_simulation()
