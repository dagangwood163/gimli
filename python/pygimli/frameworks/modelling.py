# -*- coding: utf-8 -*-
"""pyGIMLi - Inversion Frameworks.

These are basic modelling proxies.
"""
import numpy as np

from copy import copy

import pygimli as pg

DEFAULT_STYLES={'Default': {'color': 'C0', 
                           'lw' : 1.5, 'linestyle': '-'},
                'Data': {'color' : 'C0', #blueish
                        'lw'  : 1, 'linestyle' : ':',
                        'marker' : 'o'},
                'Response': {'color': 'C0', #blueish
                            'lw': 1.5, 'linestyle' : '-', 
                            'marker' : 'None'},
                'Error': {'color': 'C3',  #reddish
                          'lw': 0, 'linestyle' : '-', 
                          'elinewidth': 2, 'alpha' : 0.5},
                }


class Modelling(pg.ModellingBase):
    """Abstract Forward Operator.

    Abstract Forward Operator that is or can use a Modelling instance.
    Can be seen as some kind of proxy Forward Operator.

    TODO: 
        * Modelling or Modeling?
        * Docu:
            - describe members (model transformation, dictionary of region properties)
            - 
        * think about splitting all mes related into MeshModelling
        * clarify difference: setData(array|DC), setDataContainer(DC), setDataValues(array)
        * clarify dataSpace(comp. ModelSpace): The unique spatial or temporal origin of a datapoint (time, coordinates, 4-point-positions,
                                                                     receiver/transmitter positions
                                                                     counter)
            - Every inversion needs, dataValues and dataSpace
            - DataContainer contain, dataValues and dataSpace
            - initialize both with initDataSpace(), initModelSpace
        * createJacobian should also return J
    """
    def __init__(self, **kwargs):
        """
        Parameters
        ----------
        **kwargs :
            fop : Modelling

        """
        fop = kwargs.pop('fop', None)
        super(Modelling, self).__init__(**kwargs)

        self._regionProperties = {}
        self._regionsNeedUpdate = False
        self._modelTrans = pg.RTransLog() # Model transformation operator

        self.fop = None
        self.data = None # dataContainer

        if fop is not None:
            self.setForwardOperator(fop)

    @property
    def modelTrans(self):
        self._applyRegionProperties()
        if self.regionManager().haveLocalTrans():
            return self.regionManager().transModel()
        return self._modelTrans

    @modelTrans.setter
    def modelTrans(self, tm):
        self._modelTrans = tm

    def initModelSpace(self, **kwargs):
        """API"""    
        pass
        
    def createStartModel(self, dataVals=None):
        """Create starting model.

        Create starting model based on current data values and additional args.

        TODO

            * Howto ensure childs sets self.setStartModel(sm)?

        """
        sm = self.regionManager().createStartModel()
        return sm

    def regionManager(self):
        """
        """
        ### initialize RM if necessary
        super(Modelling, self).regionManager()

        ### set all local properties
        self._applyRegionProperties()
        return super(Modelling, self).regionManager()

    def setForwardOperator(self, fop):
        """ 
        """
        if not isinstance(fop, pg.frameworks.Modelling):
            pg.critical('Forward operator needs to be an instance of '
                        'pg.modelling.Modelling but is of type:', fop)

        self.fop = fop
        
    def setMesh(self, mesh, ignoreRegionManager=False):
        """ 
        """
        self.clearRegionProperties()

        if self.fop is not None:
            self.fop.setMesh(mesh, ignoreRegionManager)
            
            if not ignoreRegionManager:
                self.setRegionManager(self.fop.regionManagerRef())
        else:
            super(Modelling, self).setMesh(mesh, ignoreRegionManager)

    def clearRegionProperties(self):
        """Clear all region parameter."""
        self._regionProperties = {}

    def regionProperties(self, regionNr=None):
        """Return dictionary of all properties for region number regionNr."""
        if regionNr is None:
            return self._regionProperties

        try:
            return self._regionProperties[regionNr]
        except:
            print(self._regionProperties)
            pg.error("no region for regionNr:", regionNr)

    def setRegionProperties(self, regionNr, **kwargs):
        """ Set region properties. regionNr can be wildcard '*' for all regions.

                            startModel=None, limits=None, trans=None,
                            cType=None, zWeight=None, modelControl=None,
                            background=None, single=None, fix=None):
        Parameters
        ----------

        """
        if regionNr is '*':
            for regionNr in self.regionManager().regionIdxs():
                self.setRegionProperties(regionNr, **kwargs)
            return

        if regionNr not in self._regionProperties:
            self._regionProperties[regionNr] = {'startModel': None,
                                                'modelControl': 1.0,
                                                'zWeight': 1.0,
                                                'cType': 1,
                                                'limits': [0, 0],
                                                'trans': 'Log',
                                                'background': None,
                                                'single': None,
                                                'fix': None,
                                              }
        
        for key, val in kwargs.items():
            if val is not None:
                if not self._regionProperties[regionNr][key] is val:
                    self._regionsNeedUpdate = True
                    self._regionProperties[regionNr][key] = val

    def _applyRegionProperties(self):
        """
        """
        if not self._regionsNeedUpdate:
            return 

        ### call super class her because self.regionManager() calls always 
        ###  __applyRegionProperies itself
        rMgr = super(Modelling, self).regionManager()
        for rID, vals in self._regionProperties.items():

            if vals['background'] is not None:
                pg.critical('implementme')
                continue

            if vals['single'] is not None:
                pg.critical('implementme')
                continue

            if vals['fix'] is not None:
                pg.critical('implementme')
                continue

            if vals['startModel'] is not None:
                rMgr.region(rID).setStartModel(vals['startModel'])

            rMgr.region(rID).setModelTransStr_(vals['trans'])
            rMgr.region(rID).setConstraintType(vals['cType'])
            rMgr.region(rID).setZWeight(vals['zWeight'])
            rMgr.region(rID).setModelControl(vals['modelControl'])

            if vals['limits'][0] > 0:
                rMgr.region(rID).setLowerBound(vals['limits'][0])

            if vals['limits'][1] > 0:
                rMgr.region(rID).setUpperBound(vals['limits'][1])

        self._regionsNeedUpdate = False

    def setData(self, data):
        """ 
        """
        if isinstance(data, pg.DataContainer):
            self.setDataContainer(data)
        else:
            print(data)
            pg.critical("nothing known to do? Implement me in derived classes")
        
    def setDataSpace(self, **kwargs):
        """Set data space, e.g., DataContainer, times, coordinates."""
        if self.fop is not None:
            self.fop.setDataSpace(**kwargs)
        else:
            data = kwargs.pop('dataContainer', None)
            if isinstance(data, pg.DataContainer):
                self.setDataContainer(data)
            else:
                print(data)
                pg.critical("nothing known to do? Implement me in derived classes")

    def setDataContainer(self, data):
        """ 
        """
        if self.fop is not None:
            self.fop.setData(data)
        else:
            super(Modelling, self).setData(data)
            self.data = data

    def estimateError(self, data, **kwargs):
        """Create data error fallback when the data error is not known. 
            Should be implemented method depending.
        """
        raise Exception("Needed?? Implement me in derived classes")
        #data = data * (pg.randn(len(data)) * errPerc / 100. + 1.)
        #return data

    def drawModel(self, ax, model, **kwargs):
        """
        """
        if self.fop is not None:
            self.fop.drawModel(ax, model, **kwargs)
        else:
            print(kwargs)
            raise Exception("No yet implemented")

    def drawData(self, ax, data, **kwargs):
        """
        """
        if self.fop is not None:
            self.fop.drawData(ax, data, **kwargs)
        else:
            print(kwargs)
            raise Exception("No yet implemented")


