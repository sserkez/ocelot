"""
definition of magnetic lattice
linear dimensions in [m]
"""
from ocelot.cpbd.field_map import FieldMap
#from ocelot.cpbd.optics import create_transfer_map
#from ocelot.common.globals import *
import numpy as np
from numpy import pi


class Element:
    """
    Element is a basic beamline building element
    Accelerator optics elements are subclasses of Element
    Arbitrary set of additional parameters can be attached if necessary
    """
    def __init__(self, eid=None):
        self.id = eid
        if eid is None:
            self.id = "ID_{0}_".format(np.random.randint(100000000))
        self.l = 0.
        self.tilt = 0.  # rad, pi/4 to turn positive quad into negative skew
        self.angle = 0.
        self.k1 = 0.
        self.k2 = 0.
        self.dx = 0.
        self.dy = 0.
        self.dtilt = 0.
        self.params = {}
    
    def __hash__(self):
        return hash(id(self))
        #return hash((self.id, self.__class__))

    def __eq__(self, other):
        try:
            #return (self.id, type) == (other.id, type)
            return id(self) == id(other)
        except:
            return False
    

# to mark locations of bpms and other diagnostics
class Monitor(Element):
        
    def __init__(self, l=0.0, eid=None):
        Element.__init__(self, eid)
        self.l = l
        self.x_ref = 0.
        self.y_ref = 0.
        self.x = 0.
        self.y = 0.


class Marker(Element):
    def __init__(self, eid=None):
        Element.__init__(self, eid)
        self.l = 0.


class Quadrupole(Element):
    """
    l - length of lens in [m],
    k1 - strength of quadrupole lens in [1/m^2],
    k2 - strength of sextupole lens in [1/m^3],
    tilt - tilt of lens in [rad].
    """
    def __init__(self, l=0., k1=0, k2=0., tilt=0., eid=None):
        Element.__init__(self, eid)
        self.l = l
        self.k1 = k1
        self.k2 = k2
        self.tilt = tilt


class Sextupole(Element):
    """
    l - length of lens in [m],
    k2 - strength of sextupole lens in [1/m^3].
    """
    def __init__(self, l=0., k2=0., eid=None, tilt=0.):
        Element.__init__(self, eid)
        self.l = l
        self.k2 = k2
        self.tilt = tilt


class Octupole(Element):
    """
    k3 - strength of sextupole lens in [1/m^4],
    l - length of lens in [m].
    """
    def __init__(self, l=0., k3=0., eid=None, tilt=0.):
        Element.__init__(self, eid)
        self.l = l
        self.k3 = k3
        self.tilt = tilt


class Drift(Element):
    """
    l - length of drift in [m]
    """
    def __init__(self, l=0., eid=None):
        Element.__init__(self, eid)
        self.l = l


class Bend(Element):
    """
    bending magnet
    l - length of magnet in [m],
    angle - angle of bend in [rad],
    k1 - strength of quadrupole lens in [1/m^2],
    k2 - strength of sextupole lens in [1/m^3],
    tilt - tilt of lens in [rad],
    e1 - entrance angle with regards to a sector magnet in [rad],
    e2 - exit angle with regards to a sector magnet [rad].
    """
    def __init__(self, l=0., angle=0., k1=0., k2=0., tilt=0.0, e1=0., e2=0.,
                 gap=0., h_pole1=0., h_pole2=0., fint=0., fintx=0., eid=None):
        Element.__init__(self, eid)
        self.l = l
        self.angle = angle
        self.k1 = k1
        self.k2 = k2
        self.e1 = e1
        self.e2 = e2
        self.gap = gap
        self.h_pole1 = h_pole1
        self.h_pole2 = h_pole2
        self.fint1 = fint
        self.fint2 = fint
        if fintx > 0:
            self.fint2 = fintx
        self.tilt = tilt


