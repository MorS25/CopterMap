#coding=utf8
import math
from multiprocessing import Lock
from numpy import mean
import random
import matplotlib.pyplot as plt
import simpy

__author__ = 'root'


class Copter(object):
#Скорость зарядки
    CHARGE_SPEED = 0.6
    #Скорость замены груза
    EXCHANGE_TIME = 2
    #Скорость разрядки
    DISCHARGE_SPEED = 0.05
    #Максимальная скоость
    MAX_SPEED = 10
    #Максимальная масса
    MAX_MASS = 5

    def __init__(self, env, map, max_speed, start_location, end_location, mass, id=1):
        self.env = env
        self.max_speed = max_speed
        self.MAX_SPEED = max_speed
        self.mass = mass
        self.speed = self.__calc_speed()
        self.star_location = start_location
        self.end_location = end_location
        self.map = map
        self.action = env.process(self.run())
        self.id = id
        self.charge_lose = 0
        self.charge = 100
        #self.action = env.process(self.run())

    def run(self):
        start = self.env.now
        way = (
            self.map.find_way(self.star_location[0], self.end_location[0], self.star_location[1], self.end_location[1]))
        if way is None:
            way = (self.star_location, self.end_location)
            yield self.env.process(self.fly_from_point_to_point(Point(self.star_location[0], self.star_location[1]),
                                                                  Point(self.end_location[0], self.end_location[1])))
            yield self.env.process(self.do_charge())
        else:
            flying_range = (self.max_speed / (1 - (self.mass / self.MAX_MASS))) * (
                self.charge / 100) / self.DISCHARGE_SPEED
            counter = 0
            c_time = 0
            while True:
                best_point = self.map.find_point_in_range(way[counter], [w for w in way[counter + 1:]], flying_range)
                b_point = self.map.get_point(best_point[0][0], best_point[0][1])
                if best_point is None:
                    print "OPA"
                yield self.env.process(
                    copter.fly_from_point_to_point(self.map.get_point(way[counter][0], way[counter][1]), b_point))
                yield self.env.process(self.do_charge(b_point))
                if best_point[0] == way[len(way) - 1]:
                    break
                counter += 1

            # for i in range(1, len(way)):
            #     p1 = way[i - 1]
            #     p2 = way[i]
            #     point1 = self.map.points[p1[0]][p1[1]]
            #     point2 = self.map.points[p2[0]][p2[1]]
            #     yield self.env.process(self.__fly_from_point_to_point(point1, point2))
            #     # yield self.env.process(self.map.points[p2[0]][p2[1]].charge(self.charge_time()))
            #
            #     yield self.env.process(self.do_charge(point2))
        end = self.env.now

        self.time = end - start


    def fly_from_point_to_point(self, from_point, to_point):
        path = math.sqrt(math.pow((from_point.x - to_point.x), 2) + math.pow((from_point.y - to_point.y), 2))
        print "Start move {5} from {0}.{1} to {2}.{3} -- {4}".format(from_point.x, from_point.y, to_point.x, to_point.y,
                                                                     self.env.now, self.id)
        yield self.env.timeout(path / self.speed)
        self.charge -= (path / (self.max_speed / (1 - (self.mass / self.MAX_MASS)))) * self.DISCHARGE_SPEED * 100
        print "End move {5} from {0}.{1} to {2}.{3} -- {4}".format(from_point.x, from_point.y, to_point.x, to_point.y,
                                                                   self.env.now, self.id)

    def charge_time(self):
        c = 100 - self.charge
        return c / self.CHARGE_SPEED


    def do_charge(self, point=None):
        #Уровень зарядки в процентах
        c = 100 - self.charge
        self.charge_lose += c
        print "Start charge {3} from {0}% to {1}% -- {2}".format(self.charge, 100, self.env.now, self.id)
        if point is not None:
            point.lock.acquire()
            point.count += 1
            point.history.append((self.env.now, point.count))
            point.lock.release()

        yield self.env.timeout(c / self.CHARGE_SPEED)
        if point is not None:
            point.lock.acquire()
            point.count -= 1
            point.history.append((self.env.now, point.count))
            point.lock.release()

    def exchange(self):
        yield self.env.timeout(self.EXCHANGE_TIME)

    def __calc_speed(self):
        return self.max_speed / (1 - self.mass / self.MAX_MASS)


class Processor(object):
    def __init__(self, map, copters_count):
        self.map = map
        self.copters_count = copters_count

    def process(self, copter):
        1


class Point:
    def __init__(self, x, y, env=None):
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
        self.count += 1
        self.history.append((self.env.now, self.count))
        self.lock.release()
        self.env.timeout(time)
        self.lock.acquire()
        self.count -= 1
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

    def get_point(self, x, y):
        return self.points[x][y]

    def find_point_in_range(self, point, points, range):
        start_p = self.find_point(point[0], point[1])[1]
        rs = [(p, self.calc(start_p.x, p[0], start_p.y, p[1])) for p in [pp for pp in points]]
        max = None
        for r in rs:
            if max is None or max[1] < rs[1] <= range:
                max = r
        return max

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

    def calc(self, x1, x2, y1, y2):
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
            # self.print_map()
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
    info = []
    #генерация задач
    tasks = []
    for i in range(0, 20):
        tasks.append((
            (10240 * random.random(), 10240 * random.random()), (10240 * random.random(), 10240 * random.random()),
            (3 * random.random())))
    for j in range(50, 60):
        env = simpy.Environment()
        copters = []
        map = Map(env, 1, 1, 10240, 10240, 64)

        for i in tasks:
            copter = Copter(env, map, j, i[0], i[1], i[2], id=i)

            env.timeout(15)
            copters.append(copter)
        env.run()
        #Время полета коптеров
        for copter in copters:
            print copter.time

        lose_charge = sum([copter.charge_lose for copter in copters])

        #График времени полета коптеров
        data = [(copters[i].time) for i in range(0, len(copters))]
        # plt.plot(data)
        d = mean(data)
        # plt.plot([mean(data) for i in range(0, len(data))])
        # plt.figure()
        info.append((j, d, lose_charge))

        # #Загрузка станций
        # for points in (map.points):
        #     for point in points:
        #         plt.plot([x for (x, y) in point.history], [y for (x, y) in point.history])
        # plt.show()
    info2 = []
    for j in range(4, 8):
        env = simpy.Environment()
        copters = []
        map = Map(env, 1, 1, 10240, 10240, j * j)

        for i in tasks:
            copter = Copter(env, map, 50, i[0], i[1], i[2], id=i)

            env.timeout(15)
            copters.append(copter)
        env.run()
        #Время полета коптеров
        for copter in copters:
            print copter.time

        lose_charge = sum([copter.charge_lose for copter in copters])

        #График времени полета коптеров
        data = [(copters[i].time) for i in range(0, len(copters))]
        # plt.plot(data)
        d = mean(data)
        # plt.plot([mean(data) for i in range(0, len(data))])
        # plt.figure()
        info2.append((j, d, lose_charge))

        # #Загрузка станций
        # for points in (map.points):
        #     for point in points:
        #         plt.plot([x for (x, y) in point.history], [y for (x, y) in point.history])
        # plt.show()

    plt.plot([x for (x, y, z) in info], [y for (x, y, z) in info])
    plt.figure("Среднее время доставки 1")
    plt.plot([x for (x, y, z) in info], [z for (x, y, z) in info])
    plt.figure()

    plt.plot([x for (x, y, z) in info2], [y for (x, y, z) in info2])
    plt.figure("Среднее время доставки 2")
    plt.plot([x for (x, y, z) in info2], [z for (x, y, z) in info2])
    plt.show()
