from build123d import *
import math
def csk_screw(x,y,ztop,d,L,head_d,down=True):
    hh=(head_d-d)/2  # 90 deg
    head=Solid.make_cone(head_d/2,d/2,hh,Plane((x,y,ztop),z_dir=(0,0,-1)))
    sh=Solid.make_cylinder(d/2,L-hh,Plane((x,y,ztop-hh),z_dir=(0,0,-1)))
    return head.fuse(sh)
def pan_screw(x,y,zbear,d,L,head_d,head_h):
    head=Solid.make_cylinder(head_d/2,head_h,Plane((x,y,zbear),z_dir=(0,0,1)))
    sh=Solid.make_cylinder(d/2,L,Plane((x,y,zbear),z_dir=(0,0,-1)))
    return head.fuse(sh)
