#coding=utf8
import numpy
from IPython import get_ipython
import ipywidgets
from matplotlib import cm
from config import Config
from IPython.display import HTML
import Tkinter as tk
import math
from multiprocessing import Lock
from numpy import mean, linspace, float64
import random
import simpy
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

from idGenerator import IdGenerator

__author__ = 'root'

#Точка зарядки/обмена
class Point:
    def __init__(self, x, y, env=None, map=None, charge_speed=20):
        self.lock = Lock()
        self.x = x
        self.y = y
        #Количество коптеров на точке
        self.count = 0
        self.charge_speed = charge_speed
        self.env = env
        self.weight = None
        self.map = map
        self.history = []
        if env is not None and map is not None:
            self.copters = [Copter(env, map)]
        self.reserved = []

    #Получаем коптера по id задачи
    def get_copter_by_task(self, task):
        for r in self.reserved:
            if r[2] == task:
                return r[0]

    #Добавляем коптера на точку
    def put_copter(self, copter):
        self.copters.append(copter)


    def charge(self, time):
        self.lock.acquire()
        self.count += 1
        self.history.append((self.env.now, self.count))
        self.lock.release()
        yield self.env.timeout(time)
        self.lock.acquire()
        self.count -= 1
        self.history.append((self.env.now, self.count))
        self.lock.release()

    def call_copter(self, time, copter, task_id):
        if len(self.copters) > 0:
            self.lock.acquire()
            c = self.copters[0]
            self.copters.remove(c)
            self.reserved.append((c, time, task_id))
            self.lock.release()
            # print "Copter {0} is reserved to {1} by task {2} at {3}".format(c.id, time, task_id, (self.x, self.y))
            return
        if len(self.reserved) == 0:
            points = self.map.get_points_to_call(self)
            for p in points:
                c = p.rec_help(self)
                if ( c is not None):
                    if c.charge < 100:
                        yield self.env.timeout((100 - c.charge) / c.CHARGE_SPEED)
                    yield self.env.process(c.fly_from_point_to_point(p, self))
                    self.lock.acquire()
                    self.reserved.append((c, time, task_id))
                    self.lock.release()
            return

        else:
            self.lock.acquire()
            cc = None
            for c in self.reserved:
                if (time - c[1]) > (100 - copter.charge) / self.charge_speed:
                    cc = c
            self.lock.release()
            if cc is not None:
                self.lock.acquire()
                # print "Copter {0} rereserved to {1} by task {2} at {3}".format(cc[0].id, time, task_id,
                #                                                                (self.x, self.y))
                self.reserved.remove(cc)
                self.reserved.append((cc[0], time, task_id))
                self.reserved.append((copter, cc[1], cc[2]))
                self.lock.release()
                return
            else:

                points = self.map.get_points_to_call(self)
                for p in points:
                    c = p.rec_help(self)
                    if c is not None:
                        if c.charge < 100:
                            yield self.env.timeout((100 - c.charge) / c.CHARGE_SPEED)
                        yield self.env.process(c.fly_from_point_to_point(p, self))
                        self.lock.acquire()
                        self.reserved.append((c, time, task_id))
                        self.lock.release()
                return

    def rec_help(self, point):
        if len(self.copters) > 0:
            self.lock.acquire()
            c = self.copters[0]
            self.copters.remove(c)
            self.lock.release()
            # print "Copter {0} going help from {1} to {2}".format(c.id, (self.x, self.y), (point.x, point.y))
            return c
        return None

    def add_copter(self, copter):
        self.lock.acquire()
        self.copters.append(copter)
        self.lock.release()


