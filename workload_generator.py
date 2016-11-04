import tools
import time
import sys
import threading
import communication
from datetime import datetime


class StorageWorkloadGenerator (threading.Thread):
    """

    """
    def __init__(self, volume_id, workload_type, delay_between_simulator=1.0):
        """

        :param workload_type:
        :param delay_between_simulator:
        :return:
        """

        threading.Thread.__init__(self)
        self.volume_id = volume_id
        self.workload_type = workload_type
        self.delay_between_simulator = delay_between_simulator

    def run(self):

        while True:
            command = "/usr/bin/ndisk/ndisk_8.4_linux_x86_64.bin -R -r 80 -b 32k -M 3 -f /media/%s/F000 -t 3600 -C 2M \n" % self.volume_id

            start_time = datetime.now()
            tools.log(
                "  %s--> start time ndisk on: %s  \ncommand: %s" %
                (threading.currentThread().name, str(start_time), command)
            )

            out = tools.run_command2(command)

            end_time = datetime.now()
            difference = (end_time - start_time)
            duration = difference.total_seconds()

            tools.log("%s Duration: %s\n%s" %
                   (threading.currentThread().name, str(duration), out))

            time.sleep(self.delay_between_simulator)


class CinderWorkloadGenerator():

    current_vm_id = '2aac4553-7feb-4326-9028-bf923c3c88c3'

    def __init__(self):

        self.storage_workload_generator_instances = []

    def run_storage_workload_generator(self):

        for volume in tools.get_all_attached_volumes(self.current_vm_id):

            generator = StorageWorkloadGenerator(
                volume_id=volume.id,
                workload_type="",
                delay_between_simulator=2.5)

            self.storage_workload_generator_instances.append(generator)

            generator.start()

    def create_volume(self, size=1):
        '''

        :return: returns volume object
        '''

        # TODO --name create a naming convention something like tenant hostname + an index

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

    wg = CinderWorkloadGenerator()

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