class Block1DModelling(Modelling):
    """General forward operator for 1D layered models.

    Find the data space for the model space [thickness_i, parameter_jk], 
    with i = 0 - nLayers-1, j = (0 .. nLayers), k=(0 .. nPara)
    """
    def __init__(self, nPara=1, **kwargs):
        """Constructor

        Parameters
        ----------
        * nPara : int [1]
            Number of parameters per layer. e.g.: 2 for resistivity and phase.
            While the number of parameter is defined by the physics yout want 
            to simulate, nPara need to be set from the derived class and 
            cannot be changed in runtime.
        """
        super(Block1DModelling, self).__init__(**kwargs)
        self._withMultiThread = True
        self._nPara = nPara # number of parameters per layer

        # store this to avoid reinitialization if not needed
        self._nLayers = 0 

    @property
    def nLayers(self):
        return self._nLayers

    def initModelSpace(self, nLayers):
        
        """Set number of layers for the 1D block model"""
        if nLayers == self._nLayers:
            return;

        if nLayers < 2:
            pg.critical("Number of layers need to be at least 2")

        self._nLayers = nLayers

        mesh = pg.createMesh1DBlock(nLayers, self._nPara)
        self.setMesh(mesh)
        
        for i in range(self._nPara + 1):
            self.setRegionProperties(i, trans='log')
            
        if self._withMultiThread:
            self.setMultiThreadJacobian(2*nLayers - 1)

        self._applyRegionProperties()

        
    def drawModel(self, ax, model, **kwargs):
        pg.mplviewer.drawModel1D(ax=ax,
                                 model=model,
                                 plot='loglog',
                                 xlabel=kwargs.pop('xlabel', 'Model parameter'),
                                 **kwargs)
        return ax

    def drawData(self, ax, data, err=None, label=None, **kwargs):
        r"""Default data view.
        
        Probably ugly and you should overwrite it in your derived forward 
        operator. 
        """
        nData = len(data)
        yVals = range(nData)
        ax.loglog(data, yVals, 'x-', 
                  label=label,
                  **DEFAULT_STYLES.get(label, DEFAULT_STYLES['Default'])
                  )

        if err is not None:
            ax.errorbar(data, yVals,
                        xerr=err*data,
                        label='Error',
                        **DEFAULT_STYLES.get('Error', DEFAULT_STYLES['Default'])
                        )

        ax.set_ylim(max(yVals), min(yVals))
        ax.set_xlabel('Data')
        ax.set_ylabel('Data Number')
        return ax


