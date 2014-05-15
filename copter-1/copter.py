#coding=utf8
import math
from multiprocessing import Lock
import random
import matplotlib.pyplot as plt
import simpy

__author__ = 'root'


class Copter(object):
    #Скорость зарядки
    CHARGE_SPEED = 20
    #Скорость замены груза
    EXCHANGE_TIME = 2


    def __init__(self, env, map, max_speed, start_location, end_location, mass, id=1):
        self.env = env
        self.max_speed = max_speed
        self.mass = mass
        self.speed = self.__calc_speed()
        self.star_location = start_location
        self.end_location = end_location
        self.map = map
        self.action = env.process(self.run())
        self.id = id


        #self.action = env.process(self.run())

    def run(self):
        start = self.env.now
        way = (
            self.map.find_way(self.star_location[0], self.end_location[0], self.star_location[1], self.end_location[1]))
        if way is None:
            way = (self.star_location, self.end_location)
            yield self.env.process(self.__fly_from_point_to_point(Point(self.star_location[0], self.star_location[1]),
                                                                  Point(self.end_location[0], self.end_location[1])))
            yield self.env.process(self.charge())
        else:
            for i in range(1, len(way)):
                p1 = way[i - 1]
                p2 = way[i]
                point1 = self.map.points[p1[0]][p1[1]]
                point2 = self.map.points[p2[0]][p2[1]]
                yield self.env.process(self.__fly_from_point_to_point(point1, point2))
                yield self.env.process(self.map.points[p2[0]][p2[1]].charge(self.charge_time()))
        end = self.env.now

        self.time = end - start


    def __fly_from_point_to_point(self, from_point, to_point):
        path = math.sqrt(math.pow((from_point.x - to_point.x), 2) + math.pow((from_point.y - to_point.y), 2))
        print "Start move {5} from {0}.{1} to {2}.{3} -- {4}".format(from_point.x, from_point.y, to_point.x, to_point.y,
                                                                     self.env.now, self.id)
        yield self.env.timeout(path / self.speed)
        print "End move {5} from {0}.{1} to {2}.{3} -- {4}".format(from_point.x, from_point.y, to_point.x, to_point.y,
                                                                   self.env.now, self.id)

    def charge_time(self, current_lvl=0):
        c = 100 - current_lvl
        return (c / self.CHARGE_SPEED)


    def charge(self, current_lvl=0):
        #Уровень зарядки в процентах
        c = 100 - current_lvl
        print "Start charge {3} from {0}% to {1}% -- {2}".format(current_lvl, 100, self.env.now, self.id)
        yield self.env.timeout(c / self.CHARGE_SPEED)

    def exchange(self):
        yield self.env.timeout(self.EXCHANGE_TIME)

    def __calc_speed(self):
        return self.max_speed / self.mass


class Processor(object):
    def __init__(self, map, copters_count):
        self.map = map
        self.copters_count = copters_count

    def process(self, copter):
        1


class Point:
    def __init__(self,  x, y, env=None):
        self.lock = Lock()

        self.x = x
        self.y = y
        #Количество коптеров на точке
        self.count = 0
        self.env = env
        self.weight = None
        self.history = []

    def charge(self, time):
        self.lock.acquire()
        self.count+=1
        self.history.append((self.env.now, self.count))
        self.lock.release()
        yield self.env.timeout(time)
        self.lock.acquire()
        self.count-=1
        self.history.append((self.env.now, self.count))
        self.lock.release()



