__author__ = 'Sergey'
from numpy.linalg import inv
from numpy import cosh, sinh
from scipy.misc import factorial
from ocelot.cpbd.beam import Particle, Twiss, ParticleArray
from ocelot.cpbd.high_order import *
from ocelot.cpbd.r_matrix import *
from copy import deepcopy
from ocelot.common.logging import Logger
logger = Logger()


def transform_vec_ent(X, dx, dy, tilt):
    n = len(X)
    rotmat = rot_mtx(tilt)
    x_add = np.add(X.reshape(n / 6, 6), np.array([-dx, 0., -dy, 0., 0., 0.])).transpose()
    X[:] = np.dot(rotmat, x_add).transpose().reshape(n)[:]
    return X


def transform_vec_ext(X, dx, dy, tilt):
    n = len(X)
    rotmat = rot_mtx(-tilt)
    x_tilt = np.dot(rotmat, np.transpose(X.reshape(n / 6, 6))).transpose()
    X[:] = np.add(x_tilt, np.array([dx, 0., dy, 0., 0., 0.])).reshape(n)[:]
    return X


class TransferMap:

    def __init__(self):
        self.dx = 0.
        self.dy = 0.
        self.tilt = 0.
        self.length = 0
        self.hx = 0.
        # test RF
        self.delta_e = 0.0
        self.delta_e_z = lambda z: 0.0
        # 6x6 linear transfer matrix

        self.R = lambda energy: eye(6)
        self.R_z = lambda z, energy: zeros((6, 6))
        self.B_z = lambda z, energy: dot((eye(6) - self.R_z(z, energy)), array([self.dx, 0., self.dy, 0., 0., 0.]))
        self.B = lambda energy: self.B_z(self.length, energy)
        #self.B = lambda energy: zeros(6)  # tmp matrix
        self.map = lambda u, energy: self.mul_p_array(u, energy=energy)

    def map_x_twiss(self, tws0):
        E = tws0.E
        M = self.R(E)
        #print(E, self.delta_e, M)
        zero_tol = 1.e-10
        if abs(self.delta_e) > zero_tol:
            #M = self.R(E + )
            Ei = tws0.E
            Ef = tws0.E + self.delta_e #* cos(self.phi)
            #print "Ei = ", Ei, "Ef = ", Ef
            k = np.sqrt(Ef/Ei)
            M[0, 0] = M[0, 0]*k
            M[0, 1] = M[0, 1]*k
            M[1, 0] = M[1, 0]*k
            M[1, 1] = M[1, 1]*k
            M[2, 2] = M[2, 2]*k
            M[2, 3] = M[2, 3]*k
            M[3, 2] = M[3, 2]*k
            M[3, 3] = M[3, 3]*k
            #M[4, 5] = M[3, 3]*k
            E = Ef
        m = tws0
        tws = Twiss(tws0)
        tws.E = E
        tws.p = m.p
        tws.beta_x = M[0, 0]*M[0, 0]*m.beta_x - 2*M[0, 1]*M[0, 0]*m.alpha_x + M[0, 1]*M[0, 1]*m.gamma_x
        # tws.beta_x = ((M[0,0]*tws.beta_x - M[0,1]*m.alpha_x)**2 + M[0,1]*M[0,1])/m.beta_x
        tws.beta_y = M[2, 2]*M[2, 2]*m.beta_y - 2*M[2, 3]*M[2, 2]*m.alpha_y + M[2, 3]*M[2, 3]*m.gamma_y
        # tws.beta_y = ((M[2,2]*tws.beta_y - M[2,3]*m.alpha_y)**2 + M[2,3]*M[2,3])/m.beta_y
        tws.alpha_x = -M[0, 0]*M[1, 0]*m.beta_x + (M[0, 1]*M[1, 0]+M[1, 1]*M[0, 0])*m.alpha_x - M[0, 1]*M[1, 1]*m.gamma_x
        tws.alpha_y = -M[2, 2]*M[3, 2]*m.beta_y + (M[2, 3]*M[3, 2]+M[3, 3]*M[2, 2])*m.alpha_y - M[2, 3]*M[3, 3]*m.gamma_y

        tws.gamma_x = (1. + tws.alpha_x*tws.alpha_x)/tws.beta_x
        tws.gamma_y = (1. + tws.alpha_y*tws.alpha_y)/tws.beta_y

        tws.Dx = M[0, 0]*m.Dx + M[0, 1]*m.Dxp + M[0, 5]
        tws.Dy = M[2, 2]*m.Dy + M[2, 3]*m.Dyp + M[2, 5]

        tws.Dxp = M[1, 0]*m.Dx + M[1, 1]*m.Dxp + M[1, 5]
        tws.Dyp = M[3, 2]*m.Dy + M[3, 3]*m.Dyp + M[3, 5]
        denom_x = M[0, 0]*m.beta_x - M[0, 1]*m.alpha_x
        if denom_x == 0.:
            d_mux = np.pi/2.*M[0, 1]/np.abs(M[0, 1])
        else:
            d_mux = np.arctan(M[0, 1]/denom_x)

        if d_mux < 0:
            d_mux += np.pi
        tws.mux = m.mux + d_mux
        #print M[0, 0]*m.beta_x - M[0, 1]*m.alpha_x, arctan(M[2, 3]/(M[2, 2]*m.beta_y - M[2, 3]*m.alpha_y))
        denom_y = M[2, 2]*m.beta_y - M[2, 3]*m.alpha_y
        if denom_y == 0.:
            d_muy = np.pi/2.*M[2, 3]/np.abs(M[2, 3])
        else:
            d_muy = np.arctan(M[2, 3]/denom_y)
        if d_muy < 0:
            d_muy += np.pi
        tws.muy = m.muy + d_muy
        return tws

    def mul_p_array(self, particles, energy=0.):
        #print("linear:", self.R(0.1))
        #print 'Map: mul_p_array', self.order, order
        #ocelot.logger.debug('invoking mul_p_array, particle array len ' + str(len(particles)))
        #ocelot.logger.debug(order)
        #ocelot.logger.debug(self.method)

        n = len(particles)
        if 'pulse' in self.__dict__:
            logger.debug('TD transfer map')
            if n > 6: logger.debug('warning: time-dependent transfer maps not implemented for an array. Using 1st particle value')
            if n > 6: logger.debug('warning: time-dependent transfer maps not implemented for steps inside element')
            tau = particles[4]
            dxp = self.pulse.kick_x(tau)
            dyp = self.pulse.kick_y(tau)
            logger.debug('kick ' + str(dxp) + ' ' + str(dyp))
            b = array([0.0, dxp, 0.0, dyp, 0., 0.])
            a = np.add(np.transpose(dot(self.R(energy), np.transpose(particles.reshape(n/6, 6)))), b).reshape(n)
        else:
            a = np.add(np.transpose(dot(self.R(energy), np.transpose(particles.reshape(n/6, 6)))), self.B(energy)).reshape(n)
        particles[:] = a[:]
        logger.debug('return trajectory, array ' + str(len(particles)))
        return particles

    def __mul__(self, m):
        """
        :param m: TransferMap, Particle or Twiss
        :return: TransferMap, Particle or Twiss
        Ma = {Ba, Ra, Ta}
        Mb = {Bb, Rb, Tb}
        X1 = R*(X0 - dX) + dX = R*X0 + B
        B = (E - R)*dX
        """

        if m.__class__ in [TransferMap]:
            m2 = TransferMap()
            m2.R = lambda energy: dot(self.R(energy), m.R(energy))
            m2.B = lambda energy: dot(self.R(energy), m.B(energy)) + self.B(energy)  #+dB #check
            m2.length = m.length + self.length
            #print("B = ", m2.R(0))
            #m2.delta_e += self.delta_e

            return m2

        elif m.__class__ == Particle:
            self.apply(m)
            return deepcopy(m)

        elif m.__class__ == Twiss:

            tws = self.map_x_twiss(m)
            # trajectory
            #X0 = array([m.x, m.xp, m.y, m.yp, m.tau, m.p])
            #tws.x, tws.xp, tws.y, tws.yp, tws.tau, tws.dE = self.mul_p_array(X0, energy=tws.E, order=1)
            tws.s = m.s + self.length
            return tws

        else:
            print(m.__class__)
            exit("unknown object in transfer map multiplication (TransferMap.__mul__)")

    def apply(self, prcl_series):
        """
        :param prcl_series: can be list of Particles [Particle_1, Particle_2, ... ] or ParticleArray
        :return: None
        """
        if prcl_series.__class__ == ParticleArray:
            self.map(prcl_series.particles, energy=prcl_series.E)
            prcl_series.E += self.delta_e
            prcl_series.s += self.length

        elif prcl_series.__class__ == Particle:
            p = prcl_series
            p.x, p.px, p.y, p.py, p.tau, p.p = self.map(array([p.x, p.px, p.y, p.py, p.tau, p.p]), p.E)
            p.s += self.length
            p.E += self.delta_e

        elif prcl_series.__class__ == list and prcl_series[0].__class__ == Particle:
            # If the energy is not the same (p.E) for all Particles in the list of Particles
            # in that case cycle is applied. For particles with the same energy p.E
            list_e = array([p.E for p in prcl_series])
            if False in (list_e[:] == list_e[0]):
                for p in prcl_series:
                    self.map(array([p.x, p.px, p.y, p.py, p.tau, p.p]), energy=p.E)
                    p.E += self.delta_e
                    p.s += self.length
            else:
                pa = ParticleArray()
                pa.list2array(prcl_series)
                pa.E = prcl_series[0].E
                self.map(pa.particles, energy=pa.E)
                pa.E += self.delta_e
                pa.s += self.length
                pa.array2ex_list(prcl_series)

        else:
            print(prcl_series)
            exit("Unknown type of Particle_series. class TransferMap.apply()")

    def __call__(self, s):
        m = copy(self)
        m.length = s
        m.R = lambda energy: m.R_z(s, energy)
        m.B = lambda energy: m.B_z(s, energy)
        m.delta_e = m.delta_e_z(s)
        m.map = lambda u, energy: m.mul_p_array(u, energy=energy)
        return m

