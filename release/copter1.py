#coding=utf8
import math
from multiprocessing import Lock
from numpy import mean, linspace
import numpy
import random
import ipywidgets
from matplotlib import cm
import matplotlib.pyplot as plt
import simpy
from config import Config
from mpl_toolkits.mplot3d import Axes3D
__author__ = 'root'

numpy.seterr(divide='ignore', invalid='ignore')


class Copter(object):
#Скорость зарядки
    CHARGE_SPEED = 0.6
    #Скорость замены груза
    EXCHANGE_TIME = 2
    #Скорость разрядки
    DISCHARGE_SPEED = 0.01
    #Максимальная скоость
    MAX_SPEED = 10
    #Максимальная масса
    MAX_MASS = 5

    def __init__(self, env, map, max_speed, start_location, end_location, mass, id=1):
        Copter.CHARGE_SPEED = Config.CHARGE_SPEED
        #Скорость замены груза
        Copter.EXCHANGE_TIME = Config.EXCHANGE_TIME
        #Скорость разрядки
        Copter.DISCHARGE_SPEED = Config.DISCHARGE_SPEED
        #Максимальная скоость
        Copter.MAX_SPEED = Config.MAX_SPEED
        #Максимальная масса
        Copter.MAX_MASS = Config.MAX_MASS
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
            #print "Wrong way"
        else:
            flying_range = (self.max_speed / (1 - (self.mass / self.MAX_MASS))) * (
                self.charge / 100) / self.DISCHARGE_SPEED
            counter = 0
            c_time = 0
            while True:
                best_point = self.map.find_point_in_range(way[counter], [w for w in way[counter + 1:]], flying_range)
                if best_point is None:
                    #print "\n########################################\nCANT FIND WAY\n##############################\n"
                    break
                b_point = self.map.get_point(best_point[0][0], best_point[0][1])


                from_point, to_point = self.map.get_point(way[counter][0], way[counter][1]), b_point

                #Полет от точки до точки
                path = math.sqrt(math.pow((from_point.x - to_point.x), 2) + math.pow((from_point.y - to_point.y), 2))
                if path > flying_range:
                    print "qwe"
                #print "Start move {5} from {0}.{1} to {2}.{3} -- {4}, {5}".format(from_point.x, from_point.y, to_point.x, to_point.y,
                  #                                                           self.env.now, self.id)


                self.charge_lose += (path / (self.max_speed / (1 - (self.mass / self.MAX_MASS)))) * self.DISCHARGE_SPEED * 100
                self.charge -= (path / (self.max_speed / (1 - (self.mass / self.MAX_MASS)))) * self.DISCHARGE_SPEED * 100



                yield self.env.timeout(path / self.speed)

                #print "End move {5} from {0}.{1} to {2}.{3} -- {4}".format(from_point.x, from_point.y, to_point.x, to_point.y,
                      #                                                     self.env.now, self.id)
                ########################
                #Charge
                ########################
                #Уровень зарядки в процентах
                c = 100 - self.charge
                # if self.charge < 0:
                #     print "wqe"
                #print "Start charge {3} from {0}% to {1}% -- {2}".format(self.charge, 100, self.env.now, self.id)
                if b_point is not None:
                    b_point.lock.acquire()
                    b_point.count += 1
                    b_point.history.append((self.env.now, b_point.count))
                    b_point.lock.release()

                yield self.env.timeout(c / self.CHARGE_SPEED)
                self.charge = 100
                if b_point is not None:
                    b_point.lock.acquire()
                    b_point.count -= 1
                    b_point.history.append((self.env.now, b_point.count))
                    b_point.lock.release()


                if best_point[0] == way[len(way) - 1]:
                    break
                counter += 1
        end = self.env.now
        self.time = end - start


    # def fly_from_point_to_point(self, from_point, to_point):
    #     path = math.sqrt(math.pow((from_point.x - to_point.x), 2) + math.pow((from_point.y - to_point.y), 2))
    #     if path == 0:
    #         #print "qe"
    #     #print "Start move {5} from {0}.{1} to {2}.{3} -- {4}, {5}".format(from_point.x, from_point.y, to_point.x, to_point.y,
    #                                                                  self.env.now, self.id)
    #     if (path / (self.max_speed / (1 - (self.mass / self.MAX_MASS)))) * self.DISCHARGE_SPEED * 100 == 0 :
    #         #print "wqe"
    #
    #     self.charge_lose += (path / (self.max_speed / (1 - (self.mass / self.MAX_MASS)))) * self.DISCHARGE_SPEED * 100
    #     self.charge -= (path / (self.max_speed / (1 - (self.mass / self.MAX_MASS)))) * self.DISCHARGE_SPEED * 100
    #     #print self.charge
    #     yield self.env.timeout(path / self.speed)
    #
    #     #print "End move {5} from {0}.{1} to {2}.{3} -- {4}".format(from_point.x, from_point.y, to_point.x, to_point.y,
    #                                                                self.env.now, self.id)

    def charge_time(self):
        c = 100 - self.charge
        return c / self.CHARGE_SPEED


    # def do_charge(self, point=None):
    #     #Уровень зарядки в процентах
    #     c = 100 - self.charge
    #     if self.charge == 100:
    #         #print "wqe"
    #
    #     #print "Start charge {3} from {0}% to {1}% -- {2}".format(self.charge, 100, self.env.now, self.id)
    #     if point is not None:
    #         point.lock.acquire()
    #         point.count += 1
    #         point.history.append((self.env.now, point.count))
    #         point.lock.release()
    #
    #     yield self.env.timeout(c / self.CHARGE_SPEED)
    #     self.charge = 100
    #     if point is not None:
    #         point.lock.acquire()
    #         point.count -= 1
    #         point.history.append((self.env.now, point.count))
    #         point.lock.release()

    def exchange(self):
        yield self.env.timeout(self.EXCHANGE_TIME)

    def __calc_speed(self):
        return self.max_speed / (1 - self.mass / self.MAX_MASS)



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
        start_p = self.get_point(point[0], point[1])
        rs = []
        for p in points:
            point_1 = self.get_point(p[0], p[1])
            rs.append((p, self.calc(start_p.x, point_1.x, start_p.y, point_1.y)))
       # rs = [(p, self.calc(start_p.x, self.find_point(p[0], p[1])[1].x, start_p.y, self.find_point(p[0], p[1])[1].y)) for p in points]
        max_e = None
        for r in rs:
            if (max_e is None or max_e[1] < r[1] ) and r[1] <= range:
                max_e = r
        return max_e

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
        #print "#####################################################"
        for x in reversed(range(0, 8)):
            s = ""
            for y in (range(0, 8)):
                if self.points[y][x].weight is not None:
                    s += "{0}\t".format(int(self.points[y][x].weight))
                else:
                    s += "{0}\t".format(0)
            #print "{0}".format(s)
        #print "#####################################################"

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
        #print "Finding way from {0} to {1}".format(p1[2], p2[2])
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

            # #print pp
            # #print res
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
            #print [(x[1], x[2]) for x in path]
            return [(x[1], x[2]) for x in reversed(path)]
        except TypeError:
            return


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

