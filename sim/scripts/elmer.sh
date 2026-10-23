#!/bin/bash
set -x
export DEBIAN_FRONTEND=noninteractive
sleep 20
while fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 || pgrep -x apt-get >/dev/null || pgrep -f of.sh >/dev/null; do sleep 5; done
apt-get install -y --no-install-recommends cmake gfortran g++ make libblas-dev liblapack-dev git ca-certificates curl || exit 1
mkdir -p /opt/src && cd /opt/src
[ -f elmer.tgz ] || curl -fsSL -o elmer.tgz https://github.com/ElmerCSC/elmerfem/archive/refs/tags/release-26.2.1.tar.gz
rm -rf elmerfem-release-26.2.1 build && tar xzf elmer.tgz && mkdir build && cd build
cmake ../elmerfem-release-26.2.1 -DCMAKE_INSTALL_PREFIX=/opt/elmer -DWITH_MPI=FALSE -DWITH_ELMERGUI=FALSE -DWITH_OpenMP=TRUE -DCMAKE_BUILD_TYPE=Release && \
make -j$(nproc) && make install
echo EXIT=$?
ln -sf /opt/elmer/bin/ElmerSolver /usr/local/bin/ElmerSolver; ln -sf /opt/elmer/bin/ElmerGrid /usr/local/bin/ElmerGrid