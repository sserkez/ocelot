from ocelot.gui.accelerator import plot_lattice
from ocelot.cpbd.elements import *
from ocelot.cpbd.beam import *
from ocelot.cpbd.optics import *
from ocelot.cpbd.match import *
from pylab import *

from copy import deepcopy
from scipy.optimize import *

d0 = Drift(l=1.0)
d1 = Drift(l=2.5)
b1 = RBend (l=3.0, angle=0.002, id = "b1")
d2 = Drift(l=0.5)
b2 = RBend (l=3.0, angle=0.002, id = "b2")


q1 = Quadrupole(l=0.1, k1=1.0)
q2 = Quadrupole(l=0.1, k1=-3.0)
q3 = Quadrupole(l=0.1, k1=4.91776965)
q4 = Quadrupole(l=0.1, k1=4.91776965)
q5 = Quadrupole(l=0.1, k1=-3.0)
q6 = Quadrupole(l=0.1, k1=1.0)

m1 = Monitor(id="start")
m2 = Monitor(id="end")

dba = (m1,d0,q1, d2, q2, d1, b1, d2, q3, (d0,)*5, q3, d2, b2, d1, q5, d2, q6,d0,m2)

beam = Beam()
beam.E = 14.0
beam.sigma_E = 0.002
beam.emit_xn = 0.4e-6 
beam.emit_yn = 0.4e-6 
beam.gamma_rel = beam.E / (0.511e-3)
beam.emit_x = beam.emit_xn / beam.gamma_rel
beam.emit_y = beam.emit_yn / beam.gamma_rel
beam.beta_x = 33.7
beam.beta_y = 43.218
beam.alpha_x = 0.1
beam.alpha_y = -0.98



lat = MagneticLattice(dba, energy=3.0)
tw0 = Twiss(beam)
tws=twiss(lat, tw0, nPoints = 1000)



constr = {'end':{'Dx':0.0, 'Dxp':0.0, 'beta_x':55.0, 'beta_y':90.0}, 'start':{'beta_x':15.0, 'beta_y':30.0}}
#constr = {'end':{'Dx':0.0, 'Dxp':0.0}, 'start':{'beta_x':15.0, 'beta_y':30.0}}
#constr = {'end':{'Dx':0.0, 'Dxp':0.0}}


#vars = [q1,q2,q3,q5,q6, [tw0, 'beta_x'], [tw0, 'beta_y']]
vars = [q1,q2,q5,q6, [tw0, 'beta_x'], [tw0, 'beta_y'], [tw0, 'alpha_x'], [tw0, 'alpha_y']]
#vars = [q1,q2,q3,q5,q6, [tw0, 'beta_x'], [tw0, 'beta_y'], [tw0, 'alpha_x'], [tw0, 'alpha_y']]

match(lat, constr, vars, tw0)


tws=twiss(lat, tw0, nPoints = 1000)


f=plt.figure()
ax = f.add_subplot(211)
ax.set_xlim(0, lat.totalLen)

f.canvas.set_window_title('Betas [m]') 
p1, = plt.plot(map(lambda p: p.s, tws), map(lambda p: p.beta_x, tws), lw=2.0)
p2, = plt.plot(map(lambda p: p.s, tws), map(lambda p: p.beta_y, tws), lw=2.0)
plt.grid(True)

ax.twinx()
p3,=plt.plot(map(lambda p: p.s, tws), map(lambda p: p.Dx, tws), 'r',lw=2.0)

plt.legend([p1,p2,p3], [r'$\beta_x$',r'$\beta_y$', r'$D_x$'])

ax2 = f.add_subplot(212)
plot_lattice(lat, ax2, alpha=0.5)

# add beam size (arbitrary scale)

s = np.array(map(lambda p: p.s, tws))

scale = 5000

sig_x = scale * np.array(map(lambda p: np.sqrt(p.beta_x*beam.emit_x), tws)) # 0.03 is for plotting same scale
sig_y = scale * np.array(map(lambda p: np.sqrt(p.beta_y*beam.emit_y), tws))

x = scale * np.array(map(lambda p: p.x, tws))
y = scale * np.array(map(lambda p: p.y, tws))


plt.plot(s, x + sig_x, color='#0000AA', lw=2.0)
plt.plot(s, x-sig_x, color='#0000AA', lw=2.0)

plt.plot(s, sig_y, color='#00AA00', lw=2.0)
plt.plot(s, -sig_y, color='#00AA00', lw=2.0)

#f=plt.figure()
plt.plot(s, x, 'r--', lw=2.0)
#plt.plot(s, y, 'r--', lw=2.0)

plt.show()