class TestModel:
    def __init__(self, tasks, map_h, map_w, map_points, speed_list, discharge_list):
        #среднее время доставки
        self.res = []
        #максимальное
        self.rs_max = []
        #минимальное
        self.rs_min = []
        self.speed_list = speed_list
        for t in discharge_list:
            res = []
            res_max = []
            res_min = []
            for j in speed_list:
                Config.MAX_SPEED = j
                Config.DISCHARGE_SPEED = t
                env = simpy.Environment()
                copters = []
                map = Map(env, 1, 1, map_w, map_h, points=map_points)
                jo = 1
                for i in tasks:
                    copter = Copter(env, map, j, i[0], i[1], i[2], id=jo)
                    jo += 1
                    env.timeout(15)
                    copters.append(copter)
                env.run()
                data = [(copters[i].time ) for i in range(0, len(copters)) if copters[i].time > 0]
                if len(data) > 0:
                    res.append((j, mean(data)))
                    res_max.append((j, max(data)))
                    res_min.append((j, min(data)))
            self.res.append((t, res))
            self.rs_max.append((t, res_max))
            self.rs_min.append((t, res_min))

    def plot(self, discharge_time, color):
        fig, ax = plt.subplots(figsize=(4, 3),
                           subplot_kw={'axisbg':'#EEEEEE',
                                       'axisbelow':True})
        ax.grid(color='w', linewidth=2, linestyle='solid')
        rs = [y for x, y in self.res if discharge_time - 0.001 <= x <= discharge_time + 0.001]
        rs_max = [y for x, y in self.rs_max if discharge_time - 0.001 <= x <= discharge_time + 0.001]
        rs_min = [y for x, y in self.rs_min if discharge_time - 0.001 <= x <= discharge_time + 0.001]

        if len(rs) == 0:
            print "ERROR"
            raise SystemExit
        res = rs[0]
        res_max = rs_max[0]
        res_min = rs_min[0]
        # print rs[0], amplitude
        ax.plot([x for (x, y) in res], [y for (x, y) in res], color, [x for (x, y) in res_max],
                [y for (x, y) in res_max], "red",
                [x for (x, y) in res_min], [y for (x, y) in res_min], "yellow",
                lw=5, alpha=0.4)
        # ax.plot([x for (x, y) in res_max], [y for (x, y) in res_max], color="red",
        #         lw=5, alpha=0.4)
        # ax.plot([x for (x, y) in res_min], [y for (x, y) in res_min], color="green",
        #         lw=5, alpha=0.4)
        ax.set_xlim(min(self.speed_list), max(self.speed_list))
        # print max(max(y) for x, y in [y for x, y in self.res])
        ax.set_ylim(0, 200)
        # ax.set_xlim(0, 10)
        # ax.set_ylim(-1.1, 1.1)
        return fig
        # fig, ax = plt.subplots(figsize=(4, 3),
        #                    subplot_kw={'axisbg':'#EEEEEE',
        #                                'axisbelow':True})
        # ax.grid(color='w', linewidth=2, linestyle='solid')
        # rs = [y for x, y in self.res if amplitude - 0.001 <= x <= amplitude + 0.001]
        # if len(rs) == 0:
        #     print "ERROR"
        #     raise SystemExit
        # res = rs[0]
        # # print  [y for (x, y) in res]
        # ax.plot([x for (x, y) in res], [y for (x, y) in res], lw=5, alpha=0.4, color=color)
        # ax.set_xlim(0, 10)
        # ax.set_ylim(-1.1, 1.1)
        # return fig

        def __analyze_data(self, d_t):
            res = []
            rs = [y for x, y in self.res if d_t - 0.001 <= x <= d_t + 0.001]


