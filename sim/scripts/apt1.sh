#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
apt-get install -y --no-install-recommends calculix-ccx gmsh python3-gmsh paraview python3-paraview python3-venv python3-pip xvfb
echo EXIT=$?