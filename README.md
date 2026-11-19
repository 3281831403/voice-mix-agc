# 小队语音：联合增益、时钟重采样与延迟预算

多人同时说话忽大忽小：每路 AGC 独立、ducking 压所有人声、噪声门固定、采集时钟漂移、多路丢包相位乱、共享缓冲无锁。本仓库固定混音资源与优先级。

- 领域：游戏、图形与多媒体
- 子方向：音视频处理
- 语言/框架：Python 3, pytest
- 初始状态：15 个参数化用例全部失败

## 目录结构

```
README.md
conftest.py
.gitignore
audio/__init__.py
audio/voice_mix_agc.py
tests/test_voice_mix_agc.py
```

## 需要修复的 10 个问题

1. 多路语音使用联合增益，一人开口不压低其他人
2. ducking 只压音乐，不压人声，按语音优先
3. 噪声门阈值随环境噪声自适应，风扇不长期开门
4. 各路采集时钟漂移时先重采样再混音
5. 多路同时丢包时统一 PLC，保持通道间相位
6. 不同设备采样率统一到混音器目标采样率
7. 端到端延迟预算分配到采集、编码、混音与混响
8. 说话人优先级在服务端混音同样生效
9. 并发混音共享缓冲加锁，不出现整段静音
10. 残余回声在 AGC 之后抑制，不被增益放大

## 15 条验收契约

    01. joint gain — `joint_gain`
    02. music only ducking — `duck_gain`
    03. adaptive noise gate — `noise_gate`
    04. clock resample ratio — `resample_ratio`
    05. multichannel plc — `plc_channels`
    06. uniform sample rate — `target_rate`
    07. latency budget — `budget_alloc`
    08. server priority — `priority_gain`
    09. locked mix — `locked_mix`
    10. residual echo suppression — `residual_echo`
    11. gain smoothing — `smooth_gain`
    12. noise floor — `noise_floor`
    13. voice sum — `sum_voices`
    14. packet concealment — `conceal_packet`
    15. limiter — `limit_sample`

## 当前状态

`audio/voice_mix_agc.py` 只保留函数签名与文档字符串，所有函数体统一
`raise NotImplementedError`。`tests/test_voice_mix_agc.py` 使用一个
`@pytest.mark.parametrize` 装载 15 条契约，初始全部失败且没有 collection error。

```bash
python -m pytest -q
```

预期输出包含 `15 failed`。实现 `audio/voice_mix_agc.py` 后，15 条契约应全部通过。
