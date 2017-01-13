use MLScheduler;
/*
delete from log where id = @experiment_id;
*/


call insert_backend(
	'asdasdasd',
	@experiment_id,
	1,
	1,
	'DESC',
	'',
	12,
	now(),
    @id);

select * from backend where experiment_id = @experiment_id order by id desc;

delete from log where id > 0;
call	update_clock(@experiment_id,0);

select @experiment_id := id from experiment order by id desc	limit 1;
set @experiment_id  = 21;

call get_training_dataset(@experiment_id);

call report_experiment_config(@experiment_id );
call report_experiment(@experiment_id); # 214 vpm_count


# training experiment list
select ex.id, (select count(*) from volume_performance_meter vpm where vpm.experiment_id = ex.id) from experiment ex where json_extract(ex.config, '$.is_training') = true order by ex.id desc; 
/*
21	2115
9	2442
8	2214
7	231
1	2657
*/

select get_experiment_workload_config(@experiment_id, 'request_write_iops');
select get_experiment_workload_config(@experiment_id, 'request_read_iops');
select get_experiment_performance_eval_config(@experiment_id, 'perf_restart_gap');
select	get_experiment_workload_config(@experiment_id, "max_number_volumes");

select TIMESTAMPDIFF(MINUTE, cast('2016-12-15 15:59:06.000000' as datetime), now());


select @experiment_id ;
select * from backend where experiment_id =  @experiment_id ;

select @experiment_id;
set @wt = now();
set @tr = unix_timestamp(@wt) - second(@wt) - 180;
select second(@wt), @tr, from_unixtime(@tr), @wt;


select	count(*)
		From	log
        where	experiment_id	= @experiment_id	and
				type			= 'ERROR';


select cast(JSON_EXTRACT(@s, '$.max_number_vols') as UNSIGNED  INTEGER);

select isnumeric('+0.1002');
select	get_experiment_config(@experiment_id, "volume_attach_time_out");
select	set_experiment_config(@experiment_id, "volume_attach_time_out", 65);

select	set_experiment_config(@experiment_id, "max_number_vols", 0);

select	set_experiment_config(@experiment_id, "number_of_servers_to_start_simulation", 40);

select	get_all_requests_count(@experiment_id), get_experiment_config(@experiment_id, 'max_number_vols');
select * from volume_request vr where vr.workload_ID in (select e.workload_id from experiment e where e.id = @experiment_id) order by vr.id desc;

call delete_experiment(@experiment_id, 10);

set @id = 0;
call insert_volume_request(39, 39, 5, 0, 500, 500, 0, now(), @id);
/*
	workload_ID			bigint,
    experiment_id		bigint,
	Capacity			INT(11),
	type				INT(11),
	read_IOPS			INT(11),
    write_IOPS			INT(11),
	create_clock		INT(11),
	create_time			DATETIME(6),
    out id				bigint
*/


/* END TRYING TO FIGURE OUT WHY THERE IS ONLY 1 number difference between rejct_vols_o and rejct_vols*/
call report_experiment(@experiment_id); # 214 vpm_count

Select	Count(*)				As	AllRequests
		From	schedule_response		SR
					Left	Join
				volume					v
					On	v.schedule_response_ID	= SR.id
						
		Where	SR.experiment_id		= @experiment_id	and
				(
					v.is_deleted	< 2		or	# only consider properly attached volumes
					v.is_deleted	is null
				);
# 1502 (all requests) - 38 (scheduled) = 1464 (rejected)
Select	Count(*)				As	rejected_volume_count
		From	schedule_response		SR
					Left	Join
				volume					v
					On	v.schedule_response_ID	= SR.id	
						
		Where	SR.experiment_id		= @experiment_id		and
				SR.response_id		> 1			and
				(
					v.is_deleted		< 2	Or	# only consider properly attached volumes
					v.is_deleted		is null
				);

