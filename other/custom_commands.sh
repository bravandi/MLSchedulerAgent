#!/usr/bin/env bash
RED='\033[0;31m'
NC='\033[0m' # No Color

function c_killProc(){

#              dont know if ` is the right character for shell
#	for KILLPID in `ps aux | grep '$1' | awk ' { print $2;}'`;
#	do
#		print $KILLPID;
#		echo $KILLPID
#	done

	ps -ef | grep $1 | grep -v grep | awk '{print $2}' | xargs kill -9
}

function c_killWorkloadGenerator(){
	ps -ef | grep workload_generator | grep -v grep | awk '{print $2}' | xargs kill -9
}

function cp_run(){
	cp_print "$2 running" "$1";

	if [ $# -eq 1 ]
	#if [ $2 = "nohup" ]
	then
	    #cp_print "$2 THEN" "$1";
		# run in background by default
		nohup $1  </dev/null &>/dev/null &
	else
	    #cp_print "$2 ELSE" "$1";
		eval "$1"
	fi
}

function c_getProc(){
	ps aux | grep $1
}

function c_getWorkloadGenerator(){
	ps aux | grep workload_generator
}

function c_source(){
# todo fix this
	source /root/commands.sh
}

function c_runWorkloadGenerator(){
#/usr/bin/python
    cv_cmd="/root/cinder/tools/with_venv.sh /root/cinder/.venv/bin/cinder-api --config-file=/root/cinder/.venv/etc/cinder/cinder.conf --log-file=/root/cinder/.venv/var/log/cinder/cinder-api.log"

    cv_cmd="python /root/MLSchedulerAgent/workload_generator.py"

	cp_run "$cv_cmd" $1
}

function cp_print(){
    	printf "	$1 ${RED} $2 ${NC}\n"
}

function c_cdr_SL(){
	printf "	running ${RED}service-list${NC}\n"

	cinder service-list
}

function c_debugClient(){

    # this is not working it can not find pudb.run maybe because its not registered with venv ?
    # cv_cmd="/root/cinder/tools/with_venv.sh python -m pudb.run /root/python-cinderclient/cinder.py iops-available"

    # python /root/python-cinderclient/cinder.py iops-available

    cv_cmd="python -m pudb.run /root/python-cinderclient/cinder.py iops-available"

    vars=""

    for var in "$@"
    do
        vars="$vars$var "
    done

    printf "$cv_cmd $vars\n"

    eval "$cv_cmd $vars"

	#cp_run "$cv_cmd" $1

}
#cd /root/cinder/