class TestModel3d:
    def __init__(self, tasks, map_h, map_w, map_points, speed_list, discharge_list, charge_list):
        self.res = []
        #максимальное
        self.rs_max = []
        #минимальное
        self.rs_min = []
        for v in discharge_list:
            res_v = []

            for t in charge_list:
                res = []
                # res_max = []
                # res_min = []
                for j in speed_list:
                    Config.MAX_SPEED = j
                    Config.DISCHARGE_SPEED = v
                    Config.CHARGE_SPEED = t
                    env = simpy.Environment()
                    copters = []
                    map = Map(env, 1, 1, map_w, map_h, points=map_points)
                    jo = 0
                    for i in tasks:
                        copter = Copter(env, map, j, i[0], i[1], i[2], id=jo)
                        jo += 1
                        env.timeout(15)
                        copters.append(copter)
                    env.run()
                    data = [(copters[i].time ) for i in range(0, len(copters)) if copters[i].time > 0]
                        # res_max.append((j, max([x for (x, y) in p.res])))
                        # res_min.append((j, min([x for (x, y) in p.res])))
                    if len(data) > 0:
                        res.append((j, mean(data)))

                res_v.append((t, res))
                # self.rs_max.append((t, res_max))
                # self.rs_min.append((t, res_min))
            self.res.append((v, res_v))

    def plot(self, discharge_time, color):
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')

        # fig, ax = plt.subplots(figsize=(3, 4), subplot_kw={'axisbg':'#EEEEEE', 'axisbelow': True})
        rs = [y for x, y in self.res if discharge_time - 0.001 <= x <= discharge_time + 0.001]


        if len(rs) == 0:
            print "ERROR"
            raise SystemExit
        res = rs[0]
        # res_max = rs_max[0]
        # res_min = rs_min[0]
        rx = []
        ry = []
        for x, vx in res:
            rx.append(x)
            for y, vy in vx:
                if y not in ry:
                    ry.append(y)

        rz = numpy.zeros((len(rx)+1, len(ry)+1), 'Float32')
        i = 0
        j = 0
        d = {}
        for x, vx in res:
            for y, z in vx:
                rz[i, j] = z
                d[(x,y)] = z
                j+=1
            j=0
            i+=1

        X, Y = numpy.meshgrid(rx,ry)
        zs = numpy.array([self.__fun(x,y,d) for x,y in zip(numpy.ravel(X), numpy.ravel(Y))])
        Z = zs.reshape(X.shape)
        # ax.plot([x for (x, y) in res], [y for (x, y) in res], color=color)
        ax.plot_surface(X, Y, Z, rstride=1, cstride=1, cmap=cm.RdBu)
        # Xs = numpy.arange(min(rx), max(rx), 0.005)
        # Ys = numpy.arange(min(ry), max(ry), 0.005)
        # Xs, Ys = numpy.meshgrid(Xs, Ys)
        # Zs = 41.0909875400163+15.3581432751401*numpy.log(Xs)+-90.9714747515509*Ys+64.9652271333282*Ys**2
        # ax.plot_surface(Xs, Ys, Zs, rstride=4, cstride=4, alpha=0.4,cmap=cm.jet)
        # plt.show()
        return fig

    def __fun(self, x, y, r):
        return r[(x,y)]


if __name__ == "__main__":
    info = []
    #генерация задач
    tasks = []
    jo = 0
    for i in range(0, 1):
        tasks.append((
            (10240 * random.random(), 10240 * random.random()), (10240 * random.random(), 10240 * random.random()),
            (3 * random.random())))
    test = TestModel3d(tasks, 10240, 10240, 8 * 8, linspace(80, 150, num=5), linspace(0.01, 0.1, num=10), [20, 21])
    test.plot(0.03, "red")
    widget = ipywidgets.StaticInteract(test.plot, amplitude=ipywidgets.RangeWidget(0.01, 0.1, 0.01), color=ipywidgets.RadioWidget(['blue', 'green']))