import argparse
import glob
import time
from pathlib import Path

# No visualization
# try:
#     import open3d
#     from visual_utils import open3d_vis_utils as V
#     OPEN3D_FLAG = True
# except:
    # import mayavi.mlab as mlab
    # from visual_utils import visualize_utils as V
    # OPEN3D_FLAG = False

import numpy as np
import torch

from pcdet.config import cfg, cfg_from_yaml_file
from pcdet.datasets import DatasetTemplate
from pcdet.models import build_network, load_data_to_gpu
from pcdet.utils import common_utils


class Dataset(DatasetTemplate):
    def __init__(self, dataset_cfg, class_names, training=True, root_path=None, logger=None, ext='.bin'):
        """
        Args:
            root_path:
            dataset_cfg:
            class_names:
            training:
            logger:
        """
        super().__init__(
            dataset_cfg=dataset_cfg, class_names=class_names, training=training, root_path=root_path, logger=logger
        )
        self.root_path = root_path
        self.ext = ext
        data_file_list = glob.glob(str(root_path / f'*{self.ext}')) if self.root_path.is_dir() else [self.root_path]

        data_file_list.sort()
        self.sample_file_list = data_file_list

    def __len__(self):
        return len(self.sample_file_list)

    def __getitem__(self, index):
        if self.ext == '.bin':
            points = np.fromfile(self.sample_file_list[index], dtype=np.float32).reshape(-1, 4)
        elif self.ext == '.npy':
            points = np.load(self.sample_file_list[index])
        else:
            raise NotImplementedError

        # Form the input_dict
        input_dict = {
            'points': points,
            'frame_id': index,
        }

        data_dict = self.prepare_data(data_dict=input_dict)

        return data_dict
    

def parse_config():
    parser = argparse.ArgumentParser(description='arg parser')
    parser.add_argument('--cfg_file', type=str, default='cfgs/kitti_models/second.yaml',
                        help='specify the config for demo')
    parser.add_argument('--data_path', type=str, default='demo_data',
                        help='specify the point cloud data file or directory')
    parser.add_argument('--ckpt', type=str, default=None, help='specify the pretrained model')
    parser.add_argument('--ext', type=str, default='.bin', help='specify the extension of your point cloud data file')

    args = parser.parse_args()

    cfg_from_yaml_file(args.cfg_file, cfg, RT_detect=False)

    return args, cfg


# python pred.py --ckpt --data
def main():
    args, cfg = parse_config()
    logger = common_utils.create_logger()
    logger.info('----------------- Start Predict -------------------------')
    dataset = Dataset(
        dataset_cfg=cfg.DATA_CONFIG, class_names=cfg.CLASS_NAMES, training=False,
        root_path=Path(args.data_path), ext=args.ext, logger=logger
    )
    logger.info(f'Total number of samples: \t{len(dataset)}')

    model = build_network(model_cfg=cfg.MODEL, num_class=len(cfg.CLASS_NAMES), dataset=dataset)
    model.load_params_from_file(filename=args.ckpt, logger=logger, to_cpu=True)
    model.cuda()
    model.eval()

    # transform dict
    num2class = {
        1: 'Car',
        2: 'Pedstrain',
        3: 'Bicycle'
    }
    with torch.no_grad():
        for idx, data_dict in enumerate(dataset):
            logger.info(f'Visualized sample index: \t{idx + 1}')
            data_dict = dataset.collate_batch([data_dict])
            load_data_to_gpu(data_dict)
            pred_dicts, _ = model.forward(data_dict)

            # Print the resualt to screen
            print("+-------------------------------------------------------------------------------------------------+")
            print("num: ", len(pred_dicts[0]['pred_boxes']), "  class: ", num2class[int(pred_dicts[0]['pred_labels'][0].cpu().numpy())])
            idx = 1
            for pred_boxes in pred_dicts[0]['pred_boxes']:
                print('\n', idx, " ==> ", "loc: ", pred_boxes[0:3].cpu().numpy(), 
                                " size: ", pred_boxes[3:6].cpu().numpy(), '\n'
                                "        rotation: ", pred_boxes[6].cpu().numpy(),
                                "        score: ", pred_dicts[0]['pred_scores'][idx-1].cpu().numpy())
                idx += 1
            print("+-------------------------------------------------------------------------------------------------+\n")

            # Remove visualiazaiton step

            # V.draw_scenes(
            #     points=data_dict['points'][:, 1:], ref_boxes=pred_dicts[0]['pred_boxes'],
            #     ref_scores=pred_dicts[0]['pred_scores'], ref_labels=pred_dicts[0]['pred_labels']
            # )

            # if not OPEN3D_FLAG:
            #     mlab.show(stop=True)

    logger.info('Demo done.')
    

