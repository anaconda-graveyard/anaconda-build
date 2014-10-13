yum install gettext-devel expat-devel curl-devel zlib-devel openssl-devel
cd /tmp
wget https://www.kernel.org/pub/software/scm/git/git-2.1.0.tar.gz
tar xzvf git-2.1.0.tar.gz
cd git-2.1.0
make prefix=/opt/git all
make prefix=/opt/git install
export PATH=”/opt/git/bin:$PATH”