class PulseTM(TransferMap):
    def __init__(self, kn):
        TransferMap.__init__(self)


class MultipoleTM(TransferMap):
    def __init__(self, kn):
        TransferMap.__init__(self)
        self.kn = kn
        self.map = lambda X, energy: self.kick(X, self.kn)

    def kick(self, X, kn):
        p = -kn[0] * X[5::6] + 0j
        for n in range(1, len(kn)):
            p += kn[n] * (X[0::6] + 1j * X[2::6]) ** n / factorial(n)
        X[1::6] = X[1::6] - np.real(p)
        X[3::6] = X[3::6] + np.imag(p)
        X[4::6] = X[4::6] - kn[0] * X[0::6]
        #print("multipole 2", X)
        return X

    def __call__(self, s):
        m = copy(self)
        m.length = s
        m.R = lambda energy: m.R_z(s, energy)
        m.B = lambda energy: m.B_z(s, energy)
        m.delta_e = m.delta_e_z(s)
        m.map = lambda X, energy: m.kick(X, m.kn)
        return m

class CorrectorTM(TransferMap):
    def __init__(self, angle_x=0., angle_y=0.):
        TransferMap.__init__(self)
        self.angle_x = angle_x
        self.angle_y = angle_y
        self.map = lambda X, energy: self.kick(X, self.length, self.length, self.angle_x, self.angle_y, energy)
        self.B_z = lambda z, energy: self.kick_b(z, self.length, angle_x, angle_y)

    def kick_b(self, z, l, angle_x, angle_y):
        if l == 0:
            hx = 0.
            hy = 0.
        else:
            hx = angle_x / l
            hy = angle_y / l

        dx = hx * z * z / 2.
        dy = hy * z * z / 2.
        dx1 = hx * z if l != 0 else angle_x
        dy1 = hy * z if l != 0 else angle_y
        b = array([dx, dx1, dy, dy1, 0., 0.])
        return b

    def kick(self, X,  z, l, angle_x, angle_y, energy):
        #print("corrector kick", angle_x, angle_y)
        #ocelot.logger.debug('invoking kick_b')
        n = len(X)
        b = self.kick_b(z, l, angle_x, angle_y)
        X1 = np.add(np.transpose(dot(self.R(energy), np.transpose( X.reshape(n/6, 6)))), b).reshape(n)
        #print(X1)
        X[:] = X1[:]
        return X

    def __call__(self, s):
        m = copy(self)
        m.length = s
        m.R = lambda energy: m.R_z(s, energy)
        m.B = lambda energy: m.B_z(s, energy)
        m.delta_e = m.delta_e_z(s)
        m.map = lambda X, energy: m.kick(X, s, self.length, m.angle_x, m.angle_y, energy)
        return m