Select	Count(*)				As	scheduled_volume_count
		From	schedule_response		SR
					Inner	Join
				volume					v
					On	v.schedule_response_ID	= SR.id	
					
		Where	SR.experiment_id		= @experiment_id	and
				SR.response_id			= 1			and
				v.is_deleted			< 2	;	# only consider properly attached volumes
                
Select	count(*) From	volume_request	vr Where	vr.workload_ID	= (Select e.workload_id from experiment e where e.id = @experiment_id);
Select	count(*) from schedule_response where experiment_id = @experiment_id;
Select	count(*) from volume where experiment_id = @experiment_id;
select	count(*) from volume;
Select	count(*) from schedule_response;

/* END TRYING TO FIGURE OUT WHY THERE IS ONLY 1 number difference*/

select * from tenant where experiment_id = @experiment_id;

select * from volume_request order by id desc;
# exp_id, volume_request_id
call get_backends_weights(0, 7645);
# exp_id | 0 means the latest experiment | the input experiment must have training experiment id
call get_training_dataset(0);

Select	Count(*)				As	AllRequests
		From	schedule_response		SR
					Inner	Join
				volume					v
					On	SR.experiment_id		= @experiment_id	and
						v.schedule_response_ID	= SR.id				and
						v.is_deleted			< 2		# only consider properly attached volumes
;

select * 
		from log 
        where experiment_id	= @experiment_id
#and code like '%iops_w%' 
        #where app = 'perf_eval'
#and type = 'ERROR'
		order by id desc
        #desc limit 400
        ;

select * #mod(create_clock, 180)
from volume_performance_meter where experiment_id = @experiment_id order by id desc ;

select * from log order by id desc;

select * from log where volume_cinder_id = '3378f235-a107-4a7e-8a95-b6f93b03e05a' order by id desc;

select set_experiment_config(@experiment_id, 'restart_controller_compute_bad_volume_count_threshold', 200);

select get_experiment_config(@experiment_id, 'number_of_servers_to_start_simulation');
select get_experiment_config(@experiment_id, 'restart_controller_compute_bad_volume_count_threshold');
select get_experiment_config(@experiment_id, 'read_is_priority');
select get_experiment_config(@experiment_id, 'training_experiment_id');
select get_experiment_config(@experiment_id, 'volume_attach_time_out');
select get_experiment_config(@experiment_id, 'min_required_vpm_records');
select get_experiment_config(@experiment_id, 'wait_volume_status_timeout');
          
select get_current_experiment_id(0);

select get_training_experiment_id(0);
select * from volume v where v.experiment_id = @experiment_id and is_deleted=2;

delete from workload_generator where id > 0;
select * from workload_generator wg order by wg.id desc limit 100;

set @prev_ex = @experiment_id - 1;
select @training_id := get_experiment_config(@experiment_id, 'training_experiment_id');
call report_experiment(@prev_ex);
call report_experiment(@training_id);

select * from volume_performance_meter vpm where vpm.experiment_id = @experiment_id;

select	@experiment_id, @prev_ex, @training_id;

select * from experiment where ID = @experiment_id;

# (experiment_id)


select	get_experiment_config(@experiment_id, 'training_experiment_id') ;

select * from schedule_response where experiment_id = @experiment_id order by id desc;
select * from backend where experiment_id = @experiment_id;
select * from schedule_response where experiment_id = @experiment_id order by id desc;
select @@sql_mode;
set global sql_mode='ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION';

select	* from backend order by id desc;
select	* from tenant where experiment_id = @experiment_id;

select vr.* from volume_request vr inner join experiment e on e.id = @experiment_id and vr.workload_ID = e.workload_ID;

set session sql_mode='STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION';

Select	@config := config	From	experiment	where	id = 54;

select	@mod_clock_by := JSON_EXTRACT(@config, '$.mod_normalized_clock_for_feature_generation');

set @rank = 0;
set @last_backend_id = 0;
set @backend_id = 0;
set @max_backend_number_records = 0

select @read_violation, @experiment_id;

