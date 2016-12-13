#!/usr/bin/env bash
RED='\033[0;31m'
NC='\033[0m' # No Color

function c_killProc(){

#              dont know if ` is the right character for shell
#	for KILLPID in `ps aux | grep '$1' | awk ' { print $2;}'`;
#	do
#		print $KILLPID;
#		echo $KILLPID
#	donea

	sudo ps -ef | grep $1 | grep -v grep | awk '{print $2}' | xargs sudo kill -9
}

function c_catErr(){
	sudo find /home/centos -type f -name '*.err' -exec cat {} +
}

function c_catOut(){
	sudo find /home/centos -type f -name '*.out' -exec cat {} +
}

function c_chmod(){
    sudo chmod -R 777 ~/MLSchedulerAgent
}

function c_delErrOutFiles(){
	 sudo rm /home/centos/*.err
	 sudo rm /home/centos/*.out
}

function c_delMedia(){
	 sudo rm -r -d /media/*
}

function c_killPerformanceEvaluation(){
	sudo ps -ef | grep performance_evaluation | grep -v grep | awk '{print $2}' | xargs sudo kill -9
}

function c_killWorkloadGenerator(){
	sudo ps -ef | grep workload_generator | grep -v grep | awk '{print $2}' | xargs sudo kill -9
	sudo ps -ef | grep workload_runner | grep -v grep | awk '{print $2}' | xargs sudo kill -9
}

function c_showPerfWork(){
    sudo echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    sudo ps aux | grep workload_generator.py
    sudo echo "@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@"
    sudo ps aux | grep performance_evaluation.py
    sudo echo "@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@"
    sudo ps aux | grep workload_runner.py
}

function cp_run(){
	cp_print "$2 running" "$1";

	if [ $# -eq 1 ]
	#if [ $2 = "nohup" ]
	then
	    #cp_print "$2 THEN" "$1";
		# run in background by default
		sudo nohup $1  </dev/null &>/dev/null &
	else
	    #cp_print "$2 ELSE" "$1";
		eval "$1"
	fi
}

function c_getProc(){
	sudo ps aux | grep $1
}

function c_getWorkloadGenerator(){
	sudo ps aux | grep workload_generator
}

function c_getPerformanceEvaluation(){
	sudo ps aux | grep performance_evaluation
}

function c_source(){
# todo fix this
	source ~/MLSchedulerAgent/other/custom_commands.sh
}

#function c_runPerformanceEvaluation(){
#    cv_cmd="sudo python ~/MLSchedulerAgent/performance_evaluation.py"
#
#	cp_run "$cv_cmd" $1
#}

function cp_print(){
    printf "	$1 ${RED} $2 ${NC}\n"
}

function c_cdr_SL(){
	printf "	running ${RED}service-list${NC}\n"

	cinder service-list
}

function c_attachedVolumes(){
	sudo fdisk -l | grep vd
	sudo echo "@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@"
	sudo df | grep vd
}

function c_dockerHellowWorld(){
    sudo docker run --rm hello-world
}

function c_detDelVols(){
    sudo python /home/centos/MLSchedulerAgent/workload_generator.py det-del
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

#sudo systemctl start docker

sudo timedatectl set-timezone America/New_York
#cd /root/cinder/
htop