class CavityTM(TransferMap):
    def __init__(self, v=0, f=0., phi=0.):
        TransferMap.__init__(self)
        self.v = v
        self.f = f
        self.phi = phi
        self.delta_e_z = lambda z: self.v * np.cos(self.phi * np.pi / 180.) * z / self.length
        self.delta_e = self.v * np.cos(self.phi * np.pi / 180.)
        self.map = lambda X, energy: self.map4cav(X, energy,  self.v, self.f, self.phi)

    def map4cav(self, X, E,  V, freq, phi):
        #print("CAVITY")
        phi = phi*np.pi/180.
        X = self.mul_p_array(X, energy=E) #t_apply(R, T, X, dx, dy, tilt)
        delta_e = V*np.cos(phi)
        if E + delta_e > 0:
            k = 2.*np.pi*freq/speed_of_light
            #X[5::6] = (X[5::6]*E + V*np.cos(X[4::6]*k + phi) - delta_e)/(E + delta_e)
            E1=E + delta_e
            X[5::6] = X[5::6] + V/E1*(np.cos(-X[4::6]*k + phi) - np.cos(phi)-k*X[4::6]*np.sin(phi))
        return X

    def __call__(self, s):
        m = copy(self)
        m.length = s
        m.R = lambda energy: m.R_z(s, energy)
        m.B = lambda energy: m.B_z(s, energy)
        m.delta_e = m.delta_e_z(s)
        m.map = lambda X, energy: m.map4cav( X, energy,  m.v*s/self.length, m.f, m.phi)
        return m