select	@backend_id := ID	from backend where experiment_id = @experiment_id;

explain Select	max(rank)
			From	volume_performance_meter
            Where	experiment_id	= @experiment_id	and
					backend_ID		= @backend_id;
                    
set @max_rank_backend = 
(
	Select	max(rank)
			From	volume_performance_meter
            Where	experiment_id	= @experiment_id	and
					backend_ID		= @backend_id
);

Select	@max_rank_backend;

select	count(*) from volume_performance_meter;

Select	vpm.create_clock											As	create_clock,
		mod(vpm.create_clock, @mod_clock_by)						As	clock,
		vpm.backend_id												As	backend_id,
		count(*)													As	vpm_count,
        sum(if(
			vpm.sla_violation_id = 2 or vpm.sla_violation_id = 4,
            1,
            0))														As	read_violation_count,
		sum(if(
			vpm.sla_violation_id = 3 or vpm.sla_violation_id = 4,
            1,
            0))														As	write_violation_count,
		sum(vpm.write_iops)											As	available_write_iops_total,
        sum(vpm.read_iops)											As	available_read_iops_total,
        sum(vreq.write_iops)										as	requested_write_ios_total,
        sum(vreq.read_iops)											as	requested_read_ios_total
		
	From	volume_performance_meter		vpm
				Inner	Join
			volume							v
				On	vpm.backend_ID	= @backend_id				and
					vpm.rank		> @max_rank_backend - 5		and
					vpm.volume_ID	= v.ID
                Inner	Join
			schedule_response				sr
				on	v.schedule_response_id	= sr.id
                Inner	Join
			volume_request					vreq
				on	sr.volume_request_id	= vreq.id
            
	Group	By	vpm.create_clock
;
/*
1479437520
1479437550
1479437580
1479437640
1479438150
*/
Select vpm.create_clock From volume_performance_meter vpm 
Where vpm.experiment_id = @experiment_id and vpm.backend_id = @backend_id and vpm.rank > @max_rank_backend - 5
Group By vpm.create_clock;

call get_error_log_count(0);

select	get_current_experiment_id(0);

explain Select	*	From	volume_performance_meter		vpm	Where	vpm.experiment_id	= @experiment_id	and vpm.backend_id		= 78 and id between 30788 and 30798 order by id desc limit 1;

explain Select	*	From	volume_performance_meter		vpm	Where	vpm.experiment_id	= @experiment_id	and vpm.backend_id		= 78;
delete	from	volume_performance_meter	Where	experiment_id	= 54	and id >0;

explain Select	*	From	volume_performance_meter		vpm	order by id desc limit 10;

Select	*	From	volume_performance_meter		vpm	order by id desc limit 0, 10;


select	count(*)	from	volume_performance_meter where	backend_id = 78;

SELECT @@sql_mode;  
#ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION
set sql_mode = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION';
set sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION';


 #3 of SELECT list is not in GROUP BY clause and contains nonaggregated column 
 #'MLScheduler.vpm.sla_violation_id' which is not functionally dependent on columns in GROUP BY clause; 
 #this is incompatible with sql_mode=only_full_group_by	0.000 sec
 
 Update	volume_performance_meter
		set		sla_violation_id	= 2
		Where	experiment_id	= @experiment_id	and
				id				> 0
;
select get_all_requests_count(@experiment_id) > get_experiment_config(@experiment_id, 'max_number_vols') = 1;

Select	@experiment_id,
		json_extract(config,'$.assess_read_eff_fir') as	assess_read_eff_fir,
        json_extract(config, '$.assess_read_eff_fir_bn') as assess_read_eff_fir_bn
		From	experiment	
		where	id = @experiment_id;

select @s;

select set_experiment_config(@experiment_id, 'assess_read_eff_fir', '1');

call insert_experiment (
	1,
    '',
    '',
    @s,
    '',
    1,
    now(),
    @id);
    
select @id;

call	report_experiment_config(@id);