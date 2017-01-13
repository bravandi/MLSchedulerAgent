use MLScheduler;
select *	from experiment order by id desc;
select * 	from workload order by id desc;
select * 	from backend order by id desc;
SELECT * 	FROM volume_request order by id desc;
select * 	from tenant order by id desc;
SELECT * 	FROM workload_generator order by id desc;
Select * 	FROM volume_performance_meter	order by id desc;


#set @experiment_id = 42;
select * from experiment order by id desc;

set @experiment_id 	=	(
							select id from experiment order by id desc	limit 1
						);
select @experiment_id;

select * from tenant;
select * from backend;

update tenant set description='' where id>0;

SELECT * FROM schedule_response where experiment_id = @experiment_id order by id desc;
SELECT * FROM volume	where	id =184 order by id desc;
/*delete from volume_performance_meter where id > 0;*/
select * from tenant;

Select count(*) FROM	volume_performance_meter	order by id desc;
Select * FROM	volume_performance_meter
	where	sla_violation_id	<> 3
	order by id desc
;

/*Call	update_clock(@experiment_id, 15);*/

/* all performance_eval records for an experiment*/
SELECT	
		/*
		avg(vpm.read_iops),
        stddev(vpm.read_iops),
        avg(vpm.write_iops),
        stddev(vpm.write_iops)
        */
        
        vpm.id,
        b.cinder_id,
        t.description					as	tenant,
        vpm.volume_id,
        vpm.read_iops,
        vpm.write_iops,
        vpm.duration,
        vpm.sla_violation_id,
        vpm.terminate_wait,
        vpm.create_time,
		vpm.create_clock,
        vpm.io_test_output
        
		FROM	volume_performance_meter	vpm
					Inner	Join
				backend						b
					on	vpm.experiment_id		= @experiment_id	and
						vpm.backend_id			= b.id
					Inner	Join
				tenant						t
					on	vpm.tenant_id			= t.id
		Where	cinder_id	= 'block5@lvm'
        #Where	vpm.terminate_wait	> 0
        order	by	vpm.id	desc
        #limit 100
        ;


/* Number of deleted and active volumes for each backend  */
Select	b.cinder_id,
		sum(if(v.is_deleted = 1, 1, 0))			count_deleted_volumens,
        sum(if(v.is_deleted = 0, 1, 0))			count_live_volumes,
        count(*)								count_all

	From	schedule_response		sr
				Left	Join
			volume					v
				on	v.schedule_response_id	= sr.id
                Left	Join
			backend					b
				On	v.backend_ID	= b.id
                
	Where	sr.experiment_id		= @experiment_id
    group	by	b.cinder_id
                
	;

/* Total number of volumes for each abckend */
SELECT	b.cinder_id,
		count(*)				As	Total_number_of_volumes
        
		FROM	volume_performance_meter	vpm
					Inner	Join
				backend						b
					on	vpm.experiment_id		= @experiment_id	and
						vpm.backend_id			= b.id
					Inner	Join
				tenant						t
					on	vpm.tenant_id			= t.id
		Group	By	b.cinder_id;

/* clock distribution for each backend */
Select	r.cinder_id,
		r.clock,
        count(*)
	From	(
SELECT	       
        vpm.id,
        t.description					as	tenant,
        b.cinder_id,
        vpm.volume_id,
        vpm.read_iops,
        vpm.write_iops,
        vpm.duration,
        vpm.sla_violation_id,
        vpm.terminate_wait,
        vpm.create_time,
		second(vpm.create_time) % 15	as	clock,
        vpm.io_test_output
        
        
		FROM	volume_performance_meter	vpm
					Inner	Join
				backend						b
					on	vpm.experiment_id		= @experiment_id	and
						vpm.backend_id			= b.id
					Inner	Join
				tenant						t
					on	vpm.tenant_id			= t.id
        #limit 100
			)	as	r
		group	by	r.cinder_id,
					r.clock
                    
		order	by	r.cinder_id	asc
        ;

/* average read/wrote iops oon each backend for an experiment*/
SELECT	b.cinder_id,
        avg(vpm.read_iops),
        std(vpm.read_iops),
        avg(vpm.write_iops),
        std(vpm.write_iops),
        avg(vpm.write_iops),
        std(vpm.write_iops)
        
		FROM	volume_performance_meter	vpm
					Inner	Join
				backend						b
					on	vpm.experiment_id		= @experiment_id	and
						vpm.backend_id			= b.id
		group	by	b.cinder_id
					
		#Where	vpm.terminate_wait	> 0
        #order	by	vpm.id	desc
        #limit 100
        ;