class KickTM(TransferMap):
    def __init__(self, angle=0., k1=0., k2=0., k3=0., nkick=0.):
        TransferMap.__init__(self)
        self.angle = angle
        self.k1 = k1
        self.k2 = k2
        self.k3 = k3
        self.nkick = nkick

    def kick(self, X, l, angle, k1, k2, k3, energy, nkick=1):
        gamma = energy / m_e_GeV
        coef = 0
        if gamma != 0:
            gamma2 = gamma * gamma
            beta = 1. - 0.5 / gamma2
            coef = 1./(beta * beta * gamma2)
        l = l/nkick
        angle = angle/nkick

        dl = l / 2.
        k1 = k1*dl
        k2 = k2*dl
        k3 = k3*dl

        for i in range(nkick):

            x = X[0::6] + X[1::6] * dl - self.dx
            y = X[2::6] + X[3::6] * dl - self.dy
            tau = -X[5::6]*dl*coef

            p = -angle*X[5::6] + 0j
            #for n in range(1, len(kn)):
            xy1 = x + 1j*y
            xy2 = xy1*xy1
            xy3 = xy2*xy1
            p += k1*xy1 + k2*xy2 + k3*xy3
            X[1::6] = X[1::6] - np.real(p)
            X[3::6] = X[3::6] + np.imag(p)
            #X[4::6] = X[4::6] - angle*X[0::6]
            X[4::6] = tau - angle * X[0::6]

            X[0::6] = x + X[1::6] * dl + self.dx
            X[2::6] = y + X[3::6] * dl + self.dy
            X[4::6] -= X[5::6]*dl*coef
            #print X[1], X[3]
        return X

    def __call__(self, s):
        m = copy(self)
        m.length = s
        m.R = lambda energy: m.R_z(s, energy)
        m.B = lambda energy: m.B_z(s, energy)
        m.delta_e = m.delta_e_z(s)
        m.map = lambda X, energy: m.kick( X, s, self.angle, self.k1, self.k2, self.k3, energy, self.nkick)
        return m


class UndulatorTestTM(TransferMap):
    def __init__(self, lperiod, Kx, ax=0, ndiv=10):
        TransferMap.__init__(self)
        self.lperiod = lperiod
        self.Kx = Kx
        self.ax = ax
        self.ndiv = ndiv
        self.map = lambda X, energy: self.map4undulator(X, self.length, self.lperiod, self.Kx, self.ax, energy, self.ndiv)

    def map4undulator(self, u, z, lperiod, Kx, ax, energy, ndiv):
        kz = 2. * np.pi / lperiod
        if ax == 0:
            kx = 0
        else:
            kx = 2. * np.pi/ax
        zi = linspace(0., z, num=ndiv)
        h = zi[1] - zi[0]
        kx2 = kx * kx
        kz2 = kz * kz
        ky2 = kz * kz + kx * kx
        ky = np.sqrt(ky2)
        gamma = energy / m_e_GeV
        h0 = 0.
        if gamma != 0:
            h0 = 1. / (gamma / Kx / kz)
        h02 = h0 * h0
        h = h / (1. + u[5::6])
        x = u[::6]
        y = u[2::6]
        for z in range(len(zi) - 1):
            chx = np.cosh(kx * x)
            chy = np.cosh(ky * y)
            shx = np.sinh(kx * x)
            shy = np.sinh(ky * y)
            u[1::6] -= h / 2. * chx * shx * (kx * ky2 * chy * chy + kx2 * kx * shy * shy) / (ky2 * kz2) * h02
            u[3::6] -= h / 2. * chy * shy * (ky2 * chx * chx + kx2 * shx * shx) / (ky * kz2) * h02
            u[4::6] -= h / 2. / (1. + u[5::6]) * ((u[1::6] * u[1::6] + u[3::6] * u[3::6]) + chx * chx * chy * chy / (
                        2. * kz2) * h02 + shx * shx * shy * shy * kx2 / (2. * ky2 * kz2) * h02)
            u[::6] = x + h * u[1::6]
            u[2::6] = y + h * u[3::6]
        return u

    def __call__(self, s):
        m = copy(self)
        m.length = s
        m.R = lambda energy: m.R_z(s, energy)
        m.B = lambda energy: m.B_z(s, energy)
        #m.T = m.T_z(s)
        m.delta_e = m.delta_e_z(s)
        # print(m.R_z_no_tilt(s, 0.3))
        m.map = lambda X, energy: m.map4undulator(X, m.length, m.lperiod, m.Kx, m.ax, energy, m.ndiv)
        return m


class RungeKuttaTM(TransferMap):
    def __init__(self, s_start=0, npoints=200):
        TransferMap.__init__(self)
        self.s_start = s_start
        self.npoints = npoints
        self.mag_field = lambda x, y, z: (0, 0, 0)
        self.map = lambda X, energy: rk_field(X, self.s_start, self.length, self.npoints, energy, self.mag_field)

    def __call__(self, s):
        m = copy(self)
        m.length = s
        m.R = lambda energy: m.R_z(s, energy)
        m.B = lambda energy: m.B_z(s, energy)
        m.delta_e = m.delta_e_z(s)
        # print(m.R_z_no_tilt(s, 0.3))
        m.map = lambda X, energy: rk_field(X, m.s_start, s, m.npoints, energy, m.mag_field)
        return m


