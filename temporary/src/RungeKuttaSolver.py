# ODE solver class
class RungeKuttaSolver:

    def __init__(self, dynamics, n_int):
        self.dynamics = dynamics
        self.n_int = n_int

    def RK4(self, x, u, tau):
        h = tau/self.n_int
        k = [[],[],[],[]]
        x_dim = len(x)
        tmp = [0.0]*x_dim
        x_post = x

        for _ in range(self.n_int):
            k[0] = self.dynamics(x,u)
            for i in range(x_dim):
                tmp[i] = x[i] + h/2.0*k[0][i]

            k[1] = self.dynamics(tmp, u)
            for i in range(x_dim):
                tmp[i] = x[i] + h/2.0*k[1][i]

            k[2] = self.dynamics(tmp, u)
            for i in range(x_dim):
                tmp[i] = x[i] + h*k[2][i]

            k[3] = self.dynamics(tmp, u)
            for i in range(x_dim):
                x_post[i] = x[i] + (h/6.0)*(k[0][i] + 2.0*k[1][i] + 2.0*k[2][i] + k[3][i])

        return x_post
