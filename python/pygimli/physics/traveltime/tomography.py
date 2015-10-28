import sys
import numpy as np
import matplotlib.pyplot as plt
import pygimli as pg
from . refraction import Refraction


def readTOMfile(filename):
    """ read Reflex tomography (*.TOM) file"""
    t, xT, zT, xR, zR = np.loadtxt(filename, usecols=(0, 2, 3, 4, 5), unpack=1)
    pT = xT - zT * 1j
    pR = xR - zR * 1j
    pU = np.unique(np.hstack((pT, pR)))
    iT = np.array([np.nonzero(pU == pi)[0][0] for pi in pT], dtype=float)
    iR = np.array([np.nonzero(pU == pi)[0][0] for pi in pR], dtype=float)
    data = pg.DataContainer()
    for pp in pU:
        data.createSensor(pg.RVector3(pp.real, pp.imag))

    for tok in ['s', 'g']:
        data.registerSensorIndex(tok)

    data.resize(len(t))
    data.set('t', t)
    data.set('s', iT)
    data.set('g', iR)
    data.markValid(pg.abs(data('s') - data('g')) > 0)
    return data


class Tomography(Refraction):
    """traveltime tomography for tomographic (e.g. crosshole) measurements"""
    def __init__(self, data=None, **kwargs):
        """Init function with optional data load"""
        if isinstance(data, str):
            if data.lower()[-4:] == '.tom':
                data = readTOMfile(data)
            else:
                data = pg.DataContainer(data, 's g')
        super(type(self), self).__init__(data, **kwargs)

    def createMesh(self, quality=34.6, maxarea=0.1, addpoints=[]):
        """Create (inversion) mesh by circumventing PLC"""
        data = self.dataContainer
        sx = list(pg.x(data.sensorPositions()))
        sz = list(pg.y(data.sensorPositions()))
        for po in addpoints:
            sx.append(po[0])
            sz.append(po[1])

        iS = np.argsort(np.arctan2(sx-np.mean(sx), sz-np.mean(sz)))
        plc = pg.Mesh(2)
        nodes = [plc.createNode(sx[i], sz[i], 0) for i in iS]
        [plc.createEdge(nodes[i], nodes[i+1]) for i in range(len(nodes)-1)]
        plc.createEdge(nodes[-1], nodes[0])
        tri = pg.TriangleWrapper(plc)
        tri.setSwitches("-pzFq"+str(quality)+"a"+str(maxarea))
        self.setMesh(tri.generate())

    def offset(self):
        """return shot-geophone distance"""
        data = self.dataContainer
        return np.array([data.sensorPosition(int(data('g')[i])).distance(
                         data.sensorPosition(int(data('s')[i])))
                         for i in range(data.size())])

    def getVA(self):
        """return apparent velocity"""
        return self.offset() / self.dataContainer('t')

    def createStartModel(self, *args, **kwargs):
        """create (gradient) starting model with vtop/vbottom bounds"""
        va = self.getVA()
        nModel = self.fop.regionManager().parameterCount()
        self.start = pg.RVector(nModel, 1./np.mean(va))

    def showVA(self, ax=None, usepos=True):
        """show apparent velocity as image plot"""
        va = self.getVA()
        data = self.dataContainer
        A = np.ones((data.sensorCount(), data.sensorCount())) * np.nan
        for i in range(data.size()):
            A[int(data('s')[i]), int(data('g')[i])] = va[i]

        if ax is None:
            fig, ax = plt.subplots()

        gci = ax.imshow(A, interpolation='nearest')
        ax.grid(True)
        if usepos:
            xt = np.linspace(0, data.sensorCount()-1, 7).round()
            px = pg.abs(pg.y(self.dataContainer.sensorPositions()))
            ax.set_xticks(xt)
            ax.set_xticklabels([str(int(px[int(xti)])) for xti in xt])
            ax.set_yticks(xt)
            ax.set_yticklabels([str(int(px[int(xti)])) for xti in xt])

        plt.colorbar(gci, ax=ax)
        return va


if __name__ == '__main__':
    datafile = sys.argv[1]
    Tomo = Tomography(datafile)
    print(Tomo)
    Tomo.createMesh(addpoints=[[6, -22], [0, -8]])
    Tomo.showVA()
    Tomo.estimateError(absoluteError=0.7, relativeError=0.001)
    Tomo.run()
    Tomo.showResult()