class SecondTM(TransferMap):
    def __init__(self, r_z_no_tilt, t_mat_z_e):
        TransferMap.__init__(self)
        self.r_z_no_tilt = r_z_no_tilt
        self.t_mat_z_e = t_mat_z_e
        self.map = lambda X, energy: self.t_apply(self.r_z_no_tilt(self.length, energy), self.t_mat_z_e(self.length, energy), X, self.dx, self.dy, self.tilt)

    def t_apply(self, R, T, X, dx, dy, tilt, U5666=0.):
        #print("t_apply", self.k2, self.T)
        if dx != 0 or dy != 0 or tilt != 0:
            X = transform_vec_ent(X, dx, dy, -tilt)

        n = len(X)
        Xr = transpose(dot(R, transpose(X.reshape(n / 6, 6)))).reshape(n)

        # Xt = zeros(n)
        x, px, y, py, tau, dp = X[0::6], X[1::6], X[2::6], X[3::6], X[4::6], X[5::6]
        x2 = x * x
        xpx = x * px
        px2 = px * px
        py2 = py * py
        ypy = y * py
        y2 = y * y
        dp2 = dp * dp
        xdp = x * dp
        pxdp = px * dp
        xy = x * y
        xpy = x * py
        ypx = px * y
        pxpy = px * py
        ydp = y * dp
        pydp = py * dp

        X[0::6] = Xr[::6] + T[0, 0, 0] * x2 + T[0, 0, 1] * xpx + T[0, 0, 5] * xdp + T[0, 1, 1] * px2 + T[0, 1, 5] * pxdp + \
                  T[0, 5, 5] * dp2 + T[0, 2, 2] * y2 + T[0, 2, 3] * ypy + T[0, 3, 3] * py2

        X[1::6] = Xr[1::6] + T[1, 0, 0] * x2 + T[1, 0, 1] * xpx + T[1, 0, 5] * xdp + T[1, 1, 1] * px2 + T[1, 1, 5] * pxdp + \
                  T[1, 5, 5] * dp2 + T[1, 2, 2] * y2 + T[1, 2, 3] * ypy + T[1, 3, 3] * py2

        X[2::6] = Xr[2::6] + T[2, 0, 2] * xy + T[2, 0, 3] * xpy + T[2, 1, 2] * ypx + T[2, 1, 3] * pxpy + T[2, 2, 5] * ydp + \
                  T[2, 3, 5] * pydp

        X[3::6] = Xr[3::6] + T[3, 0, 2] * xy + T[3, 0, 3] * xpy + T[3, 1, 2] * ypx + T[3, 1, 3] * pxpy + T[3, 2, 5] * ydp + \
                  T[3, 3, 5] * pydp

        X[4::6] = Xr[4::6] + T[4, 0, 0] * x2 + T[4, 0, 1] * xpx + T[4, 0, 5] * xdp + T[4, 1, 1] * px2 + T[4, 1, 5] * pxdp + \
                  T[4, 5, 5] * dp2 + T[4, 2, 2] * y2 + T[4, 2, 3] * ypy + T[4, 3, 3] * py2 # + U5666*dp2*dp    # third order
        # X[:] = Xr[:] + Xt[:]

        if dx != 0 or dy != 0 or tilt != 0:
            X = transform_vec_ext(X, dx, dy, -tilt)

        return X

    def __call__(self, s):
        m = copy(self)
        m.length = s
        m.R = lambda energy: m.R_z(s, energy)
        m.B = lambda energy: m.B_z(s, energy)
        m.T = lambda s, energy: m.t_mat_z_e(s, energy)
        m.delta_e = m.delta_e_z(s)
        #print(m.R_z_no_tilt(s, 0.3))
        m.map = lambda X, energy: m.t_apply(m.r_z_no_tilt(s, energy), m.t_mat_z_e(s, energy), X, m.dx, m.dy, m.tilt)
        return m


