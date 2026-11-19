import pytest

from audio import voice_mix_agc as mod

CASES = [
    pytest.param('joint_gain', ([1.0, 1.0], 0.5), 0.5, True, id='01_joint_gain'),
    pytest.param('duck_gain', (2.0, 1.0), 0.5, True, id='02_music_only_ducking'),
    pytest.param('noise_gate', (0.02, 0.01, 2.0), 0.0, True, id='03_adaptive_noise_gate'),
    pytest.param('resample_ratio', (48000, 16000), 0.3333333333333333, True, id='04_clock_resample_ratio'),
    pytest.param('plc_channels', (2, 4), (0, 1, 2, 3), False, id='05_multichannel_plc'),
    pytest.param('target_rate', ([16000, 48000, 44100],), 48000, False, id='06_uniform_sample_rate'),
    pytest.param('budget_alloc', (10.0, [1.0, 1.0]), (5.0, 5.0), True, id='07_latency_budget'),
    pytest.param('priority_gain', (1.0, 1.2), 1.2, True, id='08_server_priority'),
    pytest.param('locked_mix', ([(1, 2), (3, 4)],), (4, 6), False, id='09_locked_mix'),
    pytest.param('residual_echo', (1.0, 0.5, 0.5), 0.75, True, id='10_residual_echo_suppression'),
    pytest.param('smooth_gain', (0.0, 1.0, 0.25), 0.25, True, id='11_gain_smoothing'),
    pytest.param('noise_floor', ([0.03, 0.01, 0.02],), 0.01, True, id='12_noise_floor'),
    pytest.param('sum_voices', ([1, 2],), 3, False, id='13_voice_sum'),
    pytest.param('conceal_packet', (5.0, True), 5.0, True, id='14_packet_concealment'),
    pytest.param('limit_sample', (1.2, 1.0), 1.0, True, id='15_limiter'),
]


def assert_close(actual, expected):
    if isinstance(expected, tuple):
        assert isinstance(actual, tuple) and len(actual) == len(expected)
        for a, e in zip(actual, expected):
            assert_close(a, e)
    elif isinstance(expected, list):
        assert isinstance(actual, list) and len(actual) == len(expected)
        for a, e in zip(actual, expected):
            assert_close(a, e)
    elif isinstance(expected, dict):
        assert actual.keys() == expected.keys()
        for key in expected:
            assert_close(actual[key], expected[key])
    else:
        assert actual == pytest.approx(expected)


@pytest.mark.parametrize("func_name,args,expected,approx", CASES)
def test_voice_mix_agc_contract(func_name, args, expected, approx):
    func = getattr(mod, func_name)
    result = func(*args)
    if approx:
        assert_close(result, expected)
    else:
        assert result == expected
