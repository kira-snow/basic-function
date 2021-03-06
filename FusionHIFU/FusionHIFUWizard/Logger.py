#! /usr/bin/env python
# -*- coding:utf8 -*-

__author__ = 'HIFusion Team'

import logging
import os

class Logger(object):
    """the logger class to recording the process"""    
    def __new__(cls,*args,**kwds):
        """ A singleton pattern with python style."""
        if '_inst' not in vars(cls):
            cls._inst = super(Logger, cls).__new__(cls,*args, **kwds)
        return cls._inst

    def __init__(self, cwd = r'D:/FusionHIFU_log'):
        """constructor of class Logger. 
        # cwd:the current working directory contains the log info.
        """
        self.curr_dir = cwd      
        if not os.path.exists(self.curr_dir):
            os.mkdir(self.curr_dir)
        
        try:
            # set the test logger format
            log_format = '%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s'
            logging.basicConfig(level = logging.INFO,
                format = log_format,
                datefmt = '%Y-%m-%d %H:%M:%S %p',
                filename = self.curr_dir + os.sep+'convert.log',
                filemode = 'w')
            self.__logger = logging.getLogger('HIFusionLog')

            # define RotatingFileHandler to backup 5 logger files at most, size <= 10MB each
            from logging.handlers import RotatingFileHandler
            rtHandler = RotatingFileHandler(self.curr_dir+os.sep + 'fusion_history.log',
                maxBytes = 100*1024*1024,
                backupCount = 5)
            rtHandler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)-12s %(name)-12s:%(levelname)-8s %(message)s')
            rtHandler.setFormatter(formatter)
            self.__logger.addHandler(rtHandler) 
        except ValueError as e:
            self.__logger.error(e)
    
    def getInstance(self):
        return self.__logger