class MethodTM:
    def __init__(self, params=None):
        if params == None:
            self.params = {'global': TransferMap}
        else:
            self.params = params

        if "global" in self.params.keys():
            self.global_method = self.params['global']
        else:
            self.global_method = TransferMap

        self.nkick = self.params['nkick'] if 'nkick' in self.params.keys() else 1

    def create_tm(self, element):
        if element.__class__ in self.params.keys():
            transfer_map = self.set_tm( element, self.params[element.__class__])
        else:
            transfer_map = self.set_tm(element, self.global_method )
        return transfer_map

    def set_tm(self, element, method):
        dx = element.dx
        dy = element.dy
        tilt = element.dtilt + element.tilt
        if element.l == 0:
            hx = 0.
        else:
            hx = element.angle / element.l

        r_z_e = create_r_matrix(element)

        # global method
        if method == KickTM:
            #print('kick')
            try:
                k3 = element.k3
            except:
                k3 = 0.
            tm = KickTM(angle=element.angle, k1=element.k1, k2=element.k2, k3=k3, nkick=self.nkick)

        elif method == SecondTM:
            T_z_e = lambda z, energy: t_nnn(z, hx, element.k1, element.k2, energy)

            if element.__class__ == Edge:
                if element.pos == 1:
                    R, T = fringe_ent(h=element.h, k1=element.k1, e=element.edge, h_pole=element.h_pole,
                                      gap=element.gap, fint=element.fint)
                else:
                    R, T = fringe_ext(h=element.h, k1=element.k1, e=element.edge, h_pole=element.h_pole,
                                      gap=element.gap, fint=element.fint)
                T_z_e = lambda z, energy: T
                #print("trm", tilt, element.edge, element.h, r_z_e(0, 130)[1, 0])
            tm = SecondTM(r_z_no_tilt=r_z_e, t_mat_z_e=T_z_e)

        else:
            tm = TransferMap()

        if element.__class__ == Undulator and method == UndulatorTestTM:
            try:
                ndiv = element.ndiv
            except:
                ndiv = 5
            tm = UndulatorTestTM(lperiod=element.lperiod, Kx=element.Kx, ax=element.ax, ndiv=ndiv)

        if method == RungeKuttaTM:
            try:
                s_start = element.s_start
            except:
                s_start = 0.
            try:
                npoints = element.npoints
            except:
                npoints = 200
            tm = RungeKuttaTM(s_start=s_start, npoints=npoints)
            tm.mag_field = element.mag_field

        if element.__class__ == Cavity:
            #print("CAVITY create")
            tm = CavityTM(v=element.v, f=element.f, phi=element.phi)

        if element.__class__ == Multipole:
            tm = MultipoleTM(kn=element.kn)

        if element.__class__ == Hcor:
            tm = CorrectorTM(angle_x=element.angle, angle_y=0.)

        if element.__class__ == Vcor:
            tm = CorrectorTM(angle_x=0, angle_y=element.angle)

        tm.length = element.l
        tm.dx = dx
        tm.dy = dy
        tm.tilt = tilt
        tm.R_z = lambda z, energy: np.dot(np.dot(rot_mtx(-tilt), r_z_e(z, energy)), rot_mtx(tilt))
        tm.R = lambda energy: tm.R_z(element.l, energy)
        #tm.B_z = lambda z, energy: dot((eye(6) - tm.R_z(z, energy)), array([dx, 0., dy, 0., 0., 0.]))
        #tm.B = lambda energy: tm.B_z(element.l, energy)

        return tm


def lattice_transfer_map(lattice, energy):
    """ transfer map for the whole lattice"""
    R = np.eye(6)
    #T = np.zeros((6, 6, 6))
    #print lattice.sequence[0].transfer_map.T
    for i, elem in enumerate(lattice.sequence):

        Rb = elem.transfer_map.R(energy)

        """
        Tb = elem.transfer_map.T
        Ta = deepcopy(T)
        for i in range(6):
            for j in range(6):
                for k in range(6):
                    t1 = np.dot(Rb[i, :], Ta[:, j, k])
                    t2 = 0.
                    for l in range(6):
                        for m in range(6):
                            t2 += Tb[i, l, m]*R[l, j]*R[m, k]
                    #print t1, t2
                    T[i,j,k] = t1+t2
        """
        R = dot(Rb, R)
        #print(elem.__class__.__name__, R)
        #T = Ta
        #print i, len(lattice.sequence), elem.type, elem.transfer_map.R(6)
    #print T
    #lattice.T = T
    #lattice.R = R
    #print(R)
    return R


def trace_z(lattice, obj0, z_array):
    """ Z-dependent tracer (twiss(z) and particle(z))
        usage: twiss = trace_z(lattice,twiss_0, [1.23, 2.56, ...]) ,
        to calculate Twiss params at 1.23m, 2.56m etc.
    """
    obj_list = []
    i = 0
    elem = lattice.sequence[i]
    L = elem.l
    obj_elem = obj0
    for z in z_array:
        while z > L:
            #print(lattice.sequence[i].transfer_map, obj_elem)
            obj_elem = lattice.sequence[i].transfer_map*obj_elem
            i += 1
            elem = lattice.sequence[i]
            L += elem.l

        obj_z = elem.transfer_map(z - (L - elem.l))*obj_elem

        obj_list.append(obj_z)
    return obj_list


def trace_obj(lattice, obj, nPoints = None):
    """ track object though lattice
        obj must be Twiss or Particle """

    if nPoints == None:
        obj_list = [obj]
        for e in lattice.sequence:
            #if e.__class__ == Edge:
            #    print( "EDGE", e.edge)
            obj = e.transfer_map*obj
            obj.id = e.id
            obj_list.append(obj)
    else:
        z_array = linspace(0, lattice.totalLen, nPoints, endpoint=True)
        obj_list = trace_z(lattice, obj, z_array)
    return obj_list