class MeshModelling(Modelling):
    """
    """
    def __init__(self, **kwargs):
        super(MeshModelling, self).__init__(**kwargs)

    @property
    def paraDomain(self):
        return self.regionManager().paraDomain()

    # def setMesh(self, mesh, ignoreRegionManager=False):

    #     super(MeshModelling, self).setMesh(mesh, ignoreRegionManager)

    def drawModel(self, ax, model, **kwargs):
        pg.mplviewer.drawModel(ax=ax,
                               mesh=self.paraDomain,
                               data=model,
                               **kwargs)
        return ax


class PetroModelling(Modelling):
    """Combine petrophysical relation with the modeling class f(p).

    Combine petrophysical relation :math:`p(m)` with a modeling class 
    :math:`f(p)` to invert for the petrophysical model :math:`p` instead 
    of the geophysical model :math:`m`.

    :math:`p` be the petrophysical model, e.g., porosity, saturation, ...
    :math:`m` be the geophysical model, e.g., slowness, resistivity, ...
    
    """
    def __init__(self, fop, trans, **kwargs):
        """Save forward class and transformation, create Jacobian matrix."""
        mesh = kwargs.pop('mesh', None)

        super(PetroModelling, self).__init__(fop=fop, **kwargs)
        # petroTrans.fwd(): p(m), petroTrans.inv(): m(p)
        self._petroTrans = trans  # class defining p(m)

        self._jac = pg.MultRightMatrix(self.fop.jacobian())
        self.setJacobian(self._jac)
       
    def createStartModel(self, data):
        """Use inverse transformation to get m(p) for the starting model."""
        sm = self.fop.createStartModel(data)
        pModel = self._petroTrans.inv(sm)
        return pModel
        
    def response(self, model):
        """Use transformation to get p(m) and compute response f(p)."""
        tModel = self._petroTrans(model)
        ret = self.fop.response(tModel)
        return ret

    def createJacobian(self, model):
        """Fill the individual jacobian matrices."""
        tModel = self._petroTrans(model)
        self.fop.createJacobian(tModel)
        self._jac.r = self._petroTrans.deriv(model)  # set inner derivative


