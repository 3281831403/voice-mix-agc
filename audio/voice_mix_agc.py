"""小队语音：联合增益、时钟重采样与延迟预算：待实现的核心模块。"""

from __future__ import annotations


def joint_gain(levels, target):
    """多路语音共享的联合增益。"""
    raise NotImplementedError

def duck_gain(music_energy, threshold):
    """音乐超过阈值时的 ducking 增益。"""
    raise NotImplementedError

def noise_gate(level, noise_floor, ratio):
    """自适应噪声门开关。"""
    raise NotImplementedError

def resample_ratio(src_rate, dst_rate):
    """采样率转换比例。"""
    raise NotImplementedError

def plc_channels(lost_channels, total_channels):
    """多路丢包时统一补偿的通道。"""
    raise NotImplementedError

def target_rate(rates):
    """混音器统一目标采样率。"""
    raise NotImplementedError

def budget_alloc(total_ms, weights):
    """按权重分配延迟预算。"""
    raise NotImplementedError

def priority_gain(priority, server_factor):
    """服务端同样应用的优先级增益。"""
    raise NotImplementedError

def locked_mix(frames):
    """串行加锁混音后的样本。"""
    raise NotImplementedError

def residual_echo(mic, reference, gain):
    """AGC 后残余回声抑制。"""
    raise NotImplementedError

def smooth_gain(current, target, attack):
    """增益平滑。"""
    raise NotImplementedError

def noise_floor(samples):
    """估计环境噪声底。"""
    raise NotImplementedError

def sum_voices(samples):
    """多路样本求和。"""
    raise NotImplementedError

def conceal_packet(last_sample, lost):
    """丢包隐藏输出。"""
    raise NotImplementedError

def limit_sample(sample, ceiling):
    """限幅器。"""
    raise NotImplementedError