def periodic_twiss(tws, R):
    '''
    initial conditions for a periodic Twiss slution
    '''
    tws = Twiss(tws)

    cosmx = (R[0, 0] + R[1, 1])/2.
    cosmy = (R[2, 2] + R[3, 3])/2.

    if abs(cosmx) >= 1 or abs(cosmy) >= 1:
        logger.warn("************ periodic solution does not exist. return None ***********")
        #print("************ periodic solution does not exist. return None ***********")
        return None
    sinmx = np.sign(R[0, 1])*sqrt(1.-cosmx*cosmx)
    sinmy = np.sign(R[2, 3])*sqrt(1.-cosmy*cosmy)

    tws.beta_x = abs(R[0, 1]/sinmx)
    tws.beta_y = abs(R[2, 3]/sinmy)

    tws.alpha_x = (R[0, 0] - R[1, 1])/(2.*sinmx)  # X[0,0]

    tws.gamma_x = (1. + tws.alpha_x*tws.alpha_x)/tws.beta_x  # X[1,0]

    tws.alpha_y = (R[2, 2] - R[3, 3])/(2*sinmy)  # Y[0,0]
    tws.gamma_y = (1. + tws.alpha_y*tws.alpha_y)/tws.beta_y  # Y[1,0]

    Hx = array([[R[0, 0] - 1, R[0, 1]], [R[1, 0], R[1, 1]-1]])
    Hhx = array([[R[0, 5]], [R[1, 5]]])
    hh = dot(inv(-Hx), Hhx)
    tws.Dx = hh[0, 0]
    tws.Dxp = hh[1, 0]
    Hy = array([[R[2, 2] - 1, R[2, 3]], [R[3, 2], R[3, 3]-1]])
    Hhy = array([[R[2, 5]], [R[3, 5]]])
    hhy = dot(inv(-Hy), Hhy)
    tws.Dy = hhy[0, 0]
    tws.Dyp = hhy[1, 0]
    #tws.display()
    return tws

def twiss(lattice, tws0=None, nPoints=None):
    """
    twiss parameters calculation,
    :param lattice: lattice, MagneticLattice() object
    :param tws0: initial twiss parameters, Twiss() object. If None, try to find periodic solution.
    :param nPoints: number of points per cell. If None, then twiss parameters are calculated at the end of each element.
    :return: list of Twiss() objects
    """
    if tws0 == None:
        tws0 = periodic_twiss(tws0, lattice_transfer_map(lattice, energy=0.))

    if tws0.__class__ == Twiss:
        if tws0.beta_x == 0  or tws0.beta_y == 0:
            tws0 = periodic_twiss(tws0, lattice_transfer_map(lattice, tws0.E))
            if tws0 == None:
                print('Twiss: no periodic solution')
                return None
        else:
            tws0.gamma_x = (1. + tws0.alpha_x**2)/tws0.beta_x
            tws0.gamma_y = (1. + tws0.alpha_y**2)/tws0.beta_y

        twiss_list = trace_obj(lattice, tws0, nPoints)
        return twiss_list
    else:
        print('Twiss: no periodic solution')
        return None



#class Navigator:
#    def __init__(self, lattice = None):
#        if lattice != None:
#            self.lat = lattice
#
#    z0 = 0.             # current position of navigator
#    n_elem = 0          # current number of the element in lattice
#    sum_lengths = 0.    # sum_lengths = Sum[lat.sequence[i].l, {i, 0, n_elem-1}]

    #def check(self, dz):
    #    '''
    #    check if next step exceed the bounds of lattice
    #    '''
    #    if self.z0+dz>self.lat.totalLen:
    #        dz = self.lat.totalLen - self.z0
    #    return dz

class ProcessTable:
    def __init__(self, lattice):
        self.proc_list = []
        self.lat = lattice

    def add_physics_proc(self, physics_proc, elem1, elem2):
        physics_proc.start_elem = elem1
        physics_proc.end_elem = elem2
        #print(elem1.id, elem2.id, elem1.__hash__(), elem2.__hash__(), self.lat.sequence.index(elem1), self.lat.sequence.index(elem2))
        physics_proc.indx0 = self.lat.sequence.index(elem1)
        #print(self.lat.sequence.index(elem1))
        physics_proc.indx1 = self.lat.sequence.index(elem2)
        #print(self.lat.sequence.index(elem2))
        physics_proc.counter = physics_proc.step
        physics_proc.prepare(self.lat)
        self.proc_list.append(physics_proc)
        #print(elem1.__hash__(), elem2.__hash__(), physics_proc.indx0, physics_proc.indx1, self.proc_list)

