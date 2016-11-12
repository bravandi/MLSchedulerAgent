#cd ~
sudo yum install -y make gcc libaio-devel || ( apt-get update && apt-get install -y make gcc libaio-dev  </dev/null )
sudo wget https://github.com/Crowd9/Benchmark/raw/master/fio-2.0.9.tar.gz
sudo tar xf ~/fio-2.0.9.tar.gz
#cd fio*
sudo make -C fio-2.0.9