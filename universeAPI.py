import sqlite3
import os
import random as r
import configparser

def create_config():
    config = configparser.ConfigParser()

    config["Files"] = {"source":"text.txt"}

    with open('config.ini', 'w') as configfile:
        config.write(configfile)

def get_config(variable, section='General'):
    config = configparser.ConfigParser()

    config.read('config.ini')

    val = config.get(section, variable)

    if val in ["True", "False"]:
        val = config.getboolean(section, variable)
    elif '.txt' in val:
        return list(map(lambda x : x.strip(), open(val,"r").readlines()))
    elif '.csv' in val:
        return process_csv(val)
    return val

def process_csv(file):
    f = list(map(lambda x : x.strip().split(','), open(file)))
    columns = len(f[0])
    processed_data = {}
    for i in range(columns):
        values = []
        for j in range(1,len(f)):
            values.append(f[j][i])
        processed_data[f[0][i]] = values
    return processed_data

a = get_config('Source')
print(a)

b = get_config('Randomised')
print(b)