class Map(object):
    def __init__(self, env, start_x, start_y, last_x, last_y, points=16, blocked_points=[]):
        if last_x < start_x or last_y < start_y:
            raise BaseException("Argument error")
        self.last_x = last_x
        self.last_y = last_y
        self.start_x = start_x
        self.start_y = start_y
        #Пункты зарядки
        self.points = []
        self.env = env
        self.copters = []
        self.blocked_points = blocked_points
        #Вычисление
        counter = int(math.sqrt(points))
        self.weight = counter
        self.points = self.__free_points()

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

    def get_points_to_call(self, point):
        x, y = 0, 0
        for i in range(0, len(self.points)):
            for j in range(0, len(self.points[i])):
                if self.points[i][j] == point:
                    x, y = i, j
        res = []
        for i in range(-2, 3):
            for j in range(-2, 3):
                if 0 <= x + i < self.weight and 0 <= y + j < self.weight and (i != 0 and j != 0):
                    res.append(self.points[x + i][y + j])
            # while self.weight > x >= 0:
        #     while 0 <= y < self.weight:
        #         if x != point.x and y != point.y:
        #             res.append(self.points[x][y])
        #         y -= 1
        #     x -= 1
        return res

    def __free_points(self):
        points = []
        x_range = (self.last_x - self.start_x) / (self.weight + 1)
        y_range = (self.last_y - self.start_y) / (self.weight + 1)
        for x in range(0, self.weight):
            points_x = []
            for y in range(0, self.weight):
                if (x, y) not in self.blocked_points:
                    points_x.append(Point(x_range + x_range * x, y_range + y_range * y, env=self.env, map=self))
                y += 1
            points.append(points_x)
            x += 1
        return points

    def calc(self, x1, x2, y1, y2):
        return math.sqrt(math.pow((x1 - x2), 2) + math.pow((y1 - y2), 2))
        self.x = x

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
                value = self.calc(point.x, x, point.y, y)
                if min is None or value < min[0]:
                    min = value, point, (i, j)
                j += 1
            i += 1
        return min

    def get_point(self, x, y):
        return self.points[x][y]

    def find_way(self, x1, x2, y1, y2):

        p1 = self.find_point(x1, y1)
        p2 = self.find_point(x2, y2)
        #print "Finding way from {0} to {1}".format(p1[2], p2[2])
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
            points = res
            #self.print_map()

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
            print "ERROR IN PATH"


    def set_point(self, x, y, points):
        ret_points = []
        for i in range(-1, 2):
            if 0 <= i + x < self.weight:
                for j in range(-1, 2):
                    if 0 <= j + y < self.weight and not (i == 0 and j == 0):
                        w = points[x][y].weight + self.calc(
                            points[x + i][y + j].x, points[x][y].x, points[x + i][y + j].y,
                            points[x][y].y)
                        if (w < points[x + i][y + j].weight or points[x + i][y + j].weight is None):
                            points[x + i][y + j].weight = w
                            ret_points.append((x + i, y + j))
        return ret_points


