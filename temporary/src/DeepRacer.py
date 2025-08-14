import numpy as np
import math
import RungeKuttaSolver

# unmap the throttle to the values accepted by the DeepRacer

def unmap_trottle(throttle_in):
    switcher = {
        6: 0.70,
        5: 0.65,
        4: 0.60,
        3: 0.55,
        2: 0.50,
        1: 0.45,
        0: 0.00,
        -1: -0.45,
        -2: -0.50,
        -3: -0.55,
        -4: -0.60,
        -5: -0.65,
        -6: -0.70
    }
    return switcher.get(throttle_in, "Invalid input")

# unmap the angle to the values accepted by the DeepRacer
def unmap_angle(angle_in):
    return angle_in

def deepracer_ode(x,u): 
    dxdt = np.zeros((4,1)) # creates a 4x1 matrix of 0s
    u_steer = map_steering(u[0])
    u_speed = map_speed(u[1])
    L = 0.165
    [a,b] = get_v_params(u_speed)

    dxdt[0] = np.multiply(x[3], math.cos(x[2])) # x(4)*cos(x(3));
    dxdt[1] = np.multiply(x[3], math.sin(x[2])) # x(4)*sin(x(3));
    dxdt[2] = np.multiply((np.divide(x[3], L)), math.tan(u_steer)) # (x(4)/L)*tan(u_steer);
    dxdt[3] = (np.multiply(a, x[3])) + (np.multiply(b, u_speed)) # a*x(4) + b*u_speed;

    return dxdt

def get_v_params(u_speed):

    if u_speed == 0.0:
        K = 0.0; T = 0.25
    elif u_speed == 0.45:
        K = 1.9953; T = 0.9933
    elif u_speed == 0.50:
        K = 2.3567; T = 0.8943
    elif u_speed == 0.55:
        K = 3.0797; T = 0.88976
    elif u_speed == 0.60:
        K = 3.2019; T = 0.87595
    elif u_speed == 0.65:
        K = 3.3276; T = 0.89594
    elif u_speed == 0.70:
        K = 3.7645; T = 0.92501
    elif u_speed == -0.45:
        K = 1.8229; T = 1.8431
    elif u_speed == -0.50:
        K = 2.3833; T = 1.2721
    elif u_speed == -0.55:
        K = 2.512; T = 1.1403
    elif u_speed == -0.60:
        K = 3.0956; T = 1.1278
    elif u_speed == -0.65:
        K = 3.55; T = 1.1226
    elif u_speed == -0.70:
        K = 3.6423; T = 1.1539
    else:
        print("Error. Invalid input!")
        return None

    a = -1/T
    b = K/T
    
    return [a,b]

def map_steering(angle_in):

    p1 = -0.1167
    p2 = 0.01949
    p3 = 0.3828
    p4 = -0.0293
    x = angle_in
    psi = (p1*pow(x,3)) + (p2*pow(x, 2)) + (p3*x) + p4
    
    return psi

def map_speed(speed_in):
    s = 0
    if speed_in == 6:
        s = 0.70
    elif speed_in == 5:
        s = 0.65
    elif speed_in == 4:
        s = 0.60
    elif speed_in == 3:
        s = 0.55
    elif speed_in == 2:
        s = 0.50
    elif speed_in == 1:
        s = 0.45
    elif speed_in == 0:
        s = 0.00
    elif speed_in == -1:
        s = -0.45
    elif speed_in == -2:
        s = -0.50
    elif speed_in == -3:
        s = -0.55
    elif speed_in == -4:
        s = -0.60
    elif speed_in == -5:
        s = -0.65
    elif speed_in == -6:
        s = -0.70
    
    return s

def wrapToPi(rad):
    M_PI = math.pi
    M_2PI = 2*math.pi
    ret = rad
    ret -= M_2PI * math.floor((ret + M_PI) * (1.0/M_2PI))
    return ret

def simulate(x, u, tau):

    # initialize values
    #tau = 0.5
    Tmax = 5 * tau
    #u = [-0.8, 1]
    x0 = [0, 0, 0, 0]
    solver = RungeKuttaSolver.RungeKuttaSolver(deepracer_ode, 5)
    #x = x0
    
    next_x = solver.RK4(x, u, tau)
    next_x[2] = wrapToPi(next_x[2])
    x = next_x

    return next_x