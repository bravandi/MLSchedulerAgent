#powershell.exe -file "D:\GoogleDrive\Research\MLScheduler\database\backup.ps1


$date = Get-Date -format 'yyyy-mm-dd_mm_ss'
$path = "D:\GoogleDrive\Research\MLScheduler\database\backup\" + $date

$command = "D:\GoogleDrive\Research\MLScheduler\database\mysqldump.exe -h 10.18.75.100 -u babak -p123 --routines MLScheduler > "

$command_with_date = $command + $path  + ".sql"

CMD /C $command_with_date

$command_no_data = $command + $path  + "_scheme.sql" + " -d"

CMD /C $command_no_data