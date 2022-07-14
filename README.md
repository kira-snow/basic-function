# FusionHIFU

本项目实现的是高强度聚焦术中超声([HIFU](https://baike.baidu.com/item/%E9%AB%98%E5%BC%BA%E5%BA%A6%E8%81%9A%E7%84%A6%E8%B6%85%E5%A3%B0%E6%B2%BB%E7%96%97/2175829))图像与术前CT或MR图像的配准，代表了超声精准治疗（图像引导治疗，Image Guided Therapy）的方向，对于确定治疗区域，减少健康组织损伤，评估治疗结果都有重要指导意义。


[3D Slicer](https://www.slicer.org/)是一个常用的用于医学图像分析与可视化的开源软件框架，本项目实质是基于slicer的一个扩展（extension）。[Slicer ExtensionWizard](https://www.slicer.org/wiki/Documentation/Nightly/Developers/ExtensionWizard)


要想尽快熟悉此项目，建议学习如下知识（不断补充中）：
1. 下载3DSlicer并安装
2. 完成Issue中的Warmup Task
3. 查看Issue中Documentation类型的Issue
4. Clone此仓库中的代码到本地，将此Extension加入到Slicer的module中。
5. 查看Issue中的requirement类型的Issue.

本项目实现的功能如下

- 图像浏览与测量
- CT/MR图像三维重建
- 组织分割
- 治疗计划
- 图像融合
- 术后评估