# pointcloud detector
class RT_Pred():
    # Pre-load network
    def __init__(self, ROOT_DIR, config):
        # basic info
        ROOT_DIR = str(ROOT_DIR)
        self.cfg_file = ROOT_DIR + config['lidar_detection']['cfg_file']
        self.ckpt_file = ROOT_DIR + config['lidar_detection']['ckpt_file']

        # create cfg
        self.cfg = self.create_cfg()

        # create logger
        logger = common_utils.create_logger()

        # build_network
        self.model = build_network(model_cfg=self.cfg.MODEL, num_class=len(self.cfg.CLASS_NAMES), dataset=None)
        self.model.load_params_from_file(filename=self.ckpt_file, logger=logger, to_cpu=True)
        self.model.cuda()
        self.model.eval()

        # create dataset
        self.dataset = DatasetTemplate(
            dataset_cfg=self.cfg.DATA_CONFIG, class_names=self.cfg.CLASS_NAMES, training=False,
            root_path=None, logger=None
        )

        # transform dict
        self.num2class = {
            1: 'Car',
            2: 'Pedstrain',
            3: 'Bicycle'
        }

    # create cfg
    def create_cfg(self):
        cfg_from_yaml_file(self.cfg_file, cfg, RT_detect=True)
        return cfg

    
    # Input data and return pred results
    def get_pred_dicts(self, points, print2screen):
        """
           points: array(:,4) -> x,y,z,I 
        """

        input_dict = {
            'points': points,
            'frame_id': 1,
        }
        data_dict = self.dataset.prepare_data(data_dict=input_dict)

        with torch.no_grad():
            data_dict = self.dataset.collate_batch([data_dict])
            load_data_to_gpu(data_dict)
            pred_dicts, _ = self.model.forward(data_dict)

            if print2screen:
                # Print the resualt to screen
                print("+-------------------------------------------------------------------------------------------------+")
                print("num: ", len(pred_dicts[0]['pred_boxes']), "  class: ", self.num2class[int(pred_dicts[0]['pred_labels'][0].cpu().numpy())])
                idx = 1
                for pred_boxes in pred_dicts[0]['pred_boxes']:
                    print('\n', idx, " ==> ", "loc: ", pred_boxes[0:3].cpu().numpy(), 
                                    " size: ", pred_boxes[3:6].cpu().numpy(), '\n'
                                    "        rotation: ", pred_boxes[6].cpu().numpy(),
                                    "        score: ", pred_dicts[0]['pred_scores'][idx-1].cpu().numpy())
                    idx += 1
                print("+-------------------------------------------------------------------------------------------------+\n")

        # store the results
        pred_boxes = pred_dicts[0]['pred_boxes'].cpu().numpy()
        pred_labels = pred_dicts[0]['pred_labels'].cpu().numpy()
        pred_scores = pred_dicts[0]['pred_scores'].cpu().numpy()

        return pred_boxes, pred_labels, pred_scores


def main_2():
    args, cfg = parse_config()
    logger = common_utils.create_logger()

    model = build_network(model_cfg=cfg.MODEL, num_class=len(cfg.CLASS_NAMES), dataset=None)
    model.load_params_from_file(filename=args.ckpt, logger=logger, to_cpu=True)
    model.cuda()
    model.eval()

    points_file = '../data/custom/for_test/point_cloud_data_1.bin'
    points = np.fromfile(points_file, dtype=np.float32).reshape(-1, 4)
    input_dict = {
            'points': points,
            'frame_id': 1,
        }
    dataset = DatasetTemplate(
        dataset_cfg=cfg.DATA_CONFIG, class_names=cfg.CLASS_NAMES, training=False,
        root_path=None, logger=None
    )
    data_dict = dataset.prepare_data(data_dict=input_dict)

    # transform dict
    num2class = {
        1: 'Car',
        2: 'Pedstrain',
        3: 'Bicycle'
    }

    with torch.no_grad():
        data_dict = dataset.collate_batch([data_dict])
        load_data_to_gpu(data_dict)
        pred_dicts, _ = model.forward(data_dict)

        # Print the resualt to screen
        print("+-------------------------------------------------------------------------------------------------+")
        print("num: ", len(pred_dicts[0]['pred_boxes']), "  class: ", num2class[int(pred_dicts[0]['pred_labels'][0].cpu().numpy())])
        idx = 1
        for pred_boxes in pred_dicts[0]['pred_boxes']:
            print('\n', idx, " ==> ", "loc: ", pred_boxes[0:3].cpu().numpy(), 
                            " size: ", pred_boxes[3:6].cpu().numpy(), '\n'
                            "        rotation: ", pred_boxes[6].cpu().numpy(),
                            "        score: ", pred_dicts[0]['pred_scores'][idx-1].cpu().numpy())
            idx += 1
        print("+-------------------------------------------------------------------------------------------------+\n")

        # store the results
        pred_boxes = pred_dicts[0]['pred_boxes'].cpu().numpy()
        pred_labels = pred_dicts[0]['pred_labels'].cpu().numpy()
        pred_scores = pred_dicts[0]['pred_scores'].cpu().numpy()

        # For test
        # import sys
        # sys.path.append('/home/zonlin/CRLFnet/src/site_model/src/utils/')
        # import visualization
        # visualization.lidar2visual(pred_boxes)


if __name__ == '__main__':
    # Python demo.py
    # main()

    # Test for real-time detection
    main_2()

    # Test for real-time detection
    # time1 = time.time()
    # pointcloud_detector = RT_Pred()
    # time2 = time.time()
    # print("建立网络用时：", (time2-time1)*1000)
    # time1 = time.time()
    # pointcloud_detector.get_pred_dicts()
    # time2 = time.time()
    # print("检测用时：", (time2-time1)*1000)