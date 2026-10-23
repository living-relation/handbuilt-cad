grep CODENAME /etc/os-release
echo "--- openfoam.org dists:"; curl -s https://dl.openfoam.org/ubuntu/dists/ | grep -oE 'href="[a-z]+/' | sort -u | tr '\n' ' '; echo
echo "--- openfoam.com packagecloud:"; curl -s -o /dev/null -w '%{http_code}\n' https://packagecloud.io/OpenCFD/openfoam/ubuntu/dists/resolute/Release
curl -s -o /dev/null -w 'noble %{http_code}\n' https://packagecloud.io/OpenCFD/openfoam/ubuntu/dists/noble/Release
echo "--- elmer ppa dists:"; curl -s https://ppa.launchpadcontent.net/elmer-csc-ubuntu/elmer-csc-ppa/ubuntu/dists/ | grep -oE 'href="[a-z]+/' | sort -u | tr '\n' ' '; echo
apt-cache search --names-only 'openfoam|elmer' | head