class Copter(object):
    #Скорость зарядки
    CHARGE_SPEED = Config.CHARGE_SPEED
    #Скорость замены груза
    EXCHANGE_TIME = Config.EXCHANGE_TIME
    #Скорость разрядки
    DISCHARGE_SPEED = Config.DISCHARGE_SPEED
    #Максимальная скоость
    MAX_SPEED = Config.MAX_SPEED
    #Максимальная масса
    MAX_MASS = Config.MAX_MASS

    def __init__(self, env, map, id=None):
        """
        @param env: environment
        @param map: map
        @param id:
        """
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
        self.max_speed = self.MAX_SPEED
        # print "MAX SPEED {0}".format(self.MAX_SPEED)
        if id is None:
            self.id = IdGenerator().getId()
        else:
            self.id = id
        self.map = map
        self.start_charge = 0
        self.charge = 100
        self.history = []
        self.map.copters.append(self)

    #ВОТ ЭТО не нужно в текущей версии
    def run(self, mass, star_location, end_location, task_id):
        if task_id == 0:
            yield self.env.timeout(0)
        start = self.env.now
        way = (
            self.map.find_way(star_location[0], end_location[0], star_location[1], end_location[1]))
        if way is None or len(way) <= 1:
            return

        flying_range = (self.DISCHARGE_SPEED / (self.max_speed / (1 - (mass / self.MAX_MASS)))) * (self.charge / 100)

        counter = 0
        c_time = 0
        while True:
            best_point = self.map.find_point_in_range(way[counter], [w for w in way[counter + 1:]], flying_range)
            b_point = self.map.get_point(best_point[0][0], best_point[0][1])
            distance = self.map.calc(best_point[0][0], way[counter][0], best_point[0][1], way[counter][1])

            c_time += distance / (self.max_speed / (1 - (mass / self.MAX_MASS)))

            yield self.env.process(b_point.call_copter(c_time, self, task_id))
            counter += 1
            if best_point[0] == way[len(way) - 1]:
                break

        counter = 0
        while True:
            best_point = self.map.find_point_in_range(way[counter], [w for w in way[counter + 1:]], flying_range)
            b_point = self.map.get_point(best_point[0][0], best_point[0][1])
            distance = self.map.calc(best_point[0][0], way[counter][0], best_point[0][1], way[counter][1])
            yield self.env.process(self.fly_from_point_to_point(self.map.get_point(way[counter][0], way[counter][1])),
                                   b_point)


    def fly_from_point_to_point(self, from_point, to_point, mass=0):

        if self.charge != 100 and ((100 - self.charge) / self.CHARGE_SPEED) > (self.env.now - self.start_charge):
            self.history.append(((from_point, self.env.now), (
                from_point, self.env.now + ((100 - self.charge) / self.CHARGE_SPEED) - (self.env.now - self.start_charge))))
            yield self.env.timeout(((100 - self.charge) / self.CHARGE_SPEED) - (self.env.now - self.start_charge))
        else:
            self.charge = 100
        path = math.sqrt(math.pow((from_point.x - to_point.x), 2) + math.pow((from_point.y - to_point.y), 2))
        # print "Start move {5} from {0}.{1} to {2}.{3} -- {4}|| Charge {6}".format(from_point.x, from_point.y,
        #                                                                           to_point.x, to_point.y,
        #                                                                           self.env.now, self.id, self.charge)
        self.charge -= (path / (self.max_speed / (1 - (mass / self.MAX_MASS)))) * self.DISCHARGE_SPEED * 100
        if (path / (self.max_speed / (1 - (mass / self.MAX_MASS)))) * self.DISCHARGE_SPEED * 100 == 0:
            print "qwe"
        self.history.append(((from_point, self.env.now), (
                to_point, self.env.now + path / (self.max_speed / (1 - (mass / self.MAX_MASS))))))
        yield self.env.timeout(path / (self.max_speed / (1 - (mass / self.MAX_MASS))))
        # print "End move {5} from {0}.{1} to {2}.{3} -- {4}|| Charge {6}".format(from_point.x, from_point.y, to_point.x,
        #                                                                         to_point.y,
                                                                                # self.env.now, self.id, self.charge)

    def charge_time(self):
        c = 100 - self.charge
        return c / self.CHARGE_SPEED


    def do_charge(self):
        #Уровень зарядки в процентах
        self.start_charge = self.env.now
        # print "Start charge {3} from {0}% to {1}% -- {2}".format(self.charge, 100, self.env.now, self.id)
        # yield self.env.timeout(c / self.CHARGE_SPEED)
        # self.charge = 100
        # print "End charge {1} -- {0}".format(self.env.now, self.id)


    def exchange(self):
        yield self.env.timeout(self.EXCHANGE_TIME)

    def calc_speed(self, mass):
        return self.max_speed / mass


class Processor(object):
    def __init__(self, map, env, copters_count):
        self.map = map
        self.env = env
        self.copters_count = copters_count
        self.res = []

    def process_ticket(self, star_location, end_location, mass, task_id):

        # print "#### strt task {0}".format(task_id)
        if task_id == 0:
            yield self.env.timeout(0)
        start = self.env.now
        way = (
            self.map.find_way(star_location[0], end_location[0], star_location[1], end_location[1]))
        if way is None or len(way) <= 1:
            return
        # print way
        copter = Copter(env=self.env, map=self.map)
        # flying_range = (Copter.DISCHARGE_SPEED / (copter.max_speed / (1 - (mass / copter.MAX_MASS)))) * (copter.charge / 100)
        flying_range = (copter.max_speed / (1 - (mass / copter.MAX_MASS))) * (
            copter.charge / 100) / Copter.DISCHARGE_SPEED
        # print way
        counter = 0
        c_time = 0
        while True:
            best_point = self.map.find_point_in_range(way[counter], [w for w in way[counter + 1:]], flying_range)
            # print best_point
            if best_point is None:
                # print "ERROR in way. Flying range too small"
                return
            b_point = self.map.get_point(best_point[0][0], best_point[0][1])
            distance = self.map.calc(best_point[0][0], way[counter][0], best_point[0][1], way[counter][1])

            c_time += distance / (copter.max_speed / (1 - (mass / copter.MAX_MASS)))

            yield self.env.process(b_point.call_copter(c_time, copter, task_id))
            counter += 1
            if best_point[0] == way[len(way) - 1]:
                break

        counter = 0
        start = self.env.now
        while True:
            best_point = self.map.find_point_in_range(way[counter], [w for w in way[counter + 1:]], flying_range)
            b_point = self.map.get_point(best_point[0][0], best_point[0][1])
            if (copter is None):
                print "qwe"

            for xx in copter.fly_from_point_to_point(self.map.get_point(way[counter][0], way[counter][1]), b_point):
                yield xx

            b_point.copters.append(copter)
            copter.start_charge = self.env.now
            # yield self.env.process(b_point.put_copter(copter))
            new_copter = b_point.get_copter_by_task(task_id)
            if new_copter is None:
                copter.start_charge = self.env.now

                # self.env.process(copter.do_charge())
            else:
                copter = new_copter
            counter += 1
            if best_point[0] == way[len(way) - 1]:
                end = self.env.now
                # print (end - start, task_id)
                self.res.append((end - start, task_id))
                break
        # print "#### end task {0}".format(task_id)


