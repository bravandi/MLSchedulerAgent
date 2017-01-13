set @t = now();

#test = datetime.strptime("2016-11-14 12:36:01.0", "%Y-%m-%d %H:%M:%S.%f")
#1479144960



select @t;
set @z = 0;

set @t = STR_TO_DATE('2016-11-14 12:37:30', '%Y-%m-%d %H:%i:%s');
select	UNIX_TIMESTAMP(@t) = 1479144960,
		@z := UNIX_TIMESTAMP(@t),
        @t_s := second(@t),
		@c := if(@t_s > 30, @z + 30 - @t_s, @z - @t_s),
        from_unixtime(@c),
        if(second(@t) > 30, UNIX_TIMESTAMP(@t) + 30 - second(@t), UNIX_TIMESTAMP(@t) - second(@t))
        From	experiment
        limit 1
        ;

set @t = STR_TO_DATE('2016-11-14 12:37:31', '%Y-%m-%d %H:%i:%s');
select	if(second(UNIX_TIMESTAMP(@t)) > 30, UNIX_TIMESTAMP(@t) + 30 - second(@t), UNIX_TIMESTAMP(@t) - second(@t))
        From	experiment
        limit 1
        ;

select TIME_TO_SEC('00:01:01'), second('00:01:16') % 15;


SELECT
  DATE_FORMAT(NOW(), '%d %m %Y') AS your_date
  ;