class LCModelling(Modelling):
    """2D Laterally constrained (LC) modelling.

    2D Laterally constrained (LC) modelling based on BlockMatrices.
    """
    def __init__(self, fop, **kwargs):
        """Parameters: fop class ."""

        super(LCModelling, self).__init__()

        self._singleRegion = False

        self._fopTemplate = fop
        self._fopKwargs = kwargs
        self._fops1D = []
        self._mesh = None
        self._nSoundings = 0
        self._parPerSounding = 0
        self._jac = None

        self.soundingPos = None

    def setDataBasis(self, **kwargs):
        """Set homogeneous data basis.

        Set a common data basis to all forward operators.
        If you want individual you need to set them manually.
        """
        for f in self._fops1D:
            f.setDataBasis(**kwargs)

    def initModelSpace(self, nLayers):
        for i, f in enumerate(self._fops1D):
            f.initModelSpace(nLayers)

    def createStartModel(self, models):
        sm = pg.RVector()
        for i, f in enumerate(self._fops1D):
            sm = pg.cat(sm, f.createStartModel(models[i]))
        return sm

    def response(self, par):
        """Cut together forward responses of all soundings."""
        mods = np.asarray(par).reshape(self._nSoundings, self._parPerSounding)

        resp = pg.RVector(0)
        for i in range(self._nSoundings):
            r = self._fops1D[i].response(mods[i])
            #print("i:", i, mods[i], r)
            resp = pg.cat(resp, r)

        return resp

    def createJacobian(self, par):
        """Create Jacobian matrix by creating individual Jacobians."""
        mods = np.asarray(par).reshape(self._nSoundings, self._parPerSounding)

        for i in range(self._nSoundings):
            self._fops1D[i].createJacobian(mods[i])

    def createParametrization(self, nSoundings, nLayers=4, nPar=1):
        """Create LCI mesh and suitable constraints informations.

        Parameters
        ----------
        nLayers : int
            Numbers of depth layers

        nSoundings : int
            Numbers of 1D measurements to laterally constrain

        nPar : int
            Numbers of independent parameter types,
            e.g., nPar = 1 for VES (invert for resisitivies),
            nPar = 2 for VESC (invert for resisitivies and phases)
        """
        nCols = (nPar+1) * nLayers - 1 ## fail for VES-C
        self._parPerSounding = nCols
        self._nSoundings = nSoundings

        self._mesh = pg.createMesh2D(range(nCols + 1),
                                     range(nSoundings + 1))
        self._mesh.rotate(pg.RVector3(0, 0, -np.pi/2))

        cm = np.ones(nCols * nSoundings) * 1

        if not self._singleRegion:
            for i in range(nSoundings):
                for j in range(nPar):
                    cm[i * self._parPerSounding + (j+1) * nLayers-1 :
                       i * self._parPerSounding + (j+2) * nLayers-1] += (j+1)

        self._mesh.setCellMarkers(cm)
        self.setMesh(self._mesh)

        pID = self.regionManager().paraDomain().cellMarkers()
        cID = [c.id() for c in self._mesh.cells()]
        #print(np.array(pID))
        #print(np.array(cID))
        #print(self.regionManager().parameterCount())
        perm = [0]*self.regionManager().parameterCount()
        for i in range(len(perm)):
            perm[pID[i]] = cID[i]

        #print(perm)
        self.regionManager().permuteParameterMarker(perm)
        #print(self.regionManager().paraDomain().cellMarkers())

    def initJacobian(self, dataVals, nLayers, nPar=None):
        """
        Parameters
        ----------
        dataVals : ndarray | RMatrix | list
            Data values of size (nSounding x Data per sounding).
            All data per sounding need to be equal in length.
            If they don't fit into a matrix use list of sounding data.
        """

        nSoundings = len(dataVals)

        if nPar is None:
            #TODO get nPar Infos from fop._fopTemplate
            nPar = 1

        self.createParametrization(nSoundings, nLayers=nLayers, nPar=nPar)

        if self._jac is not None:
            self._jac.clear()
        else:
            self._jac = pg.BlockMatrix()

        self.fops1D = []
        nData = 0

        for i in range(nSoundings):
            kwargs = {}
            for key, val in self._fopKwargs.items():
                if hasattr(val, '__iter__'):
                    if len(val) == nSoundings:
                        kwargs[key] = val[i]
                else:
                    kwargs[key] = val

            f = None
            if issubclass(self._fopTemplate, pg.frameworks.Modelling):
                f = self._fopTemplate(**kwargs)
            else:
                f = type(self._fopTemplate)(self.verbose, **kwargs)

            f.setMultiThreadJacobian(self._parPerSounding)

            self._fops1D.append(f)

            nID = self._jac.addMatrix(f.jacobian())
            self._jac.addMatrixEntry(nID, nData, self._parPerSounding * i)
            nData += len(dataVals[i])

        self._jac.recalcMatrixSize()
        #print("Jacobian size:", self.J.rows(), self.J.cols(), nData)
        self.setJacobian(self._jac)

    def drawModel(self, ax, model, **kwargs):
        mods = np.asarray(model).reshape(self._nSoundings,
                                         self._parPerSounding)
        nPar = 1
        pg.mplviewer.showStitchedModels(mods, ax=ax, useMesh=True,
                                        x=self.soundingPos,
                                        **kwargs)
