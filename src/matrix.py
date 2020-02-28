import numpy as np

print("Hello World")


def rot_matrix(matrix, degree):
    global rotm

    winkel = np.radians(degree)

    c, s = np.cos(winkel), np.sin(winkel)
    rotm = np.matrix([ [1,0,0],[0,c,-s],[0,s,c] ])

    print(rotm)
    return np.matmul(rotm, matrix)

def matrix():
    m1 = np.matrix([[1,0,0,0], [0,1,0,0], [0,0,1,0], [0,0,0,1]])
    m2 = np.matrix('1 0 0 0; 0 1 0 0; 0 0 1 0; 0 0 0 1')
    
    e2 = np.matrix('1 0; 0 1')
    e3 = np.matrix('1;1;1')

    print(e3)
    print("\n")

    rot = rot_matrix(e3, -90)

    print(rot)
    print(rot[2].item())

def mat_mult():
    m1 = np.matrix('3 2 1; 1 0 2')
    m2 = np.matrix('1 2; 0 1; 4 0')

    result = np.matmul(m1, m2)

    print(result)

matrix()