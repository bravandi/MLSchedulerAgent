import tools
import time
import sys

import pdb

class WorkloadGenerator():

    current_columes = []

    current_vm_id = '2aac4553-7feb-4326-9028-bf923c3c88c3'

    def __init__(self):

        pass

    def create_volume(self):
        '''

        :return: returns volume object
        '''

        # TODO --name create a naming convention something like tenant hostname + an index

        # todo use cinder python api
        cinder = tools.get_cinder_client()

        volume = cinder.volumes.create(1, name="vol2")

        return volume

    def attach_volume(self, instance_id, volume_id):
        '''

        :param instance_id:
        :param volume_id:
        :return:    result.volumeId: the same volume id
                    result.device: the device in the tenant operation system that the volume is attached to
        '''

        print ("attach_volume instance_id=%s volume_id=%s", instance_id, volume_id)

        # wait until the volume is ready
        tools.cinder_wait_for_volume_status(volume_id, status="available")

        nova = tools.get_nova_client()

        result = nova.volumes.create_server_volume(instance_id, volume_id)

        return result

    def mount_volume(self, device, volume, base_path = "/media/"):
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

    def detach_delete_all_volumes(self):
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
                    volumes.remove(volume)

    def remove_all_available_volumes(self):
        print("remove_all_available_volumes()")

        cinder = tools.get_cinder_client()

        for volume in cinder.volumes.list():
            if volume.status == 'available':
                cinder.volumes.delete(volume.id)

if __name__ == "__main__":

    wg = WorkloadGenerator()

    if("det-del" in sys.argv):
        wg.detach_delete_all_volumes()

    elif ("del-avail" in sys.argv):
        wg.remove_all_available_volumes()

    else:

        volume = wg.create_volume()

        attach_result = wg.attach_volume(wg.current_vm_id, volume.id)

        # print(attach_result)

        # device_attached = "/dev/vdd"

        wg.mount_volume(attach_result.device, volume)