class Edge(Bend):
    def __init__(self, l=0., angle=0.0, k1=0., edge=0.,
                 tilt=0.0, dtilt=0.0, dx=0.0, dy=0.0,
                 h_pole=0., gap=0., fint=0., pos=1, eid=None):
        Element.__init__(self, eid)
        if l != 0.:
            self.h = angle/l
        else:
            self.h = 0
        self.l = 0.
        self.k1 = k1
        self.h_pole = h_pole
        self.gap = gap
        self.fint = fint
        self.edge = edge
        self.dx = dx
        self.dy = dy
        self.dtilt = dtilt
        self.tilt = tilt
        self.pos = pos


class SBend(Bend):
    """
    sector bending magnet,
    l - length of magnet in [m],
    angle - angle of bend in [rad],
    k1 - strength of quadrupole lens in [1/m^2],
    k2 - strength of sextupole lens in [1/m^3],
    tilt - tilt of lens in [rad],
    e1 - entrance angle in [rad],
    e2 - exit angle in magnet [rad].
    """
    def __init__(self, l=0., angle=0.0, k1=0.0, k2=0., e1=0.0, e2=0.0, tilt=0.0,
                 gap=0, h_pole1=0., h_pole2=0., fint=0., fintx=0., eid=None):

        Bend.__init__(self, l=l, angle=angle, k1=k1, k2=k2, e1=e1, e2=e2, tilt=tilt,
                      gap=gap, h_pole1=h_pole1, h_pole2=h_pole2, fint=fint, eid=eid)

        self.fint1 = fint
        self.fint2 = fint
        if fintx > 0:
            self.fint2 = fintx


class RBend(Bend):
    """
    rectangular bending magnet,
    l - length of magnet in [m],
    angle - angle of bend in [rad],
    k1 - strength of quadrupole lens in [1/m^2],
    k2 - strength of sextupole lens in [1/m^3],
    tilt - tilt of lens in [rad],
    e1 - entrance angle in [rad],
    e2 - exit angle in [rad].
    """
    def __init__(self, l=0., angle=0., tilt=0, k1=0., k2=0.,  e1=None, e2=None,
                 gap=0, h_pole1=0., h_pole2=0., fint=0., fintx=0., eid=None):
        if e1 == None:
            e1 = angle/2.
        else:
            e1 += angle/2.
        if e2 == None:
            e2 = angle/2.
        else:
            e2 += angle/2.

        Bend.__init__(self, l=l, angle=angle, e1=e1, e2=e2, k1=k1, k2=k2, tilt=tilt,
                      gap=gap, h_pole1=h_pole1, h_pole2=h_pole2, fint=fint, fintx=fintx, eid=eid)

        self.fint1 = fint
        self.fint2 = fint
        if fintx > 0:
            self.fint2 = fintx

class Hcor(RBend):
    """
    horizontal corrector,
    l - length of magnet in [m],
    angle - angle of bend in [rad],
    """
    def __init__(self, l=0., angle=0., eid=None):
        RBend.__init__(self, l=l, angle=angle, eid=eid)
        self.l = l
        self.angle = angle
        self.tilt = 0.


class Vcor(RBend):
    """
    horizontal corrector,
    l - length of magnet in [m],
    angle - angle of bend in [rad],
    """
    def __init__(self, l=0., angle=0., eid=None):
        RBend.__init__(self, l=l, angle=angle, eid=eid)
        self.l = l
        self.angle = angle
        self.tilt = pi/2.


