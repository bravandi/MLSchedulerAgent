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
import novaclient
import cinderclient


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
                 volume_attach_time_out,
                 wait_volume_status_timeout,
                 performance_evaluation_args,
                 workload_id=0):
        """

        :param workload_id: if equal to 0 it will create new workload by capturing the current experiment requests
        :param current_vm_id:
        :param fio_test_name:
        :param delay_between_storage_workload_generation:
        :return:
        """

        communication.insert_tenant(
            experiment_id=CinderWorkloadGenerator.experiment["id"],
            description=tools.get_current_tenant_description(),
            nova_id=tools.get_current_tenant_id()
        )

        self.performance_evaluation_args = performance_evaluation_args

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
        self.wait_volume_status_timeout = wait_volume_status_timeout
        self.volume_attach_time_out = volume_attach_time_out

        self.delete_detach_volumes_list = {}  # contains volume id

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
            time.sleep(1)
            # todo recursive DEADLOCK risk however, if upon start of the application an attached volume is left, then the simulation wont work properly
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
                    if self._detach_volume(self.current_vm_id, volume.id) in ['successful', 'not-found']:
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
                app="MAIN_WORKGEN",
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

        except cinderclient.exceptions.ClientException as err:

            # ERR: The server has either erred or is incapable of performing the requested operation

            # todo shutdown the application in this case. even worse, might need to reset the api server
            # ERR: The server has either erred or is incapable of performing the requested operation

            tools.log(
                app="agent",
                type="ERROR",
                code="server-incapable-create-vol",
                file_name="workload_generator.py",
                function_name="create_volume",
                message="failed to get create volume",
                exception=err
            )

            return 'server-incapable-create-vol'

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
                app="MAIN_WORKGEN",
                type="WARNING",
                code="rejected|vol_status_error",
                file_name="workload_generator.py",
                function_name="attach_volume",
                message="Reason: Assume volume is rejected. Cannot distinguish rejection or another reason for having error status. VOLUME DELETED because status is 'error'",
                volume_cinder_id=volume_id,
            )

            return None

        tools.log(
            app="MAIN_WORKGEN",
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
                app="MAIN_WORKGEN",
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

        # WARNING I know there is a case that two volumes get attached at same time, therefore two devices gets ready
        # and it only picks one of them this can cause testing/writing to a wrong volume since device maps the
        # underlying attachment process. Therefore must detach and remove the volume.
        device = ''
        already_attached_devices = set()

        try:
            already_attached_devices = tools.get_attached_devices()
        except Exception as err:
            tools.log(
                app="MAIN_WORKGEN",
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
        while tools.get_time_difference(start_time) < self.volume_attach_time_out:
            try:
                new_device = tools.get_attached_devices() - already_attached_devices
            except Exception as err:
                tools.log(
                    app="MAIN_WORKGEN",
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
                        app="MAIN_WORKGEN",
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

        if device.strip() == '' or device is None:
            tools.log(
                app="MAIN_WORKGEN",
                volume_cinder_id=volume.id,
                type="WARNING",
                code="device_find_timeout",
                file_name="workload_generator.py",
                function_name="mount_volume",
                message="Timeout to find device. timeout threshold > " + str(self.volume_attach_time_out)
            )

            return False

        tools.log(
            app="MAIN_WORKGEN",
            type="INFO",
            file_name="workload_generator.py",
            function_name="mount_volume",
            message="try to mount_volume device: %s" % device,
            volume_cinder_id=volume.id,
            insert_db=False)

        c1 = c2 = c3 = None

        # log = ""
        try:
            c1 = ["sudo", 'mkfs', '-t', "ext3", device]
            out, err, p = tools.run_command(c1, debug=True)
            if "in use by the system" in err:
                tools.log(
                    app="MAIN_WORKGEN",
                    type="ERROR",
                    code="mkfs_stderr",
                    file_name="workload_generator.py",
                    function_name="mount_volume",
                    volume_cinder_id=volume.id,
                    message="Format/mkfs failed. command: %s STDOUT: %s" % (" ".join(c1), out),
                    exception=err
                )
                return False
                # log = "%s %s out-->%s err-->%s  \n" % (log, c1, out, err)
        except Exception as err:
            tools.log(
                app="MAIN_WORKGEN",
                volume_cinder_id=volume.id,
                type="ERROR",
                code="mkfs_exception",
                file_name="workload_generator.py",
                function_name="mount_volume",
                message="failed to run mkfs. command: " + " ".join(c1),
                exception=err
            )
            return False

        mount_to_path = base_path + volume.id

        try:
            c2 = ["sudo", 'mkdir', mount_to_path]
            out, err, p = tools.run_command(c2, debug=True)

            if err != "":
                tools.log(
                    app="MAIN_WORKGEN",
                    volume_cinder_id=volume.id,
                    type="ERROR",
                    code="mkdir_stderr",
                    file_name="workload_generator.py",
                    function_name="mount_volume",
                    message="mkdir stderr not empty. command: %s stdout:%s " % (" ".join(c2), out),
                    exception=err
                )
                return False
                # log = "%s %s out-->%s err-->%s  \n" % (log, c2, out, err)
        except Exception as err:
            tools.log(
                app="MAIN_WORKGEN",
                type="ERROR",
                volume_cinder_id=volume.id,
                code="mkdir_exception",
                file_name="workload_generator.py",
                function_name="mount_volume",
                message="failed to run mkdir. command: " + " ".join(c2),
                exception=err
            )
            return False

        try:
            c3 = ["sudo", 'mount', device, mount_to_path]
            out, err, p = tools.run_command(c3, debug=True)

            if err != "":
                tools.log(
                    app="MAIN_WORKGEN",
                    type="ERROR",
                    volume_cinder_id=volume.id,
                    code="mount_stderr",
                    file_name="workload_generator.py",
                    function_name="mount_volume",
                    message="mount stderr not empty. cmd: " + " ".join(c3),
                    exception=err
                )
                return False
                # log = "%s %s out-->%s err-->%s  \n" % (log, c3, out, err)
        except Exception as err:
            tools.log(
                app="MAIN_WORKGEN",
                volume_cinder_id=volume.id,
                type="ERROR",
                code="mount_exception",
                file_name="workload_generator.py",
                function_name="mount_volume",
                message="failed to run mount. command:" + " ".join(c3),
                exception=err
            )
            return False

        tools.log(
            app="MAIN_WORKGEN",
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
                        app="MAIN_WORKGEN",
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

            if result == "not-found":
                return True

            if result == "nova-vol-detach-failed":
                return False

        else:
            tools.log(
                app="MAIN_WORKGEN",
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

            return True

        except cinderclient.exceptions.NotFound as err:
            return True

        except cinderclient.exceptions.BadRequest as err:
            # 'Invalid volume: Volume status must be available or error or error_restoring or error_extending and must not be migrating, attached, belong to a consistency group or have snapshots. (HTTP 400) (Request-ID: req-41d22e3e-9805-4da4-b184-e27f45d8fe01)'

            if "Volume status must be available or error or error" in str(err) is False:
                tools.log(
                    app="MAIN_WORKGEN",
                    type="ERROR",
                    volume_cinder_id=volume_id,
                    code="cinder_del_vol_failed",
                    file_name="workload_generator.py",
                    function_name="_delete_volume",
                    # message="[FROM FUNC: %s, STATUS: %s] cinder client failed to delete the volume" %
                    #         (debug_call_from, cinder_vol.status),
                    message="[FROM FUNC: %s] Bad request" % debug_call_from,
                    exception=err)

                # pass
        except Exception as err:

            if "No volume with a name or ID of" in str(err) or "could not be found" in str(err):
                tools.log(
                    app="MAIN_WORKGEN",
                    type="WARNING",
                    volume_cinder_id=volume_id,
                    code="cinder_del_general_fail",
                    file_name="workload_generator.py",
                    function_name="_delete_volume",
                    message="[FROM FUNC: %s] attempt to delete failed" % debug_call_from,
                    exception=err)

                return True

        # try to delete later. if is_delete = 2, then means volume wont be counted in reports
        if self.delete_detach_volumes_list.has_key(volume_id) is False:
            self.delete_detach_volumes_list[volume_id] = is_deleted

        return False

    def _detach_volume(self, nova_id, volume):
        nova = tools.get_nova_client()

        if isinstance(volume, basestring):
            volume_id = volume
        else:
            volume_id = volume.id

        # vol = tools.get_cinder_volume(volume_id, debug_call_from="_detach_volume")
        # if vol == "volume-not-exists":
        #     return "volume-not-exists"

        # if vol.status == "in-use":
        try:
            nova.volumes.delete_server_volume(nova_id, volume_id)

        except novaclient.exceptions.NotFound as err:
            return 'not-found'

        except novaclient.exceptions.BadRequest as err:

            if tools.get_volume_status(volume_id) in ["available", 'error']:
                # in case of str(err) --> Invalid volume: Volume must be attached in order to detach.
                return 'successful'

            # in case of str(err) --> #Invalid input received: Invalid volume: Unable to detach volume.
            # Volume status must be 'in-use' and attach_status must be 'attached' to detach.
            # Lets try to check if volume is not attached, then reset its status to error

            # todo tools.check_is_device_attached() should be called but it is too much work to implement
            # hopefully will work fun now. Because tools.check_is_device_mounted_to_volume is based
            # on df not fdisk
            if tools.check_is_device_mounted_to_volume(volume_id) == '':
                cinder = tools.get_cinder_client()
                try:
                    cinder.volumes.reset_state(volume_id, 'error', 'detached')
                except Exception as err:
                    return "reset-status-failed"

            return "attempted-reset-state"

        except Exception as err:

            tools.log(
                app="MAIN_WORKGEN",
                type="ERROR",
                volume_cinder_id=volume_id,
                code="nova_del_vol_failed",
                file_name="workload_generator.py",
                function_name="_detach_volume",
                message="attempt to detach a volume, openstack failed.",
                exception=err)

            return 'nova-vol-detach-failed'

        # else:
        #     tools.log(
        #         app="MAIN_WORKGEN",
        #         type="ERROR",
        #         volume_cinder_id=volume_id,
        #         code="detach_failed",
        #         file_name="workload_generator.py",
        #         function_name="_detach_volume",
        #         message="attempted to detach, but volume status is not 'in-use' it is %s" % vol.status)

        return 'successful'

    def create_attach_mount_volume(self):
        volume = self.create_volume()

        if volume == 'server-incapable-create-vol':
            return None, volume

        if volume is None:
            return None, "failed"

        attach_result = self.attach_volume(wg.current_vm_id, volume.id)

        if attach_result is not None:

            tools.log(
                app="MAIN_WORKGEN",
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
            app="MAIN_WORKGEN",
            type="INFO",
            code="start_simulation",
            file_name="workload_generator.py",
            function_name="start_simulation",
            message="tenant_id: %s" % (tools.get_current_tenant_id()))

        self.detach_delete_all_volumes()

        # "id": volume_id, "generator":, "perf_test":,  "last_test_time":, "create_time", "active":
        workgen_volumes = []

        last_rejected_create_volume_time = None
        rejection_hold_create_new_volume_request = False

        last_create_volume_time = None
        workload_generate_hold_create_new_volume_request = False

        # try:

        # never use continue in this loop, there are multiple independent tasks here
        while True:
            print ("LOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOP")

            # region <<<<<<<<<<<<<<<<<<<<<DELETE DETACH MARKED VOLUMES>>>>>>>>>>>>>>>>>>>>>>>>>>>>
            for volume_id in self.delete_detach_volumes_list.keys():

                find_workload_gen = [wg for wg in workgen_volumes if wg["id"] == volume_id]
                workload_gen = None
                if len(find_workload_gen) == 1:
                    workload_gen = find_workload_gen[0]

                if workload_gen is not None:
                    if workload_gen["perf_test"] is not None and \
                            workload_gen["perf_test"].is_perf_alive():
                        continue  # wait until perf-fio-test is done
                    if workload_gen["generator"] is not None and \
                                    workload_gen["generator"].is_alive() is True:
                        continue  # wait until workgen-fio is done

                if self.detach_volume(cinder_volume_id=volume_id):

                    out, err, p = tools.run_command([
                        "sudo", "rm", "-d", "-r", CinderWorkloadGenerator.mount_path + volume_id])

                    if self._delete_volume(
                            volume_id,
                            is_deleted=self.delete_detach_volumes_list[volume_id],
                            debug_call_from="start_simulation") is True:
                        #
                        del self.delete_detach_volumes_list[volume_id]

                        if workload_gen in workgen_volumes:
                            workgen_volumes.remove(workload_gen)
            # endregion

            # region <<<<<<<<<<<<<<<<<<<HOLD for REJECTION or VOLUME GENERATION GAP>>>>>>>>>>>>>>>>
            # hold requesting new volumes if one is rejected
            if rejection_hold_create_new_volume_request is True:
                rejection_hold_create_new_volume_request = False

                gap = int(
                    np.random.choice(self.wait_after_volume_rejected[0], 1, p=self.wait_after_volume_rejected[1]))

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
            # endregion

            # region <<<<<<<<<<<<<<<<<<<START MEW VOLUME REQUEST>>>>>>>>>>>>>>>>>>>>>>>>>

            active_workgen_volumes = [workgen_volume for workgen_volume in workgen_volumes if
                                      workgen_volume["active"] is True]

            if workload_generate_hold_create_new_volume_request is False and \
                            rejection_hold_create_new_volume_request is False and \
                            len(active_workgen_volumes) < int(
                        np.random.choice(self.max_number_volumes[0], 1, p=self.max_number_volumes[1])):

                last_create_volume_time = datetime.now()
                workload_generate_hold_create_new_volume_request = True

                volume_id, result = self.create_attach_mount_volume()

                if result == 'server-incapable-create-vol':
                    raise Exception("server-incapable-create-vol")

                tools.log(
                    app="MAIN_WORKGEN",
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

                    self.delete_detach_volumes_list[volume_id] = 2

                elif volume_id is not None or result == "successful":
                    volume_create_time = datetime.now()

                    new_workgen_volume = {
                        "id": volume_id,
                        "generator": None,  # will create upon time to the run storage generator
                        "perf_test": None,  # will create upon time to run performance test
                        "last_test_time": datetime.now(),
                        "create_time": volume_create_time,
                        "active": True
                    }

                    workgen_volumes.append(new_workgen_volume)
                    active_workgen_volumes.append(new_workgen_volume)
            # endregion

            # region <<<<<<<<<<<<<<<<<<<<<<<<<REMOVE EXPIRED VOLUMES>>>>>>>>>>>>>>>>>>>>>>>>>>>>
            for workgen_volume in active_workgen_volumes:
                if tools.get_time_difference(workgen_volume["create_time"]) > \
                        int(np.random.choice(
                            self.volume_life_seconds[0],
                            1,
                            p=self.volume_life_seconds[1])):
                    # terminate fio tests on the performance eval instance
                    # no need to call <workgen_volume["generator"].terminate()>, it terminates automatically

                    self.delete_detach_volumes_list[workgen_volume["id"]] = 1
                    workgen_volume["active"] = False

            # endregion

            # region <<<<<<<<<<<<<<START PERFORMANCE EVALUATIONS and STORAGE GENERATORS>>>>>>>>>>>>>>>>>>

            for workgen_volume in active_workgen_volumes:
                volume_id = workgen_volume["id"]

                #  START START START>>> PERFORMANCE EVALUATION SECTION <<< START START START

                perf_test = workgen_volume["perf_test"]

                if perf_test is None:
                    perf_test = perf.PerformanceEvaluation(
                        current_vm_id=tools.get_current_tenant_id(),
                        fio_test_name=self.performance_evaluation_args["fio_test_name"],
                        terminate_if_takes=self.performance_evaluation_args["terminate_if_takes"],
                        restart_gap=self.performance_evaluation_args["restart_gap"],
                        restart_gap_after_terminate=self.performance_evaluation_args[
                            "restart_gap_after_terminate"],
                        show_fio_output=self.performance_evaluation_args["show_fio_output"],
                        volume_id=volume_id
                    )

                    if perf_test.initialize() == 'failed-copy-perf-eval-fio-test-file':

                        # if failed to finish one time initialize then do not consider it in the reports
                        if self.delete_detach_volumes_list.has_key(volume_id) is False:
                            self.delete_detach_volumes_list[volume_id] = 2
                        workgen_volume["active"] = False
                        continue

                    else:
                        workgen_volume["perf_test"] = perf_test

                result_run_fio = perf_test.run_fio_test()
                # END END END>>> PERFORMANCE EVALUATION SECTION <<<END END END

                # START START START>>> STORAGE WORKLOAD GENERATOR SECTION <<< START START START

                # based on each volume creation time start storage workload generator for them
                if tools.get_time_difference(workgen_volume["last_test_time"]) >= int(np.random.choice(
                        self.delay_between_storage_workload_generation[0],
                        1,
                        p=self.delay_between_storage_workload_generation[1]
                )):

                    workload_generator = workgen_volume["generator"]

                    if workload_generator is None:
                        #
                        workload_generator = \
                            storage_workload_gen.StorageWorkloadGenerator.create_storage_workload_generator(
                                volume_id=volume_id,
                                fio_test_name=self.fio_test_name,
                                delay_between_storage_workload_generation=self.delay_between_storage_workload_generation
                            )

                        if workload_generator == 'failed-copy-fio-file':
                            # it might failed to detach because the volume is detached, or removed from
                            # the 'workgen_volumes' earlier than this point

                            if self.delete_detach_volumes_list.has_key(volume_id) is False:
                                self.delete_detach_volumes_list[volume_id] = 1
                            workgen_volume["active"] = False

                            continue

                        workgen_volume["generator"] = workload_generator

                    workload_generator.start()
                    #  END END END >>> STORAGE WORKLOAD GENERATOR SECTION <<<END END END
            # endregion

            time.sleep(1)
        # except Exception as err:
        #
        #     tools.log(
        #         app="MAIN_WORKGEN",
        #         type="ERROR",
        #         volume_cinder_id=volume_id,
        #         code="simulation_failed",
        #         file_name="workload_generator.py",
        #         function_name="start_simulation",
        #         message="simulation ended with an exception",
        #         exception=err)

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

    parser.add_argument('--save_info_logs', type=str, metavar='', required=False, default='False',
                        help='save INFO logs in database ?')

    # Performance Evaluation Parameters

    args = parser.parse_args()

    tools.save_info_logs = tools.str2bool(args.save_info_logs)

    wg = CinderWorkloadGenerator(
        current_vm_id=tools.get_current_tenant_id(),
        fio_test_name=args.fio_test_name,
        # todo make it a config
        volume_attach_time_out=18,
        # todo make it a config
        wait_volume_status_timeout=20,

        performance_evaluation_args={
            "fio_test_name": args.perf_fio_test_name,
            "terminate_if_takes": args.perf_terminate_if_takes,
            "restart_gap": args.perf_restart_gap,
            "restart_gap_after_terminate": args.perf_restart_gap_after_terminate,
            "show_fio_output": tools.str2bool(args.perf_show_fio_output)
        },

        wait_after_volume_rejected=json.loads(args.wait_after_volume_rejected),
        request_read_iops=json.loads(args.request_read_iops),
        request_write_iops=json.loads(args.request_write_iops),
        delay_between_storage_workload_generation=json.loads(args.delay_between_storage_workload_generation),
        delay_between_create_volume_generation=json.loads(args.delay_between_create_volume_generation),
        max_number_volumes=json.loads(args.max_number_volumes),
        volume_life_seconds=json.loads(args.volume_life_seconds),
        volume_size=json.loads(args.volume_size)
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
