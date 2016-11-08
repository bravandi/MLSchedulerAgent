import os
import tools
import time
import sys
from multiprocessing import Process
import communication
from datetime import datetime
import pdb

class StorageWorkloadGenerator:
    """

    """
    def __init__(self, volume_id, workload_type, test_path, show_output=False, delay_between_generation=1.0):
        """

        :param workload_type:
        :param delay_between_generation:
        :return:
        """

        # threading.Thread.__init__(self)
        self.volume_id = volume_id
        self.workload_type = workload_type
        self.delay_between_simulator = delay_between_generation
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

    @staticmethod
    def run_workload_generator(generator_instance):

        while True:

            start_time = datetime.now()

            command = CinderWorkloadGenerator.fio_bin_path + " " + generator_instance.test_path

            # command = "/usr/bin/ndisk/ndisk_8.4_linux_x86_64.bin -R -r 80 -b 32k -M 3 -f /media/%s/F000 -t 3600 -C 2M \n" % generator_instance.volume_id
            tools.log(
                "   {run_f_test} Time: %s \ncommand: %s" %
                (str(start_time), command))

            out, err = tools.run_command([CinderWorkloadGenerator.fio_bin_path, generator_instance.test_path], debug=False)

            duration = tools.get_time_difference(start_time)

            iops_measured = tools.get_iops_measures_from_fio_output(out)

            communication.insert_workload_generator(
                tenant_id=1,
                duration=duration,
                read_iops=iops_measured["read"],
                write_iops=iops_measured["write"],
                command=command,
                output="OUTPUT_STD:%s\n ERROR_STD: %s" % (out, err))

            if generator_instance.show_output == False:
                out = "SHOW_OUTPUT = False"

            tools.log(" DURATION: %s IOPS: %s VOLUME: %s\n OUTPUT_STD:%s\n ERROR_STD: %s" %
                   (str(duration), str(iops_measured), generator_instance.volume_id, out, err))

            time.sleep(generator_instance.delay_between_simulator)


