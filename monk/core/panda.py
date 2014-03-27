# -*- coding: utf-8 -*-
"""
Created on Fri Nov 08 19:51:53 2013
The basic executor of the machine learning building block, 
i.e., a binary classifier or a linear regressor
@author: xm
"""
from ..math.flexible_vector import FlexibleVector
from ..math.cmath import sigmoid
import base, crane
from mantis import Mantis
import logging
logger = logging.getLogger('monk.panda')

class Panda(base.MONKObject):

    def __restore__(self):
        super(Panda, self).__restore__()
        if "uid" not in self.__dict__:
            self.uid = crane.uidStore.nextUID()
        if "name" not in self.__dict__:
            logger.warning('no name is specified, using default')
            self.name = 'Var' + str(self.uid)

    def save(self, **kwargs):
        crane.pandaStore.update_one_in_fields(self, self.generic())
        
    def has_mantis():
        return False
    
    def add_features(self, uids):
        pass
    
    def add_one(self, partition_id):
        pass
    
    def load_one(self, partition_id):
        return True
    
    def save_one(self, partition_id):
        return True
    
    def train_one(self, partition_id):
        pass
    
    def predict(self, partition_id, entity):
        return 0

    def get_model(self, partition_id):
        return None


class ExistPanda(Panda):

    def predict(self, partition_id, entity):
        def extract(x, y):
            try:
                if entity[y].find(self.name) >= 0:
                    return x + 1
                else:
                    return x
            except:
                return x
        return reduce(extract, entity.iterkeys(), 0)

class RegexPanda(Panda):

    def predict(self, partition_id, entity):
        pass

class LinearPanda(Panda):

    def __restore__(self):
        super(LinearPanda, self).__restore__()
        self.weights = {}
        if "consensus" not in self.__dict__:
            self.consensus = FlexibleVector()
        else:
            self.consensus = FlexibleVector(generic=self.consensus)

        if "mantis" not in self.__dict__:
            self.mantis = Mantis()
        else:
            self.mantis = crane.mantisStore.load_or_create(self.mantis)

        self.mantis.panda = self

    def generic(self):
        result = super(LinearPanda, self).generic()
        # @error: problematic when saving, only works on updating
        result['consensus'] = self.consensus.generic()
        result['mantis'] = self.mantis._id
        del result['weights']
        return result
    
    def save(self, **kwargs):
        crane.pandaStore.update_one_in_fields(self, self.generic())
        self.mantis.save()
            
    def has_mantis(self):
        return True
    
    def add_features(self, uids):
        self.consensus.addKeys(uids)
        
    def add_one(self, partition_id):
        field = 'weights.{0}'.format(partition_id)
        if partition_id in self.weights or crane.pandaStore.exists_field(self, field):
            logger.warning('partition {0} already exists'.format(partition_id))
            return False
        
        self.weights[partition_id] = self.consensus.clone()
        return self.mantis.add_one(partition_id)

    def update_one_weight(self, partition_id):
        field = 'weights.{0}'.format(partition_id)
        pa = crane.pandaStore.load_one_in_fields(self, [field])
        w = self.weights[partition_id]
        if 'weights' in pa:
            w.update(pa['weights'][partition_id])
        return w
    
    def update_consensus(self):
        pa = crane.pandaStore.load_one_in_fields(self,['consensus'])
        if 'consensus' in pa:
            self.consensus.update(pa['consensus'])
        return self.consensus
    
    def save_consensus(self):
        crane.pandaStore.update_one_in_fields(self, {'consensus':self.consensus.generic()})
        
    def load_one(self, partition_id):
        if partition_id in self.weights:
            logger.warning('partition {0} already exists'.format(partition_id))
            return False
            
        field = 'weights.{0}'.format(partition_id)
        pa = crane.pandaStore.load_one_in_fields(self, [field])
        try:
            self.weights[partition_id] = FlexibleVector(generic=pa['weights'][partition_id])
        except:
            logger.error('can not find model for partition {0}'.format(partition_id))
            return False
        
        return self.mantis.load_one(partition_id)
        
    def save_one(self, partition_id):
        if partition_id not in self.weights:
            logger.warning('parititon {0} not found to save'.format(partition_id))
            return False
        
        field = 'weights.{0}'.format(partition_id)
        crane.pandaStore.update_one_in_fields(self, {field:self.weights[partition_id].generic()})
        
        return self.mantis.save_one(partition_id)

    def get_model(self, partition_id=None):
        if partition_id is None:
            return self.consensus

        if partition_id in self.weights:
            return self.weights[partition_id]
        else:
            logger.warning('LinearPanda has no model for {0}'.format(partition_id))
            return None
        
    def predict(self, partition_id, entity):
        model = self.get_model(partition_id)
        if model:
            return sigmoid(model.dot(entity._features))
        else:
            return 0

base.register(Panda)
base.register(ExistPanda)
base.register(RegexPanda)
base.register(LinearPanda)
