#coding=utf8
from ConfigParser import SafeConfigParser

__author__ = 'kirill'

 # #Скорость зарядки
 #    CHARGE_SPEED = 20
 #    #Скорость замены груза
 #    EXCHANGE_TIME = 2
 #    #Скорость разрядки
 #    DISCHARGE_SPEED = 0.03
 #    #Максимальная скоость
 #    MAX_SPEED = 80
 #    #Максимальная масса
 #    MAX_MASS = 15

def getCfg():
    parser = SafeConfigParser()
    try:
        parser.read('cfg.ini')
        charge = parser.get('settings', 'CHARGE_SPEED')
        EXCHANGE_TIME = parser.get('settings', 'EXCHANGE_TIME')
        DISCHARGE_SPEED = parser.get('settings', 'DISCHARGE_SPEED')
        MAX_SPEED = parser.get('settings', 'MAX_SPEED')
        MAX_MASS = parser.get('settings', 'MAX_MASS')
        return charge, EXCHANGE_TIME, DISCHARGE_SPEED, MAX_SPEED, MAX_MASS
    except BaseException:
        raise SystemExit

class Config:
    __data = getCfg()
    CHARGE_SPEED = float(__data[0])
    EXCHANGE_TIME = float(__data[1])
    DISCHARGE_SPEED = float(__data[2])
    MAX_SPEED = float(__data[3])
    MAX_MASS = float(__data[4])