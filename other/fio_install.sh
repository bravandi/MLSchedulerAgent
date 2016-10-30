cd /root
yum install -y make gcc libaio-devel || ( apt-get update && apt-get install -y make gcc libaio-dev  </dev/null )
wget https://github.com/Crowd9/Benchmark/raw/master/fio-2.0.9.tar.gz ; tar xf fio*
cd fio*
make