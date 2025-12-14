# 0. 效果演示
![img.png](img/img.png) \
演示音频分割功能可以访问 https://www.bilibili.com/video/BV1oxrcYuELK \
演示视频分割功能可以访问 https://www.bilibili.com/video/BV1xYweeKEvZ \
演示热词功能 https://www.bilibili.com/video/BV1uZuSzFEtM \
如果是不懂代码的人想要使用本项目，可以使用我打包好的程序，我是在Windows 11系统上打包的，不确定Windows其它版本是否能用，如果是非Windows系统，请使用源码方式运行。 \
[点击这里跳转到打包好的可执行程序](https://item.taobao.com/item.htm?ft=t&id=853452834970)
# 1. 说明
这是基于开源的 FunASR 实现的说话人分离的 GUI 项目，可以在支持图形界面中的任意 PC 端运行 \
要求 python version >= 3.8 \
支持运行在 Windows、MacOS、Linux 系统 \
本项目适合个人电脑使用，如果要在生产服务器中部署，并且需要并发处理，可到我博客中联系我 \
热词功能，在当前路径下的 hotwords.txt 中写入热词，每个热词一行 \
区分说话人语音识别接口可[点击这里](https://github.com/lukeewin/FunASR_API)
# 2. 开发日志
2023-11-14 对选择的多个音频分离不同的人声 \
2024-01-04 保存每个说话人对应的内容 \
2024-01-09 增加合并相同说话人功能 \
2024-01-22 增加视频切片功能 \
2024-02-25 新增允许控制每个音频片段切割的字符数 \
2025-07-19 新增支持热词功能
# 3. 安装
执行下面命令来安装依赖
```shell
pip install -U funasr modelscope ffmpeg-python pydub
```
此外还需要安装 torch，可以到 torch 官方中根据自己电脑情况安装不同版本的 torch \
安装 ffmpeg，可以到 github 中搜索 ffmpeg，下载解压后，配置环境变量 \
如果不会安装 torch 和 ffmpeg，可以参考我之前发布到博客中的一篇[文章](https://blog.lukeewin.top/archives/windows-an-zhuang-whisper#toc-head-1)。
# 4. 功能
1. 支持对指定的单个或者多个音频中不同的说话人讲的话进行分离，分别归类到不同的目录中
2. 保存每个说话人对应的包含时间戳的文本内容
3. 支持视频切片，根据说话人声音进行视频切片 
4. 支持自定义热词

# 5. 模型下载
执行下面程序，会自动下载模型到当前用户 .cache/modelscope/hub/models/iic/ 目录中
```shell
python download_model.py
```
# 6. 联系
可以添加交流群 693367146，添加时记得备注来自哪个平台 \
个人技术分享博客：https://blog.lukeewin.top \
如果是小白，不懂代码，可以[点击这里](https://item.taobao.com/item.htm?ft=t&id=853452834970)
# 7. 其它项目
1. [区分说话人语音识别接口，可点击这里跳转](https://github.com/lukeewin/FunASR_API)
2. 基于 Java 开发的桌面端实时字幕软件，[可点击这里跳转](https://github.com/lukeewin/desktop_subtitle)
3. 基于 Celery + Redis 开发的分布式区分说话人语音识别项目，适用于中大型公司使用，可分布式部署在多台服务器中，可使用多张显卡。（非开源项目，有意愿的公司可联系微信 lukeewin01）
4. 基于 Java 开发的实时一句话语音识别项目，在阿里云高性能计算型服务器中转写 10 秒音频耗时 100 毫秒，不需要显卡，使用 onnxruntime 推理模型，适合公司级项目使用。（非开源项目）
5. 基于 Java 开发的长录音转写项目，在阿里云高性能计算型服务器中转写 1 分钟音频耗时 1.1 秒，不需要显卡，使用 onnxruntime 推理模型。（非开源项目）
6. 区分说话人语音识别接口。（非开源项目）