class Map(object):
    def __init__(self, env, start_x, start_y, last_x, last_y, points=16):
        if last_x < start_x or last_y < start_y:
            raise BaseException("Argument error")
        self.last_x = last_x
        self.last_y = last_y
        self.start_x = start_x
        self.start_y = start_y
        #Пункты зарядки
        self.points = []
        self.env = env

        #Вычисление
        counter = int(math.sqrt(points))
        self.weight = counter
        self.points = self.__free_points()

    def __free_points(self):
        points = []
        x_range = (self.last_x - self.start_x) / self.weight
        y_range = (self.last_y - self.start_y) / self.weight
        for x in range(0, self.weight):
            points_x = []
            for y in range(0, self.weight):
                points_x.append(Point(x_range + x_range * x, y_range + y_range * y, env=self.env))
                y += 1
            points.append(points_x)
            x += 1
        return points

    def __calc(self, x1, x2, y1, y2):
        return math.sqrt(math.pow((x1 - x2), 2) + math.pow((y1 - y2), 2))

    def print_map(self):
        print "#####################################################"
        for x in reversed(range(0, 8)):
            s = ""
            for y in (range(0, 8)):
                if self.points[y][x].weight is not None:
                    s += "{0}\t".format(int(self.points[y][x].weight))
                else:
                    s += "{0}\t".format(0)
            print "{0}".format(s)
        print "#####################################################"

    def find_point(self, x, y):
        min = None
        i = 0
        j = 0
        for points_x in self.points:
            j = 0
            for point in points_x:
                value = self.__calc(point.x, x, point.y, y)
                if min is None or value < min[0]:
                    min = value, point, (i, j)
                j += 1
            i += 1
        return min

    def find_way(self, x1, x2, y1, y2):

        p1 = self.find_point(x1, y1)
        p2 = self.find_point(x2, y2)
        print "Finding way from {0} to {1}".format(p1[2], p2[2])
        point1 = self.points[p1[2][0]][p1[2][1]], p1[2][0], p1[2][1]
        point2 = self.points[p2[2][0]][p2[2][1]], p2[2][0], p2[2][1]
        #self.points[p1[2][0]][p1[2][1]].weight = 0

        points_m = self.__free_points()
        points_m[p1[2][0]][p1[2][1]].weight = 0
        ##Заполняем точки
        points = [(p1[2][0], p1[2][1])]
        while True:
            if points_m[p2[2][0]][p2[2][1]].weight is not None:
                break
            pp = points
            res = []
            for p in pp:
                r_p = self.set_point(p[0], p[1], points_m)
                for r in r_p:
                    if r not in res:
                        res.append(r)

            # print pp
            # print res
            points = res
        self.print_map()
        ##Ищем путь
        e_p = points_m[p2[2][0]][p2[2][1]], p2[2][0], p2[2][1]

        path = [e_p]
        try:
            while True:
                min_l = None
                for i in range(-1, 2):
                    if 0 <= i + e_p[1] < self.weight:
                        for j in range(-1, 2):
                            if 0 <= j + e_p[2] < self.weight and not (i == 0 and j == 0):
                                if (min_l is None and points_m[e_p[1] + i][e_p[2] + j].weight is not None) or (
                                            points_m[e_p[1] + i][e_p[2] + j].weight is not None and min_l[0].weight >
                                        points_m[e_p[1] + i][e_p[2] + j].weight):
                                    min_l = points_m[e_p[1] + i][e_p[2] + j], e_p[1] + i, e_p[2] + j
                path.append(min_l)
                # print(min_l[1], min_l[2])
                e_p = min_l
                if min_l is not None and min_l[1] == p1[2][0] and min_l[2] == p1[2][1]:
                    break
            print [(x[1], x[2]) for x in path]
            return [(x[1], x[2]) for x in reversed(path)]
        except TypeError:
            print "wqe"


    def set_point(self, x, y, points):
        ret_points = []
        for i in range(-1, 2):
            if 0 <= i + x < self.weight:
                for j in range(-1, 2):
                    if 0 <= j + y < self.weight and not (i == 0 and j == 0):
                        w = points[x][y].weight + self.__calc(
                            points[x + i][y + j].x, points[x][y].x, points[x + i][y + j].y,
                            points[x][y].y)
                        if (w < points[x + i][y + j].weight or points[x + i][y + j].weight is None):
                            points[x + i][y + j].weight = w
                            ret_points.append((x + i, y + j))
        return ret_points


if __name__ == "__main__":
    env = simpy.Environment()

    # v = map.find_point(235, 642)
    # way = map.find_way(235, 854, 920, 150)
    copters = []
    map = Map(env, 1, 1, 1024, 1024, 64)
    for i in range(0, 100):
        copter = Copter(env, map, 50, (1024 * random.random(), 1024 * random.random()),
                        (1024 * random.random(), 1024 * random.random()), (3 * random.random()), id=i)
        env.timeout(15)
        copters.append(copter)
    env.run()
    for copter in copters:
        print copter.time
    data = [(copters[i].time) for i in range(0, len(copters))]
    # plt.plot(data)
    # d = mean(data)
    # plt.plot([mean(data) for i in range(0, len(data))])

    #Загрузка станций
    for points in (map.points):
        for point in points:
            plt.plot([x for (x, y) in point.history], [y for (x, y) in point.history])
    plt.show()

