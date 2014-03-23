# -*- coding: utf-8 -*-
"""
Created on Fri Nov 08 19:52:40 2013
The binary or linear optimizer that is the basic building block for 
solving machine learning problems
@author: xm
"""
import base
from crane import mantisStore
from ..math.svm_solver_dual import SVMDual
from ..math.flexible_vector import FlexibleVector
import logging
logger = logging.getLogger("monk.mantis")

class Mantis(base.MONKObject):

    def __restore__(self):
        super(Mantis, self).__restore__()
        if "eps" not in self.__dict__:
            self.eps = 1e-4
        if "Cp" not in self.__dict__:
            self.Cp = 1
        if "Cn" not in self.__dict__:
            self.Cn = 1
        if "lam" not in self.__dict__:
            self.lam = 1
        if "rho" not in self.__dict__:
            self.rho = 1
        if "max_num_iters" not in self.__dict__:
            self.max_num_iters = 1000
        if "max_num_instances" not in self.__dict__:
            self.max_num_instances = 1000
        if "max_num_partitions" not in self.__dict__:
            self.max_num_partitions = 100
        if "panda" not in self.__dict__:
            self.panda = None
        self.solvers = {}

    def __defaults__(self):
        super(Mantis, self).__defaults__()
        self.panda = None
        self.eps = 1e-4
        self.Cp = 1
        self.Cn = 1
        self.lam = 1
        self.rho = 1
        self.max_num_iters = 1000
        self.max_num_instances = 1000
        self.max_num_partitions = 100
        self.solvers = {}

    def generic(self):
        result = super(Mantis, self).generic()
        # every mantis should have a panda
        result['panda'] = self.panda._id
        try:
            del result['solvers']
        except Exception as e:
            logger.warning('deleting solvers failed {0}'.format(e.message))
        return result

    def get_solver(self, partition_id):
        try:
            return self.solvers[partition_id]
        except KeyError:
            logger.info('no solver found for {0}'.format(partition_id))
            return None

    def train_one(self, partition_id):
        solver = self.get_solver(partition_id)
        if solver:
            consensus = self.panda.update_consensus()
            solver.setModel(consensus)
            solver.trainModel()
    
    def add_data(self, partition_id, x, y, c):
        solver = self.get_solver(partition_id)
        if solver:
            solver.setData(x,y)
    
    def aggregate(self, partition_id):
        # @todo: incremental aggregation
        # @todo: ADMM aggregation
        consensus = self.panda.consensus
        t = len(self.panda.weights)
        if self.panda.weights.has_key(partition_id):
            w = self.panda.weights[partition_id]
        else:
            w = consensus
            t += 1
        consensus.add(w, -1/t)
        w = self.panda.update_one_weight(partition_id)
        consensus.add(w, 1/t)
        
    def add_one(self, partition_id):
        w = self.panda.get_model(partition_id)
        self.solvers[partition_id] = SVMDual(w, self.eps, self.lam, self.Cp, self.Cn,
                                             self.rho, self.max_num_iters,
                                             self.max_num_instances)
    
    def load_one(self, partition_id):
        if not self.solvers.has_key(partition_id):
            fields = ['solvers.{0}'.format(partition_id)]
            s = mantisStore.load_one_in_fields(self, fields)
            if s.has_key('solvers'):
                self.solvers[partition_id] = SVMDual(s['solvers'][partition_id])
            else:
                logger.error('can not find solver for {0}'.format(partition_id))
        else:
            logger.warning('solver for {0} already exists'.format(partition_id))
            
    def save_one(self, partition_id):
        if self.solvers.has_key(partition_id):
            mantisStore.update_one_in_fields(self, {'solvers.{0}'.format(partition_id):self.solvers[partition_id].generic()})
        else:
            logger.warning('can not find solver for {0} to save'.format(partition_id))
            
base.register(Mantis)
