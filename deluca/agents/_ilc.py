import time
import jax.numpy as np
import numpy as onp
# from deluca.agents._ilqr import LQR
from deluca.agents.core import Agent
from deluca.agents.planning_utils import f_at_x, rollout, LQR

def iLC_closed(env_true, env_sim, U, T, k=None, K=None, X=None, ref_alpha=1.0, log=None):
    alpha, r = ref_alpha, 1
    X, U, c = rollout(env_true, U, k, K, X)
    print('initial cost:' + str(c))
    for t in range(T):
        _, F, C = f_at_x(env_sim, X, U)
        k, K = LQR(F, C)
        for alphaC in alpha * 1.1 * 1.1 ** (-np.arange(10) ** 2):
            r += 1
            XC, UC, cC = rollout(env_true, U, k, K, X, alphaC)
            if cC <= c:
                X, U, c, alpha = XC, UC, cC, alphaC
                print(
                    f"(iLC): t = {t}, r = {r}, c = {c}, alpha = {alpha}"
                )
                if log is not None:
                    log.append(f"(iLC): t = {t}, r = {r}, c = {c}, alpha = {alpha}")
                break
        else:
            return X, U, k, K, c
    return X, U, k, K, c

class ILCInner:
    def __init__(self, env_true, env_sim):
        self.env_true = env_true
        self.env_sim = env_sim

    def train(self, T, U_init=None, k=None, K=None, X=None, ref_alpha=1.0):
        self.log = []
        if U_init is None:
            U_init = [jnp.zeros(self.env_true.action_dim) for _ in range(self.env_true.H)]
        X, U, k, K, c = iLC_closed(self.env_true, 
                                   self.env_sim, 
                                   U_init, 
                                   T, 
                                   k,
                                   K,
                                   X,
                                   ref_alpha,
                                   self.log)
        return X, U, k, K, c, self.log


class ILC(Agent):
    def __init__(self):
        self.reset()

    def train(self, env_true, env_sim, train_steps, U_init=None, k=None, K=None, X=None, ref_alpha=1.0):
        self.env_true = env_true
        self.env_sim = env_sim
        ilqr_agent = ILCInner(self.env_true, self.env_sim)
        X, U, k, K, c, log = ilqr_agent.train(train_steps, U_init, k, K, X, ref_alpha)
        self.U = np.array(U)
        self.X = np.array(X)
        self.k = np.array(k)
        self.K = np.array(K)
        return c, log

    def reset(self):
        self.t = 0

    def __call__(self, state):
        action = self.U[self.t]
        self.t += 1

        return action