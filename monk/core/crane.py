# -*- coding: utf-8 -*-
"""
Created on Fri Nov 08 19:51:41 2013
The persistent storage manager that talks to different databases

@author: xm
"""

import pymongo as pm
#@todo: using cache
#from monk.utils.cache import lru_cache
import logging
import base
from bson.objectid import ObjectId
from uid import UID
logger = logging.getLogger("monk.crane")

class Crane(object):

    def __init__(self, database=None, collectionName=None, fields={}):
        if database is None or collectionName is None:
            return
            
        logger.info('initializing {0} '.format(collectionName))
        self._database = database
        self._coll = self._database[collectionName]
        self._fields = fields        
        self._cache = {}

    # cache related operation
    def __get_one(self, key):
        if key in self._cache:
            return self._cache[key]
        else:
            return None

    def __get_all(self, keys):
        objs = [self._cache[key] for key in keys if key in self._cache]
        rems = [key for key in keys if key not in self._cache]
        return objs, rems

    def __put_one(self, obj):
        self._cache[obj._id] = obj

    def __put_all(self, objs):
        map(self.__put_one, objs)

    def __erase_one(self, obj):
        del self._cache[obj._id]

    def __erase_all(self, objs):
        map(self.__erase_one, objs)

    def load_or_create(self, obj):
        if not obj:
            return None
        
        if isinstance(obj, ObjectId):
            return self.load_one_by_id(obj)
        else:
            return self.create_one(obj)

    def load_or_create_all(self, objs):
        if not objs:
            return []
        
        if isinstance(objs[0], ObjectId):
            return self.load_all_by_ids(objs)
        else:
            return self.create_all(objs)
            
    def exists_field(self, obj, field):
        query = {'_id':obj._id, field:{'$exists':True}}
        if self._coll.find_one(query, {'_id':1}):
            return True
        else:
            return False
            
    def exists_fields(self, obj, fields):
        query = {field:{'$exists':True} for field in fields}
        query['_id'] = obj._id
        if self._coll.find_one(query,{'_id':1}):
            return True
        else:
            return False
        
    def update_one_in_fields(self, obj, fields):
        # fields are in flat form
        # 'f1.f2':'v' is ok, 'f1.f3' won't be erased
        # 'f1':{'f2':'v'} is NOT, 'f1':{'f3':vv} will be erased
        try:
            self._coll.update({'_id':obj._id}, {'$set':fields}, upsert=True)
        except Exception as e:
            logger.warning(e.message)
            logger.warning('can not update document {0} in fields {1}'.format(obj._id, fields))
            return False
        return True
    
    def load_one_in_fields(self, obj, fields):
        # fields is a list
        try:
            return self._coll.find_one({'_id':obj._id}, fields)
        except Exception as e:
            logger.warning(e.message)
            logger.warning('can not load document {0} in fields {1}'.format(obj._id, fields))
            return None
    
    def create_one(self, obj):
        obj = base.monkFactory.decode(obj)
        self.__put_one(obj)
        obj.save()
        return obj
    
    def create_all(self, objs):
        decode = base.monkFactory.decode
        objs = map(decode, objs)
        self.__put_all(objs)
        [obj.save for obj in objs]
        return objs
        
    def load_one_by_id(self, objId):
        obj = self.__get_one(objId)
        if not obj:
            try:
                obj = self._coll.find_one({'_id': objId}, self._fields)
                self.__put_one(obj)
            except Exception as e:
                logger.warning(e.message)
                logger.warning('can not load document by id {0}'.format(objId))
                obj = None
        return obj

    def load_all_by_ids(self, objIds):
        objs, rems = self.__get_all(objIds)
        if rems:
            try:    
                remainObjs = self._coll.find(
                    {'_id': {'$in', rems}}, self._fields)
            except Exception as e:
                logger.warning(e.message)
                logger.warning('can not load remains {0} ...'.format(rems[0]))
                remainObjs = []
            objs.extend(remainObjs)
            self.__put_all(remainObjs)
        return objs

    def load_one_in_id(self, query):
        try:
            return self._coll.find_one(query, {'_id': 1})
        except Exception as e:
            logger.warning(e.message)
            logger.warning('can not load document by query'.format(query))
            return None

    def load_all_in_ids(self, query):
        try:
            return self._coll.find(query, {'_id': 1})
        except Exception as e:
            logger.warning(e.message)
            logger.warning('can not load documents by query'.format(query))
            return []

    def load_one(self, query, fields):
        try:
            return self._coll.find_one(query, fields)
        except Exception as e:
            logger.warning(e.message)
            logger.warning('query {0} can not be executed'.format(query))
            return None

    def load_all(self, query, fields):
        try:
            return self._coll.find(query, fields)
        except Exception as e:
            logger.warning(e.message)
            logger.warning('query {0} can not be executed'.format(query))
            return None

    def has_name(self, name):
        if self._coll.find_one({'name': name}):
            return True
        else:
            return False

dataDB       = None
modelDB      = None
uidDB        = None
uidStore     = None
entityStore  = Crane()
pandaStore   = Crane()
mantisStore  = Crane()
turtleStore  = Crane()
tigressStore = Crane()

def create_db(connectionString, databaseName):
    try:
        conn = pm.Connection(connectionString)
        database = conn[databaseName]
    except Exception as e:
        logger.warning(e.message)
        logger.warning('failed to connection to database {0}.{1}'.format(connectionString, databaseName))
        return None
    return database
    
def initialize_storage(config):
    global dataDB, modelDB, uidDB
    global uidStore, entityStore, pandaStore
    global mantisStore, turtleStore, tigressStore
    
    #initialize uid store
    uidDB = create_db(config.uidConnectionString,
                      config.uidDataBaseName)
    if uidDB is None:
        logger.error('can not access the database {0} at {1}'.format(
                     config.uidDataBaseName,
                     config.uidConnectionString))
        return False
    uidStore = UID(uidDB)

    #initialize data store
    dataDB = create_db(config.dataConnectionString,
                       config.dataDataBaseName)
    if dataDB is None:
        logger.error('can not access the database {0} at {1}'.format(
                     config.dataDataBaseName,
                     config.dataConnectionString))
        return False
    entityStore   = Crane(dataDB,
                          config.entityCollectionName,
                          config.entityFields)

    #initialize model store
    modelDB = create_db(config.modelConnectionString,
                        config.modelDataBaseName)
    if modelDB is None:
        logger.error('can not access the database {0} at {1}'.format(
                     config.modelDataBaseName,
                     config.modelConnectionString))
        return False
    pandaStore   = Crane(modelDB,
                         config.pandaCollectionName,
                         config.pandaFields)
    mantisStore  = Crane(modelDB,
                         config.mantisCollectionName,
                         config.mantisFields)
    turtleStore  = Crane(modelDB,
                         config.turtleCollectionName,
                         config.turtleFields)
    tigressStore = Crane(modelDB,
                         config.tigressCollectionName,
                         config.tigressFields)
    return True