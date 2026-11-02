# 从这里开始

先读README.md认识两个用途及小模型限制，再按RUN.md确认系统。

macOS：安装Python3.9+，在本目录运行 `bash start.sh`。首次下载约187MB软件和523MB模型；只监听本机，运行完成即停止服务。Windows ARM64有start.cmd，但本期未核心实测；Linux和Windows x64须用已有官方CLI，详见RUN.md。

成功后看output/中的四份文本结果和verification.json。摘要对照fixtures.json原文复核；结构化字段应与expected对应。修改样例后，不把旧预期继续当新答案。

图在images/；输出是本期真实模型结果的重排，不是软件图形界面截图。README、FAQ与SERVICE保留许可、适用边界和已发现的误读。
