from ptc_spiral.trajectory import spiral_trajectory


def test_spiral_property_holds():
    N = 12345678901234567890
    primes = [3, 5, 7, 11, 13, 17, 19]

    traj = spiral_trajectory(N, primes)

    # property: x_{k+1} % M_k == x_k
    for (M1, x1), (_M2, x2) in zip(traj, traj[1:]):
        assert x2 % M1 == x1
