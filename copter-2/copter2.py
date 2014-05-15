#coding=utf8
import math
from multiprocessing import Lock
import random
import simpy

from idGenerator import IdGenerator

__author__ = 'root'


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

    def get_copter_by_task(self, task):
        for r in self.reserved:
            if r[2] == task:
                return r[0]

    def put_copter(self, copter):
        self.copters.append(copter)
        yield self.env.process(copter.do_charge())

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
            print "Copter {0} is reserved to {1} by task {2} at {3}".format(c.id, time, task_id, (self.x, self.y))
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
                print "Copter {0} rereserved to {1} by task {2} at {3}".format(cc[0].id, time, task_id,
                                                                               (self.x, self.y))
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
            print "Copter {0} going help from {1} to {2}".format(c.id, (self.x, self.y), (point.x, point.y))
            return c
        return None

    def add_copter(self, copter):
        self.lock.acquire()
        self.copters.append(copter)
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

    def find_point_in_range(self, point, points, range):
        start_p = self.find_point(point[0], point[1])[1]
        rs = [(p, self.calc(start_p.x, p[0], start_p.y, p[1])) for p in [pp for pp in points]]
        max = None
        for r in rs:
            if max is None or max[1] < rs[1] <= range:
                max = r
        return max

    def get_points_to_call(self, point):
        x, y = 0, 0
        for i in range(0, len(self.points)):
            for j in range(0, len(self.points[i])):
                if self.points[i][j] == point:
                    x, y = i, j
        res = []
        while self.weight > x >= 0:
            while 0 <= y < self.weight:
                if x != point.x and y != point.y:
                    res.append(self.points[x][y])
                y -= 1
            x -= 1
        return res

    def __free_points(self):
        points = []
        x_range = (self.last_x - self.start_x) / self.weight
        y_range = (self.last_y - self.start_y) / self.weight
        for x in range(0, self.weight):
            points_x = []
            for y in range(0, self.weight):
                points_x.append(Point(x_range + x_range * x, y_range + y_range * y, env=self.env, map=self))
                y += 1
            points.append(points_x)
            x += 1
        return points

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
    CHARGE_SPEED = 20
    #Скорость замены груза
    EXCHANGE_TIME = 2
    #Скорость разрядки
    DISCHARGE_SPEED = 0.05
    #Максимальная скоость
    MAX_SPEED = 10
    #Максимальная масса
    MAX_MASS = 15

    def __init__(self, env, map, id=None):
        """

        @param env: environment
        @param map: map
        @param id:
        """
        self.env = env
        self.max_speed = self.MAX_SPEED
        # self.mass = mass
        if id is None:
            self.id = IdGenerator().getId()
        else:
            self.id = id
            # self.star_location = start_location
        # self.end_location = end_location
        self.map = map
        #self.action = env.process(self.run(0, (0,0), (0,0), 0))

        self.charge = 100


        #self.action = env.process(self.run())

    def run(self, mass, star_location, end_location, task_id):
        if task_id == 0:
            yield self.env.timeout(0)
        self.speed = self.max_speed / mass
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
        path = math.sqrt(math.pow((from_point.x - to_point.x), 2) + math.pow((from_point.y - to_point.y), 2))
        print "Start move {5} from {0}.{1} to {2}.{3} -- {4}".format(from_point.x, from_point.y, to_point.x, to_point.y,
                                                                     self.env.now, self.id)
        self.charge -= (path / (self.max_speed / (1 - (mass / self.MAX_MASS)))) * self.DISCHARGE_SPEED * 100
        yield self.env.timeout(path / (self.max_speed / (1 - (mass / self.MAX_MASS))))
        print "End move {5} from {0}.{1} to {2}.{3} -- {4}".format(from_point.x, from_point.y, to_point.x, to_point.y,
                                                                   self.env.now, self.id)

    def charge_time(self):
        c = 100 - self.charge
        return c / self.CHARGE_SPEED


    def do_charge(self):
        #Уровень зарядки в процентах
        c = 100 - self.charge
        print "Start charge {3} from {0}% to {1}% -- {2}".format(self.charge, 100, self.env.now, self.id)
        yield self.env.timeout(c / self.CHARGE_SPEED)
        self.charge = 100
        print "End charge {1} -- {0}".format(self.env.now, self.id)

    def exchange(self):
        yield self.env.timeout(self.EXCHANGE_TIME)

    def calc_speed(self, mass):
        return self.max_speed / mass


class Processor(object):
    def __init__(self, map, env, copters_count):
        self.map = map
        self.env = env
        self.copters_count = copters_count

    def process_ticket(self, star_location, end_location, mass, task_id):
        if task_id == 0:
            yield self.env.timeout(0)
        start = self.env.now
        way = (
            self.map.find_way(star_location[0], end_location[0], star_location[1], end_location[1]))
        if way is None or len(way) <= 1:
            return

        copter = Copter(env=self.env, map=self.map)
        # flying_range = (Copter.DISCHARGE_SPEED / (copter.max_speed / (1 - (mass / copter.MAX_MASS)))) * (copter.charge / 100)
        flying_range = (copter.max_speed / (1 - (mass / copter.MAX_MASS))) * (
            copter.charge / 100) / Copter.DISCHARGE_SPEED

        counter = 0
        c_time = 0
        while True:
            best_point = self.map.find_point_in_range(way[counter], [w for w in way[counter + 1:]], flying_range)
            b_point = self.map.get_point(best_point[0][0], best_point[0][1])
            distance = self.map.calc(best_point[0][0], way[counter][0], best_point[0][1], way[counter][1])

            c_time += distance / (copter.max_speed / (1 - (mass / copter.MAX_MASS)))

            yield self.env.process(b_point.call_copter(c_time, copter, task_id))
            counter += 1
            if best_point[0] == way[len(way) - 1]:
                break

        counter = 0
        while True:
            best_point = self.map.find_point_in_range(way[counter], [w for w in way[counter + 1:]], flying_range)
            b_point = self.map.get_point(best_point[0][0], best_point[0][1])
            if (copter is None):
                print "qwe"
                # distance = self.map.calc(best_point[0][0], way[counter][0], best_point[0][1], way[counter][1])
            yield self.env.process(
                copter.fly_from_point_to_point(self.map.get_point(way[counter][0], way[counter][1]), b_point))
            self.env.process(b_point.put_copter(copter))
            new_copter = b_point.get_copter_by_task(task_id)
            if new_copter is None:
                self.env.process(copter.do_charge())
            else:
                copter = new_copter
            counter += 1
            if best_point[0] == way[len(way) - 1]:
                break


if __name__ == "__main__":
    env = simpy.Environment()

    # v = map.find_point(235, 642)
    # way = map.find_way(235, 854, 920, 150)
    copters = []
    map = Map(env, 1, 1, 1024, 1024, 64)
    p = Processor(map, env, 10000)
    for i in range(0, 30):
        # copter = Copter(env, map)
        # env.process(copter.run(1, (1024 * random.random(), 1024 * random.random()),
        #                        (1024 * random.random(), 1024 * random.random()), i))
        env.process(p.process_ticket((1024 * random.random(), 1024 * random.random()),
                                     (1024 * random.random(), 1024 * random.random()), random.random(), i))
    env.run()
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
