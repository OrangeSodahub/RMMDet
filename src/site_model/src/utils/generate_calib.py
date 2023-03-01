#!/usr/bin/env python3

#############################################################
#   This py file caculate the calibration matrix            #
#   Output txt file to tools/calib/                         #
#   Author: Yangxiuyu                                       #
#############################################################

import math
from termcolor import colored
from pathlib import Path
import argparse
import yaml
import os
import numpy as np

def main(ROOT_DIR: Path, config: dict):
    """
        generate the calib matrix
    """
    # Transform dict
    camera_name = {0: 11, 1: 12, 2: 13, 3: 14, 4: 2,
                5: 3, 6: 41, 7: 42, 8: 43, 9: 44}
    pole_name = {0: "pole1", 1: "pole1", 2: "pole1", 3: "pole1", 4: "pole2",
                5: "pole3", 6: "pole4", 7: "pole4", 8: "pole4", 9: "pole4"
            }

    # Generate 'calib' array
    world_to_camera_, camera_to_pixel_ = world_to_pixel(ROOT_DIR, config, pole_name[0], camera_name[0])
    camera_cur = np.append(world_to_camera_.flatten(),camera_to_pixel_.flatten(),axis=0)
    calib = [np.append([camera_name[0]],camera_cur,axis=0)]
    for i in range(1,10):
        world_to_camera_, camera_to_pixel_ = world_to_pixel(ROOT_DIR, config, pole_name[i], camera_name[i])
        camera_cur = np.append(world_to_camera_.flatten(),camera_to_pixel_.flatten(),axis=0)
        camera_cur = np.append([camera_name[i]],camera_cur,axis=0)
        calib = np.append(calib,[camera_cur],axis=0)

    # Save the file
    calib_dir = ROOT_DIR / config['calib']['calib_dir']
    os.makedirs(calib_dir,exist_ok=True)
    np.savetxt(str(calib_dir / 'calib.txt'), calib)


# transform matrix
def world_to_pixel(ROOT_DIR: str, config: dict, pole_name: str, camera_name: str):
    """
        input: world_pose
        output: pixel_pose
        process: world_pose->pole_pose->camera_pose->pixel_pose
        tips: camera_pose->pixel_pose
              need to shift the camera_coordinates
    """
    world_to_camera_ = world_to_camera(config, pole_name, camera_name)
    camera_to_pixel_ = camera_to_pixel(ROOT_DIR, config, camera_name)

    # caculate the transfrom matrix
    world_to_pixel_ = np.matmul(camera_to_pixel_, world_to_camera_)

    return world_to_camera_, camera_to_pixel_


# camera external parameter matrix
def world_to_camera(config: dict, pole_name: str, camera_name: str):
    """
        world_to_camera = pose_to_camera * world_to_camera
    """
    pole = config['calib']['pole_pose'][pole_name]
    camera = config['calib']['camera_pose'][camera_name]

    world_to_pole = RTmatrix(pole)
    pole_to_camera = RTmatrix(camera)
    world_to_camera_ = np.matmul(pole_to_camera,world_to_pole) # Wrong: world_to_Pole * pole_to_camera

    return world_to_camera_


def camera_to_pixel(ROOT_DIR: str, config: dict, camera_name: int):
    """
        get the internal parameter matrix of camera (fixed)
    """
    transform = {11: 0, 12: 1, 13: 2, 14: 3, 2: 4,
                3: 5, 41: 6, 42: 7, 43: 8, 44: 9}
    camera_info_dir = ROOT_DIR / config['calib']['camera_info_dir']
    K = np.loadtxt(str(camera_info_dir / 'camera_info.txt'))[transform[camera_name]][28:40] # fuck! [4] is a bug!
    K = K.reshape(3,4)

    return K


def RTmatrix(pose):
    """
        caculate the external parameter matrix of camera:
        R = Rz * Ry * Rx
        tips: need to inverse the matrix R
    """
    # Translation matrix
    T = [[pose[0]],[pose[1]],[pose[2]]]

    # Roatation matrix
    r_angle = pose[3]
    p_angle = pose[4]
    y_angle = pose[5]
    
    Rx = [[1                 ,0                ,0],
            [0,math.cos(r_angle),-math.sin(r_angle)],
            [0,math.sin(r_angle),math.cos(r_angle)]]
    Ry = [[math.cos(p_angle),0,math.sin(p_angle)],
            [0,               1,               0],
            [-math.sin(p_angle),0,math.cos(p_angle)]]
    Rz = [[math.cos(y_angle),-math.sin(y_angle),0],
            [math.sin(y_angle),math.cos(y_angle),0],
            [0                ,0                ,1]]

    R = np.matmul(Rz,np.matmul(Ry,Rx)) # Wrong:R=RxRyRz

    # RTmatrix 
    O1 = np.transpose([[0],[0],[0],[1]])
    RT = np.append(R,T,axis=1)
    result = np.append(RT,O1,axis=0)

    # Inverse the matrix
    result = np.linalg.inv(result)

    return result


if __name__=='__main__':
    # get ROOT DIR
    ROOT_DIR = Path(__file__).resolve().parents[2]

    parser = argparse.ArgumentParser()
    parser.add_argument("--config",
                        help="path to config file",
                        metavar="FILE",
                        required=False,
                        default= str(ROOT_DIR.joinpath('config/config.yaml'))
                        )
    args = parser.parse_args()

    params = parser.parse_args()

    with open(params.config, 'r') as f:
        try:
            config = yaml.load(f,Loader=yaml.FullLoader)

        except:
            print(colored('Config file could not be read','red'))
            exit(1)
        
        main(ROOT_DIR, config)
        print(colored('Calib parameter generated.', 'green'))