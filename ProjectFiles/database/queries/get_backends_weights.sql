select @experiment_id := id from experiment order by id desc	limit 1;

Select	b.id								as	backend_id,
		b.cinder_id							as	cinder_id,
		count(*)							as	live_volume_count_during_clock,
		/* it can be null if backend has no volume */
		ifnull(sum(vreq.write_iops), 0)		as	requested_write_iops_total,
		ifnull(sum(vreq.read_iops), 0)		as	requested_read_iops_total
        
		From	backend				b
					left	join
				volume				v
					on	b.id					= 30		and
						v.backend_ID			= b.id
					inner	join
				schedule_response	sr
					on	v.schedule_response_id	= sr.id
                    inner	join
				volume_request		vreq
					on	sr.volume_request_id	= vreq.id
;
				

Select	bkd_id								as	backend_id,
		cinder_id							as	cinder_id,
		count(*)							as	live_volume_count_during_clock,
		/* it can be null if backend has no volume */
		ifnull(sum(vreq.write_iops), 0)		as	requested_write_iops_total,
		ifnull(sum(vreq.read_iops), 0)		as	requested_read_iops_total
		
	From	volume							v
				Inner	Join
			schedule_response				sr
				on	v.schedule_response_id	= sr.id			and
					v.backend_ID	= bkd_id				and
					v.is_deleted	= 0
					/*
					(
								v.delete_clock	is null		or
								(vpm.create_clock >= UNIX_TIMESTAMP(v.create_time) and vpm.create_clock < UNIX_TIMESTAMP(v.delete_time))
					)
					*/
				Inner	Join
			volume_request					vreq
				on	sr.volume_request_id	= vreq.id
	;