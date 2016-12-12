import argparse
import tools
import time
import json
import communication
from datetime import datetime
import pdb
import numpy as np
import performance_evaluation as perf
import storage_workload_generator as storage_workload_gen


class CinderWorkloadGenerator:
    experiment = communication.Communication.get_current_experiment()
    mount_path = "/media/"  # must end with /

    def __init__(self,
                 current_vm_id,
                 fio_test_name,
                 delay_between_storage_workload_generation,
                 delay_between_create_volume_generation,
                 max_number_volumes,
                 volume_life_seconds,
                 volume_size,
                 request_read_iops,
                 request_write_iops,
                 wait_after_volume_rejected,
                 performance_evaluation_instance,
                 volume_attach_time_out,
                 wait_volume_status_timeout,
                 workload_id=0):
        """

        :param workload_id: if equal to 0 it will create new workload by capturing the current experiment requests
        :param current_vm_id:
        :param fio_test_name:
        :param delay_between_storage_workload_generation:
        :return:
        """

        self.wait_after_volume_rejected = wait_after_volume_rejected
        self.request_read_iops = request_read_iops
        self.request_write_iops = request_write_iops
        self.delay_between_create_volume_generation = delay_between_create_volume_generation
        self.current_vm_id = current_vm_id
        self.fio_test_name = fio_test_name
        self.delay_between_storage_workload_generation = delay_between_storage_workload_generation
        self.workload_id = workload_id
        self.max_number_volumes = max_number_volumes
        self.volume_size = volume_size
        self.volume_life_seconds = volume_life_seconds
        self.performance_evaluation_instance = performance_evaluation_instance
        self.wait_volume_status_timeout = wait_volume_status_timeout
        self.volume_attach_time_out = volume_attach_time_out

        self.delete_failed_to_attached_volumes = {}  # contains volume id

    def detach_delete_all_volumes(self):
        """

        :return:
        """

        tools.log(message="detach_delete_all_volumes()", insert_db=False)

        nova = tools.get_nova_client()

        try:

            volumes = nova.volumes.get_server_volumes(self.current_vm_id)

        except Exception as err:

            tools.log(
                app="work_gen",
                type="ERROR",
                code="detach_delete_all_volumes",
                file_name="workload_generator.py",
                function_name="get_all_attached_volumes",
                message="%s fetch server volumes failed" % tools.get_current_tenant_description(),
                exception=err
            )

            # todo DEADLOCK risk however, if upon start of the application an attached volume is left, then the simulation wont work properly

            time.sleep(1)
            self.detach_delete_all_volumes()

            return None

        volumes_copy = volumes[:]

        # todo DEADLOCK risk
        while len(volumes_copy) > 0:

            for volume in volumes_copy[:]:
                # first umount
                device = tools.check_is_device_mounted_to_volume(volume.id)

                tools.umount_device(device)

                # to check the umount was successful
                device = tools.check_is_device_mounted_to_volume(volume.id)

                if device == '':
                    if self._detach_volume(self.current_vm_id, volume.id) == 'successful':
                        volumes_copy.remove(volume)

        # wait until all remaining volumes are detached then attempt to remove them
        # todo DEADLOCK risk

        while len(volumes) > 0:

            for volume in volumes[:]:

                if self._delete_volume(volume.id, debug_call_from="detach_delete_all_volumes") is True:

                    try:
                        out, err, p = tools.run_command([
                            "sudo", "rm", "-d", "-r", CinderWorkloadGenerator.mount_path + volume.id])
                    except Exception as err:
                        tools.log(
                            app="work_gen",
                            type="ERROR",
                            volume_cinder_id=volume.id,
                            code="failed_rm_dir",
                            file_name="workload_generator.py",
                            function_name="detach_delete_all_volumes",
                            message="failed to remove mounted directory",
                            exception=err)
                        continue

                    volumes.remove(volume)
                else:
                    # could be any status like 'detaching', 'deleting', ''
                    time.sleep(1)

        try:
            out, err, p = tools.run_command(["sudo", "rm", "-d", "-r", CinderWorkloadGenerator.mount_path + "*"])
        except Exception as err:
            tools.log(
                app="work_gen",
                type="ERROR",
                volume_cinder_id=volume.id,
                code="failed_rm_all",
                file_name="workload_generator.py",
                function_name="detach_delete_all_volumes",
                message="failed to remove all mounted directories.",
                exception=err)

    def create_volume(self, size=None):
        """

        :param size:
        :return: returns volume object
        """

        if size is None:
            size = int(np.random.choice(self.volume_size[0], 1, self.volume_size[1]))

        read_iops = int(np.random.choice(self.request_read_iops[0], 1, p=self.request_read_iops[1]))
        write_iops = int(np.random.choice(self.request_write_iops[0], 1, p=self.request_write_iops[1]))

        db_id = communication.insert_volume_request(
            experiment_id=CinderWorkloadGenerator.experiment["id"],
            capacity=size,
            type=0,
            read_iops=read_iops,
            write_iops=write_iops
        )

        cinder = tools.get_cinder_client()

        try:
            volume = cinder.volumes.create(size, name="%s,%s" % (CinderWorkloadGenerator.experiment["id"], str(db_id)))
        except Exception as err:
            tools.log(
                app="agent",
                type="ERROR",
                code="create_vol_failed",
                file_name="workload_generator.py",
                function_name="create_volume",
                message="failed to get create volume",
                exception=err
            )

            time.sleep(1)
            return None

        # todo must call from scheduler it self
        # communication.add_volume(
        #     cinder_id=volume.id,
        #     backend_id=tools.Backend.specifications["id"],
        #     schedule_response=communication.ScheduleResponse.Accepted,
        #     capacity=size
        # )

        return volume

    def attach_volume(self, instance_id, volume_id):
        """
        :param instance_id:
        :param volume_id:
        :return:    result.volumeId: the same volume id
                    result.device: the device in the tenant operation system that the volume is attached to
                    None: failed
        """

        # wait until the volume is ready
        if tools.cinder_wait_for_volume_status(
                volume_id,
                status="available",
                timeout=self.wait_volume_status_timeout) is False:
            #

            tools.log(
                app="work_gen",
                type="WARNING",
                code="rejected|vol_status_error",
                file_name="workload_generator.py",
                function_name="attach_volume",
                message="Reason: Assume volume is rejected. Cannot distinguish rejection or another reason for having error status. VOLUME DELETED because status is 'error'",
                volume_cinder_id=volume_id,
            )

            return None

        tools.log(
            app="work_gen",
            type="INFO",
            file_name="workload_generator.py",
            function_name="attach_volume",
            message="attach_volume instance_id=%s volume_id=%s" % (instance_id, volume_id),
            volume_cinder_id=volume_id,
            insert_db=False)

        nova = tools.get_nova_client()

        try:
            result = nova.volumes.create_server_volume(instance_id, volume_id)
        except Exception as err:
            tools.log(
                app="work_gen",
                type="ERROR",
                code="nova_attach_failed",
                file_name="workload_generator.py",
                function_name="attach_volume",
                message="attach failed",
                volume_cinder_id=volume_id,
                exception=err
            )
            return None

        return result

    def mount_volume(self, device_from_openstack, volume, base_path="/media/"):
        """

        :param device_from_openstack: pass null if you want to find it using the 'df' and 'fdisk' commands. if buggy,
               do not use because openstack returns wrong device sometimes. So, nby comparing fdisk -l it finds the
               latest attached device
        :param volume: it must be an instance of volume object in the cinderclient
        :param base_path
        :return:
        """

        # todo I know there is a case that two volumes get attached at same time, therefore two devices gets ready
        # and it only picks one of them this can cause testing/writing to a wrong volume since device maps the
        # underlying attachment process. Therore must detach and remove the volume.
        device = ''
        already_attached_devices = set()

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
                exception=err,
                volume_cinder_id=volume.id
            )
            return False

        start_time = datetime.now()

        # make sure the device is ready to be mounted, if takes more than XX seconds drop it
        # todo make this a config
        while tools.get_time_difference(start_time) < self.volume_attach_time_out:
            try:
                new_device = tools.get_attached_devices() - already_attached_devices
            except Exception as err:
                tools.log(
                    app="work_gen",
                    type="ERROR",
                    code="get_attached_devices",
                    file_name="workload_generator.py",
                    function_name="mount_volume",
                    message="failed to get attached devices. will retry in the while true loop.",
                    exception=err,
                    volume_cinder_id=volume.id
                )
                # too much load on OS
                time.sleep(0.1)
                continue

            if len(new_device) > 0:
                if len(new_device) > 1:
                    tools.log(
                        app="work_gen",
                        type="ERROR",
                        code="concurrent_bug",
                        file_name="workload_generator.py",
                        function_name="mount_volume",
                        volume_cinder_id=volume.id,
                        message="already_attached_devices: %s \nnew_devic: %s \ntwo devices attached at the same time, can not identify which one should be mounted to which volume." % (
                            already_attached_devices, new_device))

                    return False

                device = new_device.pop()
                break

        tools.log(
            app="work_gen",
            type="INFO",
            file_name="workload_generator.py",
            function_name="mount_volume",
            message="try to mount_volume device: %s" % device,
            volume_cinder_id=volume.id,
            insert_db=False)

        # log = ""
        try:
            c1 = ["sudo", 'mkfs', '-t', "ext3", device]
            out, err, p = tools.run_command(c1, debug=True)
            if "in use by the system" in err:
                tools.log(
                    app="work_gen",
                    type="ERROR",
                    code="in_use",
                    file_name="workload_generator.py",
                    function_name="mount_volume",
                    volume_cinder_id=volume.id,
                    message="cannot mount because it is in use. %s out-->%s err-->%s  \n" % (c1, out, err)
                )
                return False
                # log = "%s %s out-->%s err-->%s  \n" % (log, c1, out, err)
        except Exception as err:
            tools.log(
                app="work_gen",
                volume_cinder_id=volume.id,
                type="ERROR",
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
            out, err, p = tools.run_command(c2, debug=True)

            if err != "":
                tools.log(
                    app="work_gen",
                    volume_cinder_id=volume.id,
                    type="ERROR",
                    code="mount_mkdir",
                    file_name="workload_generator.py",
                    function_name="mount_volume",
                    message="mkdir stderr not empty. %s out-->%s \n" % (c2, out),
                    exception=err
                )
                return False
                # log = "%s %s out-->%s err-->%s  \n" % (log, c2, out, err)
        except Exception as err:
            tools.log(
                app="work_gen",
                type="ERROR",
                volume_cinder_id=volume.id,
                code="mkdir_failed",
                file_name="workload_generator.py",
                function_name="mount_volume",
                message="failed to run mkdir. return False",
                exception=err
            )
            return False

        try:
            c3 = ["sudo", 'mount', device, mount_to_path]
            out, err, p = tools.run_command(c3, debug=True)

            if err != "":
                tools.log(
                    app="work_gen",
                    type="ERROR",
                    volume_cinder_id=volume.id,
                    code="mount_mount",
                    file_name="workload_generator.py",
                    function_name="mount_volume",
                    message="mount std err not empty. cmd: " + c3,
                    exception=err
                )
                return False
                # log = "%s %s out-->%s err-->%s  \n" % (log, c3, out, err)
        except Exception as err:
            tools.log(
                app="work_gen",
                volume_cinder_id=volume.id,
                type="ERROR",
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
            volume_cinder_id=volume.id,
            code="mount_done",
            file_name="workload_generator.py",
            function_name="mount_volume",
            message="mount done. "  # + log
        )

        return True

    def detach_delete_volume_rm_folder(self, cinder_volume_id, is_deleted=1):
        """

        :param cinder_volume_id:
        :param is_deleted: if set 2--> wont be counted as a deleted volume in reports
        :return:
        """

        if self.detach_volume(cinder_volume_id) is True:

            if self._delete_volume(
                    volume_id=cinder_volume_id,
                    is_deleted=is_deleted,
                    debug_call_from="detach_delete_volume"
            ) is True:

                try:
                    out, err, p = tools.run_command([
                        "sudo", "rm", "-d", "-r", CinderWorkloadGenerator.mount_path + cinder_volume_id])
                except Exception as err:
                    tools.log(
                        app="work_gen",
                        type="ERROR",
                        volume_cinder_id=cinder_volume_id,
                        code="remove_mounted_folder_failed",
                        file_name="workload_generator.py",
                        function_name="detach_delete_volume",
                        message="failed to remove the mounted folder",
                        exception=err
                    )

                    return "rm-failed"

                return "successful"

            else:
                return "delete-failed"

        else:

            "detach-failed"

    def detach_volume(self, cinder_volume_id):
        device = tools.check_is_device_mounted_to_volume(cinder_volume_id)

        tools.umount_device(device)

        device = tools.check_is_device_mounted_to_volume(cinder_volume_id)

        if device == '':
            # detach volume
            result = self._detach_volume(self.current_vm_id, cinder_volume_id)

            if result == "volume-not-exists":
                return True

            if result == "nova-vol-del-failed":
                return False

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

            return False

        return True

    def _delete_volume(self, volume_id, is_deleted=1, debug_call_from=''):
        """
        volume can be deleted if its status is: 'available', 'error', 'error_restoring', 'error_extending' and must
        not be migrating, attached, belong to a consistency group or have snapshots.
        :param volume_id:
        :param is_deleted:
        :param debug_call_from:
        :return:
        """
        if volume_id is None:
            return False

        volume_id = volume_id.encode('ascii', 'ignore')

        try:
            cinder = tools.get_cinder_client()

            cinder.volumes.delete(volume_id)

            communication.delete_volume(
                cinder_id=volume_id,
                is_deleted=is_deleted)
        except Exception as err:

            if "No volume with a name or ID of" in err or "could not be found" in err:
                tools.log(
                    app="work_gen",
                    type="WARNING",
                    volume_cinder_id=volume_id,
                    code="del_not_exist_vol",
                    file_name="workload_generator.py",
                    function_name="_delete_volume",
                    message="[FROM FUNC: %s] attempt delete none existing volume" % debug_call_from,
                    exception=err)

                return True
            else:

                cinder_vol = tools.get_cinder_volume(volume_id)
                # STATUS: %s        cinder_vol.status
                # Invalid volume: Volume status must be available or error or error_restoring or error_extending and must not be migrating, attached, belong to a consistency group or have snapshots. (HTTP 400) (Request-ID: req-48020904-b6b5-4c4c-9d3c-baad2539e224)
                tools.log(
                    app="work_gen",
                    type="ERROR",
                    volume_cinder_id=volume_id,
                    code="cinder_del_vol_failed",
                    file_name="workload_generator.py",
                    function_name="_delete_volume",
                    message="[FROM FUNC: %s, STATUS: %s] cinder client failed to delete the volume" %
                            (debug_call_from, cinder_vol.status),
                    exception=err)

            if is_deleted == 2:
                # try to delete later with is_delete = 2 that means volume wont be counted in reports
                self.delete_failed_to_attached_volumes[volume_id] = 2

            return False

        return True

    def _detach_volume(self, nova_id, volume):
        nova = tools.get_nova_client()

        if isinstance(volume, basestring):
            volume_id = volume
        else:
            volume_id = volume.id

        vol = tools.get_cinder_volume(volume_id, debug_call_from="_detach_volume")
        if vol == "volume-not-exists":
            return "volume-not-exists"

        if vol.status == "in-use":
            try:
                nova.volumes.delete_server_volume(nova_id, volume_id)
            except Exception as err:

                tools.log(
                    app="work_gen",
                    type="ERROR",
                    volume_cinder_id=volume_id,
                    code="nova_del_vol_failed",
                    file_name="workload_generator.py",
                    function_name="_detach_volume",
                    message="attempt to detach a volume, openstack failed.",
                    exception=err)

                return 'nova-vol-del-failed'

        else:
            tools.log(
                app="work_gen",
                type="ERROR",
                volume_cinder_id=volume_id,
                code="detach_failed",
                file_name="workload_generator.py",
                function_name="_detach_volume",
                message="attempted to detach, but volume status is not 'in-use' it is %s" % vol.status)

            # raise Exception("ERROR [_detach_volume] volume status is not 'in-use' it is %s volume_id: %s" %
            #                 (vol.status, volume_id))
        return 'successful'

    def create_attach_mount_volume(self):
        volume = self.create_volume()

        if volume is None:
            return None, "failed"

        attach_result = self.attach_volume(wg.current_vm_id, volume.id)

        if attach_result is not None:

            tools.log(
                app="work_gen",
                type="INFO",
                code="mount_volume",
                file_name="workload_generator.py",
                function_name="create_attach_volume",
                message="going to mount volume",
                volume_cinder_id=volume.id
            )

            mount_result = self.mount_volume(
                # device_from_openstack: pass null if you want to find it using the 'df' and 'fdisk' commands.
                device_from_openstack=None,  # attach_result.device,
                volume=volume)

            if mount_result is False:
                tools.log(
                    app="work_gen",
                    type="ERROR",
                    volume_cinder_id=volume.id,
                    code="mount_failed",
                    file_name="workload_generator.py",
                    function_name="create_attach_volume",
                    message="mount failed"
                )

                return volume.id, "mount-failed"
        else:
            return volume.id, "attach-failed"

        return volume.id.encode('ascii', 'ignore'), 'successful'

    def remove_all_available_volumes(self):
        print("remove_all_available_volumes()")

        cinder = tools.get_cinder_client()

        for volume in cinder.volumes.list():
            if volume.status == 'available':
                self._delete_volume(volume.id, debug_call_from="remove_all_available_volumes")

    def start_simulation(self):
        tools.log(
            app="work_gen",
            type="INFO",
            code="start_simulation",
            file_name="workload_generator.py",
            function_name="start_simulation",
            message="tenant_id: %s" % (tools.get_current_tenant_id()))

        self.detach_delete_all_volumes()

        workgen_volumes = []  # "id": volume_id, "generator":, "last_test_time":, "create_time"

        last_rejected_create_volume_time = None
        rejection_hold_create_new_volume_request = False

        last_create_volume_time = None
        workload_generate_hold_create_new_volume_request = False

        try:

            # never use continue in this loop, there are multiple independent tasks here
            while True:
                # region remove buggy volumes

                for volume_id in self.delete_failed_to_attached_volumes.keys():

                    if self.detach_volume(cinder_volume_id=volume_id):
                        out, err, p = tools.run_command([
                            "sudo", "rm", "-d", "-r", CinderWorkloadGenerator.mount_path + volume_id])

                        if self._delete_volume(
                                volume_id,
                                is_deleted=self.delete_failed_to_attached_volumes[volume_id],
                                debug_call_from="start_simulation") is True:
                            #
                            del self.delete_failed_to_attached_volumes[volume_id]
                # endregion

                # hold requesting new volumes if one is rejected
                if rejection_hold_create_new_volume_request is True:
                    rejection_hold_create_new_volume_request = False

                    gap = int(np.random.choice(self.wait_after_volume_rejected[0], 1, p=self.wait_after_volume_rejected[1]))

                    if tools.get_time_difference(last_rejected_create_volume_time) > gap:
                        #
                        rejection_hold_create_new_volume_request = False

                # apply create volume generation gap
                if workload_generate_hold_create_new_volume_request is True:
                    #
                    gap = int(np.random.choice(self.delay_between_create_volume_generation[0], 1,
                                               p=self.delay_between_create_volume_generation[1]))

                    if tools.get_time_difference(last_create_volume_time) > gap:
                        #
                        workload_generate_hold_create_new_volume_request = False

                # region start request new volumes

                # volume request section - will start storage ONE TIME workload generator on the created-attached volume
                if workload_generate_hold_create_new_volume_request is False and \
                                rejection_hold_create_new_volume_request is False and \
                                len(workgen_volumes) < int(
                            np.random.choice(self.max_number_volumes[0], 1, p=self.max_number_volumes[1])):

                    last_create_volume_time = datetime.now()
                    workload_generate_hold_create_new_volume_request = True

                    volume_id, result = self.create_attach_mount_volume()

                    tools.log(
                        app="work_gen",
                        type="INFO",
                        volume_cinder_id=volume_id,
                        code="create_attach_vol_result",
                        file_name="workload_generator.py",
                        function_name="create_attach_mount_volume",
                        message="CREATE_ATTACH RESULT: %s, %s" % (volume_id, result))

                    if volume_id is None or result == "failed":
                        # assume the reason is the volume_request is rejected
                        last_rejected_create_volume_time = datetime.now()
                        rejection_hold_create_new_volume_request = True

                    elif result == "mount-failed" or result == "attach-failed":
                        # pdb.set_trace()
                        self.delete_failed_to_attached_volumes[volume_id] = 2

                    elif volume_id is not None or result == "successful":
                        volume_create_time = datetime.now()

                        workgen_volumes.append({
                            "id": volume_id,
                            "generator": None,  # will create upon time to run test
                            "last_test_time": datetime.now(),
                            "create_time": volume_create_time
                        })
                # endregion

                # region remove expired volumes
                for workgen_volume in workgen_volumes[:]:
                    if tools.get_time_difference(workgen_volume["create_time"]) > \
                            int(np.random.choice(
                                self.volume_life_seconds[0],
                                1,
                                p=self.volume_life_seconds[1])):

                        # terminate fio tests on the performance eval instance
                        # no need to call <workgen_volume["generator"].terminate()>, it terminates automatically

                        self.performance_evaluation_instance.terminate_fio_test(workgen_volume["id"])

                        result = self.detach_delete_volume_rm_folder(workgen_volume["id"])

                        if result == "successful":
                            pass

                        elif result == "delete-failed" or result == "detach-failed":
                            self.delete_failed_to_attached_volumes[workgen_volume["id"]] = 1

                        elif result == "rm-failed":
                            # it will try to remove the old volume folder in media upon checking the
                            # self.delete_failed_to_attached_volumes
                            pass

                        workgen_volumes.remove(workgen_volume)
                # endregion

                # start performance evaluations
                # self.performance_evaluation_instance.run_fio_test()

                # region start perf evals and storage generators

                for workgen_volume in workgen_volumes[:]:
                    volume_id = workgen_volume["id"]

                    result_run_fio = self.performance_evaluation_instance.run_fio_test(volume_id)

                    if result_run_fio == 'failed-copy-perf-eval-fio-test-file':
                        # it might failed to detach because the volume is detached, or removed from
                        # the 'workgen_volumes' earlier than this point
                        if self.delete_failed_to_attached_volumes.has_key(volume_id) is False:
                            self.delete_failed_to_attached_volumes[volume_id] = 1

                        workgen_volumes.remove(workgen_volume)
                        continue

                    # based on each volume creation time start storage workload generator for them
                    if tools.get_time_difference(workgen_volume["last_test_time"]) >= int(np.random.choice(
                            self.delay_between_storage_workload_generation[0],
                            1,
                            p=self.delay_between_storage_workload_generation[1]
                    )):

                        workload_generator = workgen_volume["generator"]

                        if workload_generator is None:
                            workload_generator = \
                                storage_workload_gen.StorageWorkloadGenerator.create_storage_workload_generator(
                                    volume_id=volume_id,
                                    fio_test_name=self.fio_test_name,
                                    delay_between_storage_workload_generation=self.delay_between_storage_workload_generation
                                )

                            if workload_generator == 'failed-copy-fio-file':
                                # it might failed to detach because the volume is detached, or removed from
                                # the 'workgen_volumes' earlier than this point
                                if self.delete_failed_to_attached_volumes.has_key(volume_id) is False:
                                    self.delete_failed_to_attached_volumes[volume_id] = 1

                                workgen_volumes.remove(workgen_volume)
                                continue

                            workgen_volume["generator"] = workload_generator

                        workload_generator.start()
                # endregion

                time.sleep(0.8)
        except Exception as err:
            pdb.set_trace()

            tools.log(
                app="work_gen",
                type="ERROR",
                volume_cinder_id=volume_id,
                code="simulation_failed",
                file_name="workload_generator.py",
                function_name="start_simulation",
                message="simulation ended with an exception",
                exception=err)

        print("\n\n***************************************** died normally")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Synthetic workload generator.')

    parser.add_argument('commands', type=str, nargs='+',
                        choices=['det-del', 'del-avail', 'start', 'add'],
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

    parser.add_argument('--delay_between_storage_workload_generation', default='[]', metavar='', type=str,
                        required=temp_required,
                        help='wait before storage generation - seconds. example:"[[5], [1.0]]". will be fed to numpy.random.choice')

    parser.add_argument('--delay_between_create_volume_generation', default='[]', metavar='', type=str,
                        required=temp_required,
                        help='wait before volume-create requests - seconds. example:"[[5], [1.0]]". will be fed to numpy.random.choice')

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
        # todo make it a config
        volume_attach_time_out=18,
        # todo make it a config
        wait_volume_status_timeout=20,

        wait_after_volume_rejected=json.loads(args.wait_after_volume_rejected),
        request_read_iops=json.loads(args.request_read_iops),
        request_write_iops=json.loads(args.request_write_iops),
        delay_between_storage_workload_generation=json.loads(args.delay_between_storage_workload_generation),
        delay_between_create_volume_generation=json.loads(args.delay_between_create_volume_generation),
        max_number_volumes=json.loads(args.max_number_volumes),
        volume_life_seconds=json.loads(args.volume_life_seconds),
        volume_size=json.loads(args.volume_size),
        performance_evaluation_instance=p
    )

    if "det-del" in args.commands:

        if args.volume:
            tools.log("det-del", volume_cinder_id=args.volume, insert_db=False)
            wg.detach_delete_volume_rm_folder(args.volume)

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

    elif "start" in args.commands:
        wg.start_simulation()

    print("\n\n***************************************** died normally222")
