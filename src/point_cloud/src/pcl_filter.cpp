#include <iostream>
#include <ros/ros.h>
#include <pcl/visualization/cloud_viewer.h>
#include <sensor_msgs/PointCloud2.h>
#include <pcl_conversions/pcl_conversions.h>
#include <pcl/filters/statistical_outlier_removal.h>
#include <pcl/filters/voxel_grid.h>

class cloudHandler
{
public:
    cloudHandler()
    : viewer("Cloud Viewer")
    {
        pcl::PointCloud<pcl::PointXYZ> cloud;
        pcl::PointCloud<pcl::PointXYZ> cloud_filtered; // 经过滤波后的点云
        pcl::PointCloud<pcl::PointXYZ> cloud_downsampled; // 经过下采样后的点云
        pcl::io::loadPCDFile ("test_pcd.pcd", cloud);
 
        //剔除离群值
        pcl::StatisticalOutlierRemoval<pcl::PointXYZ> statFilter; // 统计离群值算法
        statFilter.setInputCloud(cloud.makeShared()); // 输入点云
        statFilter.setMeanK(10); // 均值滤波
        statFilter.setStddevMulThresh(0.4); // 方差0.4
        statFilter.filter(cloud_filtered); // 输出结果到点云

        //缩减采样
        pcl::VoxelGrid<pcl::PointXYZ> voxelSampler; // 初始化 体素栅格滤波器
        voxelSampler.setInputCloud(cloud_filtered.makeShared()); // 输入点云
        voxelSampler.setLeafSize(0.01f, 0.01f, 0.01f); // 每个体素的长宽高0.01m
        voxelSampler.filter(cloud_downsampled); // 输出点云结果
 
        viewer.showCloud(cloud_filtered.makeShared());
        viewer_timer = nh.createTimer(ros::Duration(0.1), &cloudHandler::timerCB, this);
    }
 
    void timerCB(const ros::TimerEvent&)
    {
        if (viewer.wasStopped())
        {
            ros::shutdown();
        }
    }
 
protected:
    ros::NodeHandle nh;
    
    pcl::visualization::CloudViewer viewer;
    ros::Timer viewer_timer;
};
 
main (int argc, char **argv)
{
    ros::init (argc, argv, "pcl_filter");
    cloudHandler handler;
    ros::spin();
    return 0;
}