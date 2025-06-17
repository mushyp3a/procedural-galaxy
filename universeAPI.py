import sqlite3
import os
import random as r
import configparser
import math
import matplotlib.pyplot as plt

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
    return f

def generate_graph():
    min = 50
    mtd = 60
    numSystems = 50
    mergeDist = 5
    
    output = [(0,0)]

    currentNode = (0,0)
    for i in range(numSystems):
        x = r.randint(min, mtd-1) * r.choice([1, -1])
        yMax = math.floor((mtd**2 - x**2)**0.5)
        y = r.randint(5, yMax) * r.choice([1,-1])

        output.append((currentNode[0]+x, currentNode[1]+y))
        currentNode = output[i+1]
    print(output)
    
    count = 0
    toRemove = []
    lenOutput = len(output)
    for i in range(lenOutput):
        for j in range(lenOutput):
            if i != j:
                p1 = output[i]
                p2 = output[j]
                distance = math.sqrt(abs(p1[0]-p2[0])**2 + abs(p1[1]-p2[1])**2)
                mid_x = (p1[0] + p2[0]) / 2
                mid_y = (p1[1] + p2[1]) / 2

                if distance <= mtd and distance > mergeDist:
                    plt.text(mid_x, mid_y, f'{distance:.1f}', color='red', ha='center', va='bottom')
                    count += 1

    if count < numSystems / 2:
        generate_graph()
            
    xPoints = list(map(lambda x : x[0], output))
    yPoints = list(map(lambda x : x[1], output))
    
    plt.scatter(xPoints, yPoints, color = 'black', s = 10)
    #plt.plot(xPoints, yPoints)
    for coord in output:
        for coord2 in output:
            distance = math.sqrt(abs(coord[0] - coord2[0])**2 + abs(coord[1] - coord2[1])**2)
            if distance <= mtd:
                plt.plot([coord[0], coord2[0]], [coord[1], coord2[1]], color='black')
    plt.show()

generate_graph()