class Undulator(Element):
    """
    Undulator
    lperiod - undulator period in [m];\n
    nperiod - number of periods;\n
    Kx - undulator paramenter for vertical field; \n
    Ky - undulator parameter for horizantal field;\n
    field_file_path - absolute path to magnetic field data;\n
    eid - id of undulator.
    """
    def __init__(self, lperiod=0., nperiods=0, Kx=0., Ky=0., field_file=None, eid=None):
        Element.__init__(self, eid)
        self.lperiod = lperiod
        self.nperiods = nperiods
        self.l = lperiod * nperiods
        self.Kx = Kx
        self.Ky = Ky
        self.solver = "linear"  # can be "lin" is liear matrix,  "sym" - symplectic method and "rk" is Runge-Kutta
        self.phase = 0.  # phase between Bx and By + pi/4 (spiral undulator)
        
        self.ax = -1              # width of undulator, when ax is negative undulator width is infinite
                                  # I need it for analytic description of undulator 
        
        self.field_file = field_file
        self.field_map = FieldMap(self.field_file)
        self.v_angle = 0.
        self.h_angle = 0.
        #self.processing()  # here we can check all data and here we can load magnetic map from file
                            # and if error will appear then it will be on stage of forming structure
                            # more over I suggest to store all data (including field map) in this class
                            
    def validate(self):
        pass
                            
        # maybe we will do two functions
        # 1. load data and check magnetic map
        # 2. check all input data (lperiod nperiod ...). domething like this we must do for all elements.

        # what do you think about ending poles? We can do several options
        # a) 1/2,-1,1,... -1,1/2
        # b) 1/2,-1,1,... -1,1,-1/2
        # c) 1/4,-3/4,1,-1... -1,3/4,-1/4   I need to check it.


class Cavity(Element):
    """
    RF cavity
    v - voltage [GV/m]
    f - frequency [Hz]
    phi - phase in [grad]
    """
    def __init__(self, l=0., delta_e=0.0, freq=0.0, phi=0.0, eid=None, v=0., volterr=0.):
        Element.__init__(self, eid)
        self.l = l
        self.v = v   # in GV
        self.delta_e = delta_e
        self.f = freq   # Hz
        self.phi = phi  # in grad # *np.pi/180.
        self.E = 0
        self.volterr = volterr


class Solenoid(Element):
    """
    Solenoid
    l - length in m,
    k - strength B0/(2B*rho)
    """
    def __init__(self, l=0., k=0., eid=None):
        Element.__init__(self, eid)
        self.k = k  # B0/(2B*rho)
        self.l = l


class Multipole(Element):
    """
    kn - list of strengths
    """
    def __init__(self, kn=0., eid=None):
        Element.__init__(self, eid)
        kn = np.array([kn]).flatten()
        if len(kn) < 2:
            self.kn = np.append(kn, [0.])
        else:
            self.kn = kn
        self.n = len(self.kn)
        self.l = 0.


class Matrix(Element):
    def __init__(self, l=0.,
                 rm11=0., rm12=0., rm13=0., rm14=0.,
                 rm21=0., rm22=0., rm23=0., rm24=0.,
                 rm31=0., rm32=0., rm33=0., rm34=0.,
                 rm41=0., rm42=0., rm43=0., rm44=0.,
                 eid=None):
        Element.__init__(self, eid)
        self.l = l
        self.rm11 = rm11
        self.rm12 = rm12
        self.rm13 = rm13
        self.rm14 = rm14

        self.rm21 = rm21
        self.rm22 = rm22
        self.rm23 = rm23
        self.rm24 = rm24

        self.rm31 = rm31
        self.rm32 = rm32
        self.rm33 = rm33
        self.rm34 = rm34

        self.rm41 = rm41
        self.rm42 = rm42
        self.rm43 = rm43
        self.rm44 = rm44


class Pulse:
    def __init__(self):
        self.kick_x = lambda tau: 0.0
        self.kick_y = lambda tau: 0.0
        self.kick_z = lambda tau: 0.0


class UnknownElement(Element):
    """
    l - length of lens in [m]
    """
    def __init__(self, l=0, kick=0, xsize=0, ysize=0, volt=0, lag=0, harmon=0, refer=0, vkick=0, hkick=0, eid=None):
        Element.__init__(self, eid)
        self.l = l


class Sequence:
    def __init__(self, l=0, refer=0):
        self.l = l


def survey(lat, ang=0.0, x0=0, z0=0):
    x = []
    z = []
    for e in lat.sequence:
        x.append(x0)
        z.append(z0)
        if e.__class__ in [Bend, SBend, RBend]:
            ang += e.angle
        x0 += e.l*cos(ang)  
        z0 += e.l*sin(ang)
    return x, z, ang

if __name__ == "__main__":
    a = RBend(l=13)