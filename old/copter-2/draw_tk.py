__author__ = 'kirill'

import Tkinter as tk
#
# root = tk.Tk()
# canvas = tk.Canvas(root, width=1024, height=1024, borderwidth=0, highlightthickness=0, bg="black")
# canvas.grid()
#
# def _create_circle(self, x, y, r, **kwargs):
#     return self.create_oval(x-r, y-r, x+r, y+r, **kwargs)
# tk.Canvas.create_circle = _create_circle
#
# def _create_circle_arc(self, x, y, r, **kwargs):
#     if "start" in kwargs and "end" in kwargs:
#         kwargs["extent"] = kwargs["end"] - kwargs["start"]
#         del kwargs["end"]
#     return self.create_arc(x-r, y-r, x+r, y+r, **kwargs)
# tk.Canvas.create_circle_arc = _create_circle_arc
#
#
# for i in range(1, 9):
#     for j in range(1, 9):
#         canvas.create_circle(100, 120, 50, fill="blue", outline="#DDD", width=4)
# class Circle:
#     def __init__(self, canv, x, y, direc, color):
#         self.x, self.y = x, y
#         self.direction = direc
#
#         self._canvas = canv
#         coord = (self.x)-5, (self.y)-5, (self.x)+5, (self.y)+5
#         self._index = canv.create_oval(coord, fill=color)
#
#     def move(self):
#         y_sign = 1 if self.direction == DOWN else -1
#         x_sign = 1 if self.direction == RIGHT else -1
#         if self.direction in (UP, DOWN):
#             delta = (0, y_sign * 5)
#         else:
#             delta = (x_sign * 5, 0)
#         self._canvas.move(self._index, delta[0], delta[1])

class Draw:
    def __init__(self, map):
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
        self.copter = Gyro(520, 520, self.canvas, self.root)
        self.root.mainloop()


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
        print "move to {0}".format((x, y))
        self.x = x
        self.y = y


# map = Map(simpy.Environment(), 1, 1, 10240, 10240, points=12 * 12)
# Draw(map)