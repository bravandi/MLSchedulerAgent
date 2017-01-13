Use	MLScheduler;

select	get_experiment_config(@experiment_id, 'mod_normalized_clock_for_feature_generation') ;

set	@s = '';
Select	@s := config	From	experiment	where	id = 54;
select @s;

select	JSON_EXTRACT(@s, '$.mod_normalized_clock_for_feature_generation');

SELECT mod(182, JSON_EXTRACT(@s, '$.mod_normalized_clock_for_feature_generation'));

set @s = REPLACE(@s, '\n', '');
set @s = REPLACE(@s, '"%"', '');

set @s = '{"clock_calc": "def clock_calc(t):    if(t.second > 30):        t = t.replace(second=30)    else:        t = t.replace(second=0)    t = t.replace(microsecond=0)    return t.strftime("s")", "performance_args": {"--restart_gap_after_terminate": 50, "--terminate_if_takes": 150, "--show_fio_output": false, "--fio_test_name": "resource_evaluation.fio", "--restart_gap": 20}, "workload_args": {"--max_number_volumes": 1, "--delay_between_workload_generation": 4, "--volume_life_seconds": 500, "--fio_test_name": "workload_generator.fio", "--volume_size": 5}}';
set @s = '{"clock_calc": "\ndef clock_calc(t):\n    if(t.second > 30):\n        t = t.replace(second=30)\n    else:\n        t = t.replace(second=0)\n    t = t.replace(microsecond=0)\n    return t.strftime(\"%s\")\n", "performance_args": {"--restart_gap_after_terminate": 50, "--terminate_if_takes": 150, "--show_fio_output": false, "--fio_test_name": "resource_evaluation.fio", "--restart_gap": 20}, "workload_args": {"--max_number_volumes": 1, "--delay_between_workload_generation": 4, "--volume_life_seconds": 500, "--fio_test_name": "workload_generator.fio", "--volume_size": 5}}';
#SELECT JSON_EXTRACT('{"id": 14, "name": "Aztalan"}', '$.name');