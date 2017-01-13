Select * from
(

select v.experiment_id,
		count(*)			as c
        
	from 	experiment ex
				inner	join
			volume		v
				on	v.experiment_id	= ex.id
                
	where	get_experiment_config(ex.id, 'training_experiment_id') = 1
    
    group by v.experiment_id
    
	order by v.experiment_id desc
) a
order by a.c	desc
;