class Navigator:
    """
    Navigator defines step (dz) of tracking and which physical process will be applied during each step.
    Methods:
    add_physics_proc(physics_proc, elem1, elem2)
        physics_proc - physics process, can be CSR, SpaceCharge or Wake,
        elem1 and elem2 - first and last elements between which the physics process will be applied.
    """
    def __init__(self, lattice=None):
        if lattice != None:
            self.lat = lattice
        self.process_table = ProcessTable(lattice)

        self.z0 = 0.             # current position of navigator
        self.n_elem = 0          # current index of the element in lattice
        self.sum_lengths = 0.    # sum_lengths = Sum[lat.sequence[i].l, {i, 0, n_elem-1}]
        self.unit_step = 1       # unit step for physics processes

    def add_physics_proc(self, physics_proc, elem1, elem2):
        self.process_table.add_physics_proc(physics_proc, elem1, elem2)

    def get_proc_list(self):

        proc_list = []
        for p in self.process_table.proc_list:
            if p.indx0 <= self.n_elem < p.indx1:
                proc_list.append(p)
        return proc_list

    def get_next(self):

        proc_list = self.get_proc_list()
        if len(proc_list) > 0:

            counters = np.array([p.counter for p in proc_list])
            step = counters.min()

            inxs = np.where(counters == step)
            processes = [proc_list[i] for i in inxs[0]]
            for p in proc_list:
                p.counter -= step
                if p.counter == 0:
                    p.counter = p.step
            dz = step*self.unit_step
        else:

            processes = proc_list
            n_elems = len(self.lat.sequence)
            if n_elems >= self.n_elem+1:
                L = np.sum(np.array([elem.l for elem in self.lat.sequence[:self.n_elem+1]]))
            else:
                L = self.lat.totalLen
            dz = L - self.z0
        logger.debug("navi.z0="+str(self.z0) + " navi.n_elem=" + str(self.n_elem) + " navi.sum_lengths=" +str(self.sum_lengths) + " dz=" +str(dz) + '\n' +
            "element type="+self.lat.sequence[self.n_elem].__class__.__name__ + " element name=" + self.lat.sequence[self.n_elem].id)

        return dz, processes


def get_map(lattice, dz, navi):
    nelems = len(lattice.sequence)
    TM = []
    i = navi.n_elem
    z1 = navi.z0 + dz
    elem = lattice.sequence[i]
    #navi.sum_lengths = np.sum([elem.l for elem in lattice.sequence[:i]])
    L = navi.sum_lengths + elem.l
    while z1 + 1e-10 > L:
        if i >= nelems-1:
            break
        dl = L - navi.z0
        TM.append(elem.transfer_map(dl))
        navi.z0 = L
        dz -= dl
        i += 1
        elem = lattice.sequence[i]
        L += elem.l
    if abs(dz) > 1e-10:
        TM.append(elem.transfer_map(dz))
    navi.z0 += dz
    navi.sum_lengths = L - elem.l
    navi.n_elem = i
    return TM


def merge_maps(t_maps):
    tm0 = TransferMap()
    t_maps_new = []
    for tm in t_maps:
        if tm.__class__ == TransferMap:
            tm0 = tm*tm0
        else:
            t_maps_new.append(tm0)
            t_maps_new.append(tm)
            tm0 = TransferMap()
    t_maps_new.append(tm0)
    return t_maps_new


'''
returns two solutions for a periodic fodo, given the mean beta
initial betas are at the center of the focusing quad 
'''
def fodo_parameters(betaXmean=36.0, L=10.0, verbose = False):
    lquad = 0.001
        
    kap1 = np.sqrt (1.0/2.0 * ((betaXmean/L)*(betaXmean/L) + (betaXmean/L) * np.sqrt(-4.0 + (betaXmean/L)*(betaXmean/L))))
    kap2 = np.sqrt (1.0/2.0 * ((betaXmean/L)*(betaXmean/L) - (betaXmean/L) * np.sqrt(-4.0 + (betaXmean/L)*(betaXmean/L))))
    
    k = 1.0 / (lquad * L * kap2)
    
    f = 1.0 / (k*lquad)
    
    kappa = f / L    
    betaMax = np.array(( L * kap1*(kap1+1)/np.sqrt(kap1*kap1-1), L * kap2*(kap2+1)/np.sqrt(kap2*kap2-1)))
    betaMin = np.array(( L * kap1*(kap1-1)/np.sqrt(kap1*kap1-1), L * kap2*(kap2-1)/np.sqrt(kap2*kap2-1)))
    betaMean = np.array(( L * kap2*kap2 / (np.sqrt(kap2*kap2 - 1.0)),  L * kap1*kap1 / (np.sqrt(kap1*kap1 - 1.0)) ))
    k = np.array((1.0 / (lquad * L * kap1), 1.0 / (lquad * L * kap2) ))
    
    if verbose:
        print('********* calculating fodo parameters *********')
        print('fodo parameters:')
        print('k*l=', k*lquad)
        print('f=', L * kap1, L*kap2)
        print('kap1=', kap1)
        print('kap2=', kap2)
        print('betaMax=', betaMax)
        print('betaMin=', betaMin)
        print('betaMean=', betaMean)
        print('*********                             *********')
    
    return k*lquad, betaMin, betaMax, betaMean