def timeout(env, time):
    yield env.timeout(time)


class Draw:
    def __init__(self, map):
        self.map = map
        self.root = tk.Tk()
        self.canvas = tk.Canvas(self.root, width=map.last_x / 10, height=map.last_y / 10, borderwidth=0,
                                highlightthickness=0, bg="green")
        self.canvas.grid()

        # self.canvas.create_oval(100, 200, 200, 300, fill="blue", outline="#DDD", width=4)
        self.canvas.pack(fill=None, expand=False)
        self.points = []
        for pp in map.points:
            for p in pp:
                self.points.append(
                    self.canvas.create_oval(p.x / 10 - 4, p.y / 10 - 4, p.x / 10 + 4, p.y / 10 + 4, fill="blue",
                                            outline="#DDD", width=4))
            # self.canvas.pack()
        objects = self.canvas.find_overlapping(map.points[0][0].x / 10 - 3, map.points[0][0].y / 10 - 3,
                                               map.points[0][0].x / 10 + 3, map.points[0][0].y / 10 + 3)
        self.canvas.bind("<Button-1>", self.callback)
        # self.copter = Gyro(520, 520, self.canvas, self.root)
        # for copter in map:
        #
        self.root.mainloop()
    #
    # def draw_copter(self, copter, x, y):
    #
    #     h = copter.history
    #     for p in h:
    #         if p[0][0] != p[1][0]:




    def callback(self, event):
        self.copter.move(self.copter.x - 10, self.copter.y - 10)


    def _create_circle(self, x, y, r, **kwargs):
        self.canvas.create_oval(x - r, y - r, x + r, y + r, **kwargs)


class Gyro:
    def __init__(self, x, y, canvas, root):
        self.x = x
        self.y = y
        self.canvas = canvas
        self.root = root
        self.id = self.canvas.create_oval(x / 10 - 5, y / 10 - 5, x / 10 + 5, y / 10 + 5, fill="black", outline="#DDD",
                                          width=4)

    def move(self, x, y):
        self.canvas.move(self.id, self.x - x, self.y - y)
        # print "move to {0}".format((x, y))
        self.x = x
        self.y = y


# map = Map(simpy.Environment(), 1, 1, 10240, 10240, points=12 * 12)
# Draw(map)

