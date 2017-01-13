use MLScheduler;
set @experiment_id = 42;
select * from experiment order by id desc;

set @experiment_id 	=	(
							select id from experiment order by id desc	limit 1
						);
select @experiment_id;
select t.id from tenant t where t.experiment_id = @experiment_id;

call ML_data(@experiment_id)

delete	From	workload_generator 	where	id >0 and tenant_id in (select t.id from tenant t where t.experiment_id = @experiment_id);

delete	From	workload_generator	where id > 0;

select * from workload_generator;

SELECT	wl.id,
        t.description					as	tenant,
        wl.read_iops,
        wl.write_iops,
        wl.duration,
        wl.output,
        wl.create_time,
        second(wl.create_time) % 15,
        wl.command
        
		FROM	workload_generator			wl
					Inner	Join
				tenant						t
					On	t.experiment_id	= @experiment_id	And
						wl.tenant_id	= t.id
		#Where	t.description	= 'vm-5@10.18.75.185
		#Where	vpm.terminate_wait	> 0
        order	by	wl.id	desc
        #limit 100
        ;
        
commit;
commit;