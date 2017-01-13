use MLScheduler;
set @id  = 1; 

call insert_log(0, 'app', 'type', 'code', 'filename', 'function_name', 'message', 'exception_message', now(), @id);

select * from log;
delete from log where id > 0;

/*
1: no violated
2: read_IOPS violated
3: write_IOPS violated
4: both read and write IOPS violated
*/
insert	into	sla_violation_type (id, title) values (3, 'write iops violation');
insert	into	sla_violation_type (id, title) values (4, 'read & write iops violation');
select	*	From	sla_violation_type;

call	get_training_dataset(62, 10);

/*
Accepted = 1,
rejected Capacity = 2,
rejected IOPS = 3,
rejected CapacityAndIOPS = 4
*/
insert	into	schedule_response_type (id, title) values (1, 'Accepted');
insert	into	schedule_response_type (id, title) values (2, 'rejected capacity');
insert	into	schedule_response_type (id, title) values (3, 'rejected read iops');
insert	into	schedule_response_type (id, title) values (4, 'rejected write iops');
insert	into	schedule_response_type (id, title) values (5, 'rejected read & write iops');
insert	into	schedule_response_type (id, title) values (6, 'rejected unknown reason');
insert	into	schedule_response_type (id, title) values (7, 'rejected no weighed host');
select	*	From	schedule_response_type;


update	volume_performance_meter set sla_violation_id = 1 where sla_violation_id = 0 and id > 0;
select * from volume_performance_meter where sla_violation_id >4 ;


call insert_workload('com', 1, now(), @id);
Select * from workload order by id desc;

call insert_tenant (1, 'nova id', now(), @id);
select @id,id,experiment_id,nova_id,create_time from tenant;
select * from tenant where nova_id = '38b4d2ba-7421-4c00-9d0a-ad84137eee26';
select * from tenant order by id desc;



select *  from experiment;
call get_experiment();

CALL insert_workload('comment', 1, now());
SELECT * FROM workload;

CALL insert_experiment(0, 'comment3', 'alg', 'conf', 'com2', 0, now(), @id);
Select * from workload order by id desc;
SELECT * FROM experiment order by id desc;

# (experiment_ID, tenant_id, nova_id, duration, read_iops, write_iops command, output, create_clock, create_time, id)
call insert_workload_generator(1, 0, '38b4d2ba-7421-4c00-9d0a-ad84137eee26', 1.5, 0, 0, 'a', 'b', 0, now(), @id);
select * from workload_generator order by id desc;

CALL insert_backend('block4@lvm', 1, 100, 1, "{u'ip': u'10.18.75.64', u'capacity': 100, u'id': 4, u'host_name': u'block4'}", '', 0, now());
CALL insert_backend('block5@lvm', 1, 100, 1, "{u'ip': u'10.18.75.65', u'capacity': 100, u'id': 7, u'host_name': u'block5'}", '', 0, now());
SELECT * FROM backend;
update backend set id=4 where ID = 6;
update backend set cinder_id = 'block3@lvm', Description="{u'ip': u'10.18.75.63', u'capacity': 100, u'id': 3, u'host_name': u'block3'}" where ID = 5;

CALL insert_volume_request(0, 1, 1, 1, 500, 600, 1, now(), @id);
SELECT * FROM volume_request order by id desc;

CALL insert_schedule_response(1, 1, 1, 1, now());

call delete_volume(0, '218485af-f6d4-44f9-ad6b-1ee98201568f', 0, now());
SELECT * FROM volume order by id desc;

select * from tenant;
select * from backend;
SELECT * FROM volume_request order by id desc;
SELECT * FROM schedule_response order by id desc;
SELECT * FROM volume order by id desc;
SELECT * FROM volume_performance_meter order by id desc limit 100;
select * from workload_generator where id >0 order by id desc;
select * from schedule_response where id >0 order by id desc;

#(experimentid, cinder_id, backend_cinder_id, schedule_response_id, capacity, create_clock, create_time)
CALL insert_volume(1, 'vol11522', '5@lvm', 34, 10, 1, now(),@id);
select * from backend order by id desc;
select @id;


commit;

# (experiment_ID, tenant_id, nova_id , backend_ID, volume_ID, cinder_volume_id, read_IOPS, write_IOPS [....] terminate_wait,,out@id)
CALL insert_volume_performance_meter(11, 0, '38b4d2ba-7421-4c00-9d0a-ad84137eee26', 0, 0, 'b0705326-375d-4839-b467-a0545a312c92', 500, 500, 2, 0,'',0, 1, now(),@id);

select * from tenant order by id desc;
SELECT * FROM volume_performance_meter order by id desc;