class TestModel:
    def __init__(self, tasks, map_h, map_w, map_points, speed_list, discharge_list, blocked_points=[]):
        self.res = []
        #максимальное
        self.rs_max = []
        #минимальное
        self.rs_min = []
        for t in discharge_list:
            res = []
            res_max = []
            res_min = []
            for j in speed_list:
                Config.MAX_SPEED = j
                Config.DISCHARGE_SPEED = t
                env = simpy.Environment()
                copters = []
                map = Map(env, 1, 1, map_w, map_h, points=map_points, blocked_points=blocked_points)
                p = Processor(map, env, 10000)
                c = 1
                for i in tasks:
                    env.process(p.process_ticket(i[0], i[1], i[2], i[3]))
                    if c % 100 == 0:
                        env.process(timeout(env, 30))
                    c += 1
                env.run()
                if len([x for (x, y) in p.res]) > 0:
                    res.append((j, mean([x for (x, y) in p.res])))
                    res_max.append((j, max([x for (x, y) in p.res])))
                    res_min.append((j, min([x for (x, y) in p.res])))
            self.res.append((t, res))
            self.rs_max.append((t, res_max))
            self.rs_min.append((t, res_min))

    def plot(self, discharge_time, color):
        fig, ax = plt.subplots(figsize=(3, 4), subplot_kw={'axisbg':'#EEEEEE', 'axisbelow': True})
        rs = [y for x, y in self.res if discharge_time - 0.001 <= x <= discharge_time + 0.001]
        rs_max = [y for x, y in self.rs_max if discharge_time - 0.001 <= x <= discharge_time + 0.001]
        rs_min = [y for x, y in self.rs_min if discharge_time - 0.001 <= x <= discharge_time + 0.001]

        if len(rs) == 0:
            print "ERROR"
            raise SystemExit
        res = rs[0]
        res_max = rs_max[0]
        res_min = rs_min[0]
        # ax.plot([x for (x, y) in res], [y for (x, y) in res], color=color)
        ax.plot([x for (x, y) in res], [y for (x, y) in res], color, [x for (x, y) in res_max],
                [y for (x, y) in res_max], "red",
                [x for (x, y) in res_min], [y for (x, y) in res_min], "yellow",
                lw=5, alpha=0.4)
        return fig

class TestModel3d:
    def __init__(self, tasks, map_h, map_w, map_points, speed_list, discharge_list, charge_list, blocked_points=[]):
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
                    map = Map(env, 1, 1, map_w, map_h, points=map_points, blocked_points=blocked_points)
                    p = Processor(map, env, 10000)
                    c = 1
                    for i in tasks:
                        env.process(p.process_ticket(i[0], i[1], i[2], i[3]))
                        if c % 100 == 0:
                            env.process(timeout(env, 30))
                        c += 1
                    env.run()
                    if len([x for (x, y) in p.res]) > 0:
                        res.append((j, mean([x for (x, y) in p.res])))
                        # res_max.append((j, max([x for (x, y) in p.res])))
                        # res_min.append((j, min([x for (x, y) in p.res])))
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
    tasks = []
    for i in range(0, 5):
            tasks.append((
                (10240 * random.random(), 10240 * random.random()), (100 * random.random(), 100 * random.random()),
                    random.random(), i))


    test = TestModel3d(tasks, 10240, 10240, 8 * 8, linspace(80, 150, num=5), linspace(0.01, 0.03, num=3), [20, 21])
    test.plot(0.03, "red")
    # widget = ipywidgets.StaticInteract(test.plot, amplitude=ipywidgets.RangeWidget(0.01, 0.1, 0.01), color=ipywidgets.RadioWidget(['blue', 'green']))

    # res = []po
    # tasks = []
    # for i in range(0, 100):
    #         tasks.append((
    #             (10240 * random.random(), 10240 * random.random()), (100 * random.random(), 100 * random.random()),
    #                 random.random(), i))
    # size = 8
    # for j in (80, 90, 110, 140):
    #     Config.MAX_SPEED = j
    #     env = simpy.Environment()
    #     copters = []
    #     map = Map(env, 1, 1, 10240, 10240, points=size * size)
    #     p = Processor(map, env, 10000)
    #     c = 1
    #     for i in tasks:
    #         env.process(p.process_ticket(i[0], i[1], i[2], i[3]))
    #         if c % 100 == 0:
    #             env.process(timeout(env, 30))
    #         c += 1
    #     env.run()
    #     res.append((j, mean([x for (x, y) in p.res])))
    #
    # plt.figure("Среднее время доставки 1")
    # plt.plot([x for (x, y) in res], [y for (x, y) in res])
    # plt.show()

    # Draw(map)
    # for i in range(0, 100):
    #     copter = Copter(env, map, 10, (1024 * random.random(), 1024 * random.random()),
    #                     (1024 * random.random(), 1024 * random.random()), (3 * random.random()), id=i)
    #     env.timeout(15)
    #     copters.append(copter)
    # env.run()
    # for copter in copters:
    #     print copter.time
    # data = [(copters[i].time) for i in range(0, len(copters))]
    # # plt.plot(data)
    # # d = mean(data)
    # # plt.plot([mean(data) for i in range(0, len(data))])
    #
    # #Загрузка станций
    # for points in (map.points):
    #     for point in points:
    #         plt.plot([x for (x, y) in point.history], [y for (x, y) in point.history])
    # plt.show()
    #
