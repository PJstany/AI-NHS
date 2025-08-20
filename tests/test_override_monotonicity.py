from src.overrides import override_probability

def test_override_increases_with_uncertainty():
    p_low = override_probability(uncertainty=0.1, queue_len=5, time_of_day_factor=0.5,
                                 beta_uncertainty=2.0, beta_queue=0.03, beta_time_of_day=0.5,
                                 intercept=0.0, clinician_re=0.0)
    p_high = override_probability(uncertainty=0.9, queue_len=5, time_of_day_factor=0.5,
                                  beta_uncertainty=2.0, beta_queue=0.03, beta_time_of_day=0.5,
                                  intercept=0.0, clinician_re=0.0)
    assert p_high > p_low