class CinderWorkloadGenerator:
    fio_bin_path = "/root/fio-2.0.9/fio"
    fio_tests_conf_path = "/root/MLSchedulerAgent/fio/"
    mount_base_path = '/media/'
    # storage_workload_generator_instances = []

    def __init__(self, current_vm_id, fio_test_name, delay_between_workload_generation):

        self.current_vm_id = current_vm_id
        self.fio_test_name = fio_test_name
        self.delay_between_workload_generation = delay_between_workload_generation

    def run_storage_workload_generator(self):

        for volume in tools.get_all_attached_volumes(self.current_vm_id):

            volume_path = "%s%s/" % (CinderWorkloadGenerator.mount_base_path, volume.id)
            test_path = volume_path + self.fio_test_name

            generator = StorageWorkloadGenerator(
                volume_id=volume.id,
                workload_type="",
                delay_between_generation=self.delay_between_workload_generation,
                show_output=False,
                test_path=test_path)

            # CinderWorkloadGenerator.storage_workload_generator_instances.append(generator)

            if True or os.path.isfile(test_path) == False:

                with open(CinderWorkloadGenerator.fio_tests_conf_path + self.fio_test_name, 'r') as myfile:
                    data = myfile.read().split('\n')

                    data[1] = "directory=" + volume_path

                    volume_test_file = open(test_path, 'w')

                    for item in data:
                        volume_test_file.write("%s\n" % item)

                    volume_test_file.close()

            generator.start()

    def create_volume(self, size=1):
        '''

        :return: returns volume object
        '''

        id = communication.insert_volume_request(
            workload_id=1,
            capacity=size,
            type=0,
            read_iops=500,
            write_iops=500
        )

        cinder = tools.get_cinder_client()

        volume = cinder.volumes.create(size, name=str(id))

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
        tools.cinder_wait_for_volume_status(volume_id, status="available")

        print ("attach_volume instance_id=%s volume_id=%s", instance_id, volume_id)

        nova = tools.get_nova_client()

        result = nova.volumes.create_server_volume(instance_id, volume_id)

        return result

    def mount_volume(self, device, volume, base_path="/media/"):
        '''

        :param device:
        :param volume: it must be an instance of volume object in the cinderclient
        :return:
        '''

        print ("mount_volume device: %s volume.id: %", device, volume.id)


        # todo define a timeout
        # make sure the device is ready to be mounted
        while True:

            out, err = tools.run_command(["fdisk", "-l"], debug=False)

            time.sleep(0.5)

            if device in out:
                break

        # out = tools.run_command2("reset", debug=True)

        out, err = tools.run_command(['mkfs', '-t', "ext3", device], debug=True)

        mount_to_path = base_path + volume.id

        out, err = tools.run_command(['mkdir', mount_to_path])

        out, err = tools.run_command(['mount', device, mount_to_path], debug=True)

        # todo instead of 3 seconds

    def detach_delete_volume(self, cinder_volume_id):

        self.detach_volume(cinder_volume_id)
        self.delete_volume(cinder_volume_id)

    def detach_volume(self, cinder_volume_id):

        nova = tools.get_nova_client()

        device = tools.check_is_device_mounted_to_volume(cinder_volume_id)

        tools.umount_device(device)

        device = tools.check_is_device_mounted_to_volume(cinder_volume_id)

        if device == '':
            # detach volume
            nova.volumes.delete_server_volume(self.current_vm_id, cinder_volume_id)

            # consider if deletion fails then what to do...
            communication.delete_volume(cinder_id=cinder_volume_id)

        return device

    def delete_volume(self, cinder_volume_id, mount_path="/media/"):

        cinder = tools.get_cinder_client()

        while True:

            vol_reload = cinder.volumes.get(cinder_volume_id)

            if vol_reload.status != 'detaching':
                break

        if vol_reload.status == 'available':
            cinder.volumes.delete(cinder_volume_id)

            # remove the path that volume were mounted to. Because the workload generator will keep using ndisk to consistantly write data into the disk
            tools.run_command(["rm", "-d", "-r", mount_path + cinder_volume_id])

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

                nova.volumes.delete_server_volume(self.current_vm_id, volume.id)

            # for any reason cannot umount therefor do not attempt to detach because it will mess the device value returned form the "nova volume-attach"
            else:

                volumes.remove(volume)

        # wait until all volumes are detached then attempt to remove them

        while len(volumes) > 0:

            for volume in volumes[:]:
                'Detaching'
                vol_reload = cinder.volumes.get(volume.id)

                if vol_reload.status == 'detaching' or vol_reload.status == 'deleting':

                    continue

                if vol_reload.status == 'available':
                    cinder.volumes.delete(volume.id)

                    # remove the path that volume were mounted to. Because the workload generator will keep using ndisk to consistantly write data into the disk
                    tools.run_command(["rm", "-d", "-r", mount_path + volume.id])

                    volumes.remove(volume)

    def remove_all_available_volumes(self):
        print("remove_all_available_volumes()")

        cinder = tools.get_cinder_client()

        for volume in cinder.volumes.list():
            if volume.status == 'available':
                cinder.volumes.delete(volume.id)

if __name__ == "__main__":

    wg = CinderWorkloadGenerator(
        current_vm_id=tools.get_current_tenant_id(),
        fio_test_name="workload_generator.fio",
        delay_between_workload_generation=0.5
    )

    if "det-del" in sys.argv:

        if len(sys.argv) == 2:

            wg.detach_delete_all_volumes()

        else:

            wg.detach_delete_volume(sys.argv[2])

        pass
    elif "del-avail" in sys.argv:
        wg.remove_all_available_volumes()

    elif "add" in sys.argv:

        volume = wg.create_volume()

        attach_result = wg.attach_volume(wg.current_vm_id, volume.id)

        wg.mount_volume(attach_result.device, volume)

    elif "storage" in sys.argv:
        # volume_id = "e48b41a6-c181-42eb-9b48-e04bcff02289"

        wg.run_storage_workload_generator()

    else:

        # print communication.insert_volume_request(
        #     workload_id=1,
        #     capacity=1,
        #     type=0,
        #     read_iops=500,
        #     write_iops=500
        # )

        pass