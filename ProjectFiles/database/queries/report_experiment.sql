select @experiment_id := id from experiment order by id desc	limit 1;

;

Select
	(
		Select	Count(*)				AS	ScheduledVolumes
			From	volume			v
			Where	v.experiment_id			= @experiment_id
	) as scheduled_volumes_count,
	(
		Select	Count(*)				As	AllRequests
				From	schedule_response		sr
						Where	sr.experiment_ID	= @experiment_id
	) as all_requests_count,
	(
		Select	Avg(VR.capacity)				As	AllRequests
			From	schedule_response		SR
						Inner	Join
					volume_request			VR
						On	SR.volume_request_ID	= VR.ID
			Where	SR.experiment_id			= @experiment_id
	) as capacity_avg,
	(
		Select	Count(*)				AS	deleted_volume_count
				From	volume		v
				Where	v.experiment_id		= @experiment_id	and
						v.is_deleted		= 1
	) as deleted_volume_count,
	(
		Select	Avg(unix_timestamp(v.delete_time) - unix_timestamp(v.create_time))	as	delete_average_time_seconds
			From	volume				v
			Where	v.is_deleted			= 1				And
					v.experiment_ID			= @experiment_id
	) as delete_average_time_seconds,
	(
		Select	count(*)
			From	volume_performance_meter	VPM
			Where	VPM.experiment_id		= @experiment_id	And
					VPM.sla_violation_id	= 2 /*2	read iops violation*/
	) as sla_violation_count_read_iops,
	(
		Select	count(*)
			From	volume_performance_meter	VPM
			Where	VPM.experiment_id		= @experiment_id	And
					VPM.sla_violation_id	= 3 /*2	write iops violation*/
	) as sla_violation_count_write_iops,
	(
		Select	count(*)
			From	volume_performance_meter	VPM
			Where	VPM.experiment_id		= @experiment_id
	) as volume_performance_meter_count,
	(
		Select	round(max(VPM.create_time) - (select ex.create_time from experiment ex where ex.id = @experiment_id))
			From	volume_performance_meter	VPM
			Where	VPM.experiment_id		= @experiment_id
	) as experiment_duration_seconds_apx,
	(
		Select	Count(*)		As	Backend_Count
				
			From	backend		b
			Where	b.experiment_id	= @experiment_id
	) as backend_count,
	(
		Select	avg(VR.read_iops)		As	read_iops_avg_requested
			From	schedule_response		SR
						inner	join
					volume_request			VR
						On	SR.experiment_id		= @experiment_id	and
							SR.volume_request_id	= VR.id
	) as read_iops_avg_requested,
	(
		Select	avg(VR.write_iops)			As	read_iops_avg_requested
			From	schedule_response		SR
						inner	join
					volume_request			VR
						On	SR.experiment_id		= @experiment_id	and
							SR.volume_request_id	= VR.id
	) as write_iops_avg_requested,
	(
		Select	avg(VPM.read_iops)		As	read_available_iops_average
			From	volume_performance_meter	VPM
			Where	VPM.experiment_id		= @experiment_id
	) as available_read_iops_avg,
	(
		Select	avg(VPM.write_iops)		As	read_available_iops_average
			From	volume_performance_meter	VPM
			Where	VPM.experiment_id		= @experiment_id
	) as available_write_iops_avg