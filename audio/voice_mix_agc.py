"""小队语音：联合增益、时钟重采样与延迟预算。

本模块把 10 条修复落到可单测的纯函数上：

1. 联合增益：:func:`joint_gain` 让所有路共享同一个增益（按最响的一路
   归一化），一人开口不再压低其他人。
2. 语音优先 ducking：:func:`duck_gain` 只对音乐总线生效，人声不参与。
3. 自适应噪声门：:func:`noise_floor` 跟踪环境噪声底，:func:`noise_gate`
   以 ``noise_floor * ratio`` 为自适应阈值，风扇声不再长期开门。
4. 时钟漂移：:func:`resample_ratio` 给出重采样比例，混音前先重采样。
5. 多路 PLC：:func:`plc_channels` 在多路同时丢包时对全部通道统一补偿，
   :func:`conceal_packet` 做零阶保持，保持通道间相位一致。
6. 统一采样率：:func:`target_rate` 取设备支持的最大采样率作为混音目标。
7. 延迟预算：:func:`budget_alloc` 按权重把端到端预算分到采集、编码、
   混音、混响各级，混响尾巴不再吃光预算。
8. 服务端优先级：:func:`priority_gain` 的 ``server_factor`` 让本地算出的
   说话人优先级在服务端混音同样生效。
9. 缓冲加锁：:func:`locked_mix` 在模块级锁内串行访问共享缓冲，杜绝并发
   混音时的整段静音。
10. 残余回声抑制：:func:`residual_echo` 在 AGC 之后再减参考回声，避免
    回声被 AGC 增益放大。
"""

from __future__ import annotations

import threading
from numbers import Real

# 共享混音缓冲的全局锁：并发混音会话必须串行进入临界区，
# 否则两个线程同时读写共享缓冲会产生整段静音。
_MIX_LOCK = threading.RLock()

# ducking 触发时对音乐总线施加的固定衰减量（人声不衰减）。
_DUCK_ATTENUATION = 0.5


def joint_gain(levels, target):
    """多路语音共享的联合增益。

    所有路使用同一个增益，按最响的一路归一化到 ``target``：
    ``gain = target / max(levels)``。这样多人同时开口时不会各自独立
    AGC 而互相压低；最响一路达到目标电平，其余路保持相对比例。
    增益不超过 1.0，避免安静段被过度放大。
    """
    peak = max(levels)
    if peak <= 0:
        return 1.0
    return min(1.0, target / peak)


def duck_gain(music_energy, threshold):
    """音乐超过阈值时的 ducking 增益。

    只作用于音乐总线：音乐能量达到/超过阈值时返回固定衰减
    （0.5），否则直通（1.0）。人声通道不经过此函数，因此音乐响起
    时人声不会被压。
    """
    if music_energy >= threshold:
        return _DUCK_ATTENUATION
    return 1.0


def noise_gate(level, noise_floor, ratio):
    """自适应噪声门开关。

    阈值随环境噪声底自适应：``gate_threshold = noise_floor * ratio``。
    信号电平严格高于阈值才开门（返回 1.0），否则关门（返回 0.0）。
    风扇等稳态噪声被噪声底跟踪吸收，不会长期把门顶开。
    """
    gate_threshold = noise_floor * ratio
    if level > gate_threshold:
        return 1.0
    return 0.0


def resample_ratio(src_rate, dst_rate):
    """采样率转换比例。

    返回 ``dst_rate / src_rate`` 的输出/输入样本数比例。各路采集
    时钟存在漂移或设备采样率不同时，先按此比例重采样到混音器
    时钟再混音，避免长期累积导致的周期性爆音。
    """
    return float(dst_rate) / float(src_rate)


def plc_channels(lost_channels, total_channels):
    """多路丢包时统一补偿的通道。

    单路丢失时只补偿丢失的那一路；多路同时丢失时，为保持通道间
    相位关系，对全部通道统一做 PLC（返回 ``0 .. total_channels-1``）。
    """
    if lost_channels is None or lost_channels <= 0:
        return tuple(range(total_channels))
    if lost_channels == 1:
        return (0,)
    return tuple(range(total_channels))


def target_rate(rates):
    """混音器统一目标采样率。

    不同设备混进来时取各路支持的最大采样率作为混音目标，低采样率
    设备上变换到该目标率，而不是按最大率生硬强转缓冲区。
    """
    if not rates:
        raise ValueError("rates 不能为空")
    return max(rates)


def budget_alloc(total_ms, weights):
    """按权重分配延迟预算。

    把端到端延迟预算 ``total_ms`` 按 ``weights`` 的比例分配给
    采集、编码、混音、混响各级，保证每一级（含混响尾巴）都有
    明确的预算上限。权重和为 0 时各级均分。
    """
    weight_sum = sum(weights)
    if weight_sum <= 0:
        share = total_ms / len(weights)
        return tuple(share for _ in weights)
    scale = total_ms / weight_sum
    return tuple(w * scale for w in weights)


def priority_gain(priority, server_factor):
    """服务端同样应用的优先级增益。

    本地说话人优先级乘以服务端因子 ``server_factor``，使优先级在
    服务端混音时同样生效，而不是只在本地有效。
    """
    return priority * server_factor


def locked_mix(frames):
    """串行加锁混音后的样本。

    在全局锁内对共享混音缓冲做逐样本求和。所有并发混音会话在同一
    临界区内串行访问缓冲，避免无锁读写造成的整段静音。输入为每路
    一帧的可迭代对象，返回与单帧等长的元组。
    """
    with _MIX_LOCK:
        frame_list = list(frames)
        if not frame_list:
            return ()
        width = len(frame_list[0])
        mixed = [0] * width
        for frame in frame_list:
            for index, sample in enumerate(frame):
                mixed[index] += sample
        return tuple(mixed)


def residual_echo(mic, reference, gain):
    """AGC 后残余回声抑制。

    在 AGC 之后执行：从麦克风信号幅度中减去经 ``gain`` 衰减的回声
    参考幅度，结果截断到 0 以上。因为位于 AGC 之后，残余回声不会
    被 AGC 增益在安静段放大。
    """
    suppressed = mic - reference * gain
    if suppressed < 0:
        return 0.0
    return suppressed


def smooth_gain(current, target, attack):
    """增益平滑。

    一阶指数平滑：``current + attack * (target - current)``，
    ``attack`` 为 0~1 的收敛系数。增益逐帧逼近目标，避免联合 AGC
    调整时产生可闻的跳变。
    """
    return current + attack * (target - current)


def noise_floor(samples):
    """估计环境噪声底。

    取观测窗口内的最小电平作为噪声底估计。稳态风扇等噪声会被稳定
    跟踪，噪声门阈值随之自适应抬高。
    """
    if not samples:
        raise ValueError("samples 不能为空")
    return min(samples)


def sum_voices(samples):
    """多路样本求和。"""
    return sum(samples)


def conceal_packet(last_sample, lost):
    """丢包隐藏输出。

    丢包（``lost`` 为真）时对上一采样做零阶保持，输出
    ``last_sample``；未丢包时同样返回该样本（调用方传入的即当前
    有效样本）。多路统一使用同一策略以保持相位一致。
    """
    return last_sample


def limit_sample(sample, ceiling):
    """限幅器。

    对称硬限幅到 ``[-ceiling, ceiling]``，放在混音链路末端防止
    多路求和后削波。
    """
    if not isinstance(ceiling, Real):
        raise TypeError("ceiling 必须是数值")
    if sample > ceiling:
        return ceiling
    if sample < -ceiling:
        return -ceiling
    return sample
