use MLScheduler;
select	set_experiment_config(@experiment_id, "max_number_vols", 0);
set  @experiment_id  = 34;
call report_experiment(87);
select @experiment_id := id from experiment order by id desc	limit 1;

select	set_experiment_config(@experiment_id, "assess_read_str_qos",  
	"[v1] >= 0.00");
select	set_experiment_config(@experiment_id, "assess_write_str_qos",  
	"[v1] >= 0.02");
#vol_count == 1 or 
call	report_experiment_config(@experiment_id);
call 	report_experiment(@experiment_id); # 214 vpm_count
call 	report_experiment(88);
/*
delete from log where experiment_id = @experiment_id and id > 0;
*/

select *
from (select	l.id, v.cinder_id, l.create_time, v.id as vid, b.cinder_id as backend, t.description as host, l.app, l.type, l.code, l.message, l.exception_message, l.file_name, l.function_name 
from	log l left join volume v on v.cinder_id = l.volume_cinder_id Inner Join backend	b on v.backend_ID = b.id Inner Join tenant t on	v.tenant_id	= t.id
where	l.experiment_id = @experiment_id #and l.code not in ('proc_null_is_alive', 'exp_null_is_alive')
		#and t.description like "%165%"
		#and b.cinder_id like "%block3%"
		#and l.code like "%device_find_timeout%"
		#and l.type like '%info%'
        #and l.function_name like '%mount%'
order by l.id desc limit 1000) i;
set  @experiment_id  = 86;

# number of attached failed per TENANT
select i.* from (select	t.description as tenant, l.type, 
#l.code as code , 
count(*) as cnt from	log l left join volume v on v.cinder_id = l.volume_cinder_id Inner Join backend	b on v.backend_ID = b.id Inner Join tenant t on	v.tenant_id	= t.id where	l.experiment_id = @experiment_id
	#and l.type  in ('ERROR') 
    and l.code like '%del_vol_code2%'
    #and (l.code like '%device%' or l.code like '%attach%' or l.code like '%mount%' or l.code like '%create%' or l.code like '%copy%')
    #and (l.code in ('nova_attach_failed', 'attach_failed_mount_failed_2') or l.code like '%device%')
	# device_find_timeout get_vol_status_failed nova_attach_failed nova_del_vol_failed perf_fio_stderr rejected|vol_status_error terminate_time_out
group by l.type, t.description
#,l.code 
limit 1000) i order by i.cnt desc;
/*
*/
#call update_clock(@experiment_id,0);
call get_training_dataset(@experiment_id, 0);
call report_experiment_config(@experiment_id);
call report_experiment(93);
call report_experiment(@experiment_id); # 214 vpm_count
# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@**********IMP*************  number of valid VPM count per BACKEND
select b.cinder_id, count(*) as valid_vpm_count from volume_performance_meter vpm  inner join volume v on vpm.experiment_id = @experiment_id and vpm.volume_id = v.id and vpm.terminate_wait = 0  and v.is_deleted < 2 inner join backend b on b.id = v.backend_id  group by b.cinder_id order by b.cinder_id asc;
/*
*/

# VPM report for each backend
select vpm.volume_id, b.cinder_id, t.description, vpm.read_iops, vpm.write_iops, vpm.duration, vpm.sla_violation_id, vpm.io_test_output, vpm.tenant_id, vpm.create_clock from  volume_performance_meter vpm inner join backend	b on vpm.backend_id = b.id inner join tenant t on vpm.tenant_id = t.id where vpm.experiment_id = @experiment_id
# and t.description like '%%'
# and b.cinder_id like '%block6@%'
order by vpm.id desc;

# WGEN report for each tenant
select t.description, wg.duration, wg.read_iops, wg.write_iops, wg.create_time from workload_generator wg  inner join tenant t on wg.tenant_id = t.id where t.experiment_id = @experiment_id
# and t.description like '%%'
# and b.cinder_id like '%block6@%'
order by wg.id desc;

# number of log TYPE in log per BLOCK
select i.block, i.err_type, i.cnt from (select	b.cinder_id as block, l.type as err_type, count(*) as cnt from	log l left join volume v on v.cinder_id = l.volume_cinder_id Inner Join backend	b on v.backend_ID = b.id Inner Join tenant t on	v.tenant_id	= t.id where	l.experiment_id = @experiment_id
	and l.type  in ('ERROR') 
# device_find_timeout get_vol_status_failed nova_attach_failed nova_del_vol_failed perf_fio_stderr rejected|vol_status_error terminate_time_out
group by l.type, b.cinder_id limit 1000) i order by i.cnt desc;

# number of log code in log per block
select * from (select	b.cinder_id, l.code, count(*) as frequency from	log l left join volume v on v.cinder_id = l.volume_cinder_id Inner Join backend	b on v.backend_ID = b.id Inner Join tenant t on	v.tenant_id	= t.id where	l.experiment_id = @experiment_id
	and l.code  in ('terminate_time_out', 'perf_fio_stderr', 'nova_del_vol_failed', 'device_find_timeout', 'get_vol_status_failed', 'nova_del_vol_failed', 'rejected|vol_status_error' ) 
    #and l.code  in ('terminate_time_out')
# terminate_time_out wgen_fio_stderr perf_fio_stderr device_find_timeout nova_attach_failed get_vol_status_failed  nova_del_vol_failed rejected|vol_status_error
group by l.code, b.cinder_id order by frequency desc limit 1000) i;
/*

*/


# number of terminate_time_out, perf_fio_stderr and wgen_fio_stderr and VPM per TENANT
select *
from (select  t.description as host, count(*) as number_of_terminated_per_eval
from	log l left join volume v on v.cinder_id = l.volume_cinder_id and v.is_deleted < 2 Inner Join backend	b on v.backend_ID = b.id Inner Join tenant t on	v.tenant_id	= t.id
where	l.experiment_id = @experiment_id and l.code in ('wgen_fio_stderr', 'perf_fio_stderr', 'terminate_time_out')
group by t.description #order by t.id desc
) i;

/*
g1-1@10.18.75.162
 	1
g1-2@10.18.75.163
 	2
g1-4@10.18.75.165
 	34
g1-5@10.18.75.166
 	34
g1-6@10.18.75.167
 	3
g1-7@10.18.75.168
 	1
g2-2@10.18.75.173
 	122
*/














# number of currect VPM per tenant
select  t.description as host, count(*) as number_of_valid_vpm
from	volume_performance_meter vpm left join volume v on vpm.experiment_id = @experiment_id and vpm.volume_id = v.id and vpm.terminate_wait =0 and v.is_deleted < 2 
Inner Join tenant t on	v.tenant_id	= t.id
group by t.description order by number_of_valid_vpm asc
;

# number of valid vpm count for each volume
select v.id as volume_id, v.cinder_id, count(*) vpm_count 
from volume_performance_meter vpm inner join volume v on vpm.volume_id = v.id and v.is_deleted < 2
where vpm.experiment_id = @experiment_id and vpm.terminate_wait = 0 group by v.cinder_id, v.id order by vpm_count desc;