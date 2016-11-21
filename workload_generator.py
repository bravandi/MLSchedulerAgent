import argparse
import os
import tools
import time
from multiprocessing import Process
import multiprocessing
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
                (str(start_time), command))

            out, err = tools.run_command(["sudo", CinderWorkloadGenerator.fio_bin_path, generator_instance.test_path], debug=False)

            if err != "":
                tools.log(
                    "   {ERROR} Time: %s\nVOLUME: %s\nERROR: %s" %
                    (str(start_time), generator_instance.volume_id, err))

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
                   (str(duration), str(iops_measured), generator_instance.volume_id, out, err))

            time.sleep(generator_instance.delay_between_workload_generation)


class CinderWorkloadGenerator:
    fio_bin_path = os.path.expanduser("~/fio-2.0.9/fio")
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
                 workload_id=0):
        """

        :param workload_id: if equal to 0 it will create new workload by capturing the current experiment requests
        :param current_vm_id:
        :param fio_test_name:
        :param delay_between_workload_generation:
        :return:
        """

        self.request_read_iops = request_read_iops
        self.request_write_iops = request_write_iops
        self.current_vm_id = current_vm_id
        self.fio_test_name = fio_test_name
        self.delay_between_workload_generation = delay_between_workload_generation
        self.workload_id = workload_id
        self.max_number_volumes = max_number_volumes
        self.volume_size = volume_size
        self.volume_life_seconds = volume_life_seconds

    def run_storage_workload_generator_all_volums(self):

        for volume in tools.get_all_attached_volumes(self.current_vm_id):

            self.run_storage_workload_generator(volume.id)

    def run_storage_workload_generator(self, volume_id):

        volume_path = "%s%s/" % (CinderWorkloadGenerator.mount_base_path, volume_id)
        test_path = volume_path + self.fio_test_name

        generator = StorageWorkloadGenerator(
            volume_id=volume_id,
            workload_type="",
            delay_between_workload_generation=self.delay_between_workload_generation,
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

        return generator

    def create_volume(self, size=None):
        '''

        :return: returns volume object
        '''

        if size is None:
            size = self.volume_size

        read_iops = np.random.choice(self.request_read_iops, 1, p=[0.5, 0.3, 0.2])
        write_iops = np.random.choice(self.request_write_iops, 1, p=[0.5, 0.3, 0.2])

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
            self._delete_volume(volume_id)
            tools.log("VOLUME DELETED because status is 'error' id: %s" % volume_id)
            return None

        print ("attach_volume instance_id=%s volume_id=%s", instance_id, volume_id)

        nova = tools.get_nova_client()

        result = nova.volumes.create_server_volume(instance_id, volume_id)

        return result

    def mount_volume(self, device, volume, base_path="/media/"):
        '''

        :param device: not used because openstack returns wrong device sometimes. So, nby comparing fdisk -l it finds the latest attached device
        :param volume: it must be an instance of volume object in the cinderclient
        :return:
        '''

        print ("mount_volume device: %s volume.id: %", device, volume.id)

        already_attached_devices = tools.get_attached_devices()

        # todo define a timeout !important
        # make sure the device is ready to be mounted
        while True:
            new_device = tools.get_attached_devices() - already_attached_devices

            if len(new_device) > 0:
                if len(new_device) > 1:
                    raise Exception("two devices attached at the same time, cannot identiify which one should be mounted to which voilume")
                device = new_device.pop()
                break

            # out, err = tools.run_command(["sudo", "fdisk", "-l"], debug=False)
            #
            # if device in out:
            #     break

        # out = tools.run_command2("reset", debug=True)

        out, err = tools.run_command(["sudo", 'mkfs', '-t', "ext3", device], debug=True)

        mount_to_path = base_path + volume.id

        out, err = tools.run_command(["sudo", 'mkdir', mount_to_path])

        out, err = tools.run_command(["sudo", 'mount', device, mount_to_path], debug=True)

        # todo instead of 3 seconds

    def detach_delete_volume(self, cinder_volume_id):

        self.detach_volume(cinder_volume_id)
        self.delete_volume(cinder_volume_id)

    def detach_volume(self, cinder_volume_id):

        device = tools.check_is_device_mounted_to_volume(cinder_volume_id)

        tools.umount_device(device)

        device = tools.check_is_device_mounted_to_volume(cinder_volume_id)

        if device == '':
            # detach volume

            if self._detach_volume(self.current_vm_id, cinder_volume_id) == "volume-not-exists":
                pass

        else:

            raise Exception("[detach_volume] the volume is not unmounted. volume_id: %s" % (cinder_volume_id))

        return device

    def delete_volume(self, cinder_volume_id, mount_path="/media/"):

        cinder = tools.get_cinder_client()

        while True:

            vol_reload = cinder.volumes.get(cinder_volume_id)

            if vol_reload.status != 'detaching':
                break

        if vol_reload.status == 'available':
            cinder.volumes.delete(cinder_volume_id)

            communication.delete_volume(cinder_id=cinder_volume_id)

            # remove the path that volume were mounted to. Because the workload generator will keep using ndisk to consistantly write data into the disk
            tools.run_command(["sudo", "rm", "-d", "-r", mount_path + cinder_volume_id])

    def _delete_volume(self, cinder_volume_id):
        cinder = tools.get_cinder_client()

        cinder.volumes.delete(cinder_volume_id)

        communication.delete_volume(cinder_id=cinder_volume_id)

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
            tools.log("ERROR [_detach_volume] attempt to delete a volume that does not exists. Probably [nova volume-attachment] returned a volume that does not exists. MSG: %s" % str(err))
            return "volume-not-exists"


        if vol.status == "in-use":

            nova.volumes.delete_server_volume(nova_id, volume_id)

        else:

            raise Exception("volume status is no 'in-use' it is %s volume_id: %s" %
                            (vol.status, volume_id))

    def create_attach_volume(self):

        volume = self.create_volume()

        attach_result = self.attach_volume(wg.current_vm_id, volume.id)

        if attach_result is not None:

            self.mount_volume(attach_result.device, volume)

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
                        "ERROR [detach_delete_all_volumes] attempt to delete a volume that does not exists. Probably [nova volume-attachment] returned a volume that does not exists. MSG: %s" % str(
                            err))
                    volumes.remove(volume)
                    continue

                if vol_reload.status == 'detaching' or vol_reload.status == 'deleting':

                    continue

                if vol_reload.status == 'available':
                    self._delete_volume(volume.id)

                    tools.run_command(["sudo", "rm", "-d", "-r", mount_path + volume.id])

                    volumes.remove(volume)

        tools.run_command(["sudo", "rm", "-d", "-r", mount_path + "*"])

    def remove_all_available_volumes(self):
        print("remove_all_available_volumes()")

        cinder = tools.get_cinder_client()

        for volume in cinder.volumes.list():
            if volume.status == 'available':
                self._delete_volume(volume.id)

    def start_simulation(self):
        self.detach_delete_all_volumes()

        volumes = []

        while True:

            if len(volumes) < self.max_number_volumes:

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

                if tools.get_time_difference(volume["create_time"]) > self.volume_life_seconds:
                    volume["generator"].terminate()
                    self.detach_delete_volume(volume["id"])
                    volumes.remove(volume)

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

    # parser.add_argument('--sum', dest='accumulate', action='store_const',
    #                     const=sum, default=max,
    #                     help='sum the integers (default: find the max)')

    parser.add_argument('--fio_test_name', default="workload_generator.fio", metavar='', type=str,
                        required=False,
                        help='Test name for fio')

    parser.add_argument('--delay_between_workload_generation', default=1, metavar='', type=float,
                        required=False,
                        help='wait before generation - seconds')

    parser.add_argument('--max_number_volumes', default=3, metavar='', type=int, required=False,
                        help='maximum number of volumes to be created')

    parser.add_argument('--volume_life_seconds', default=360, type=int, metavar='', required=False,
                        help='delete a volume after th specified second upon its creation.')

    parser.add_argument('--volume', type=str, metavar='', required=False,
                        help='Specify volume id to do operation on. For example for det-del a single volume.')

    parser.add_argument('--volume_size', default=2, type=int, metavar='', required=False,
                        help='Specify volume id to do operation on. For example for det-del a single volume.')

    args = parser.parse_args()

    wg = CinderWorkloadGenerator(
        current_vm_id=tools.get_current_tenant_id(),

        request_read_iops=[500, 750, 1000],
        request_write_iops=[300, 400, 500],
        fio_test_name=args.fio_test_name,
        delay_between_workload_generation=args.delay_between_workload_generation,
        max_number_volumes=args.max_number_volumes,
        volume_life_seconds=args.volume_life_seconds,
        volume_size=args.volume_size
    )

    if "det-del" in args.commands:

        if args.volume:
            tools.log("det-del volume: %s" % args.volume)
            wg.detach_delete_volume(args.volume)

        else:
            tools.log("det-del all volumes")
            wg.detach_delete_all_volumes()

    elif "del-avail" in args.commands:
        tools.log("delete all available volumes")
        wg.remove_all_available_volumes()

    elif "add" in args.commands:
        tools.log("add,attach and mount a new volume")
        volume = wg.create_volume()
        attach_result = wg.attach_volume(wg.current_vm_id, volume.id)

        if attach_result is not None:
            wg.mount_volume(attach_result.device, volume)

    elif "storage" in args.commands:
        # volume_id = "e48b41a6-c181-42eb-9b48-e04bcff02289"

        wg.run_storage_workload_generator_all_volums()

    elif "start" in args.commands:
        wg.start_simulation()
        # print communication.insert_volume_request(
        #     workload_id=1,
        #     capacity=1,
        #     type=0,
        #     read_iops=500,
        #     write_iops=500
        # )

    else:

        tools.log("Wrong command: %s. check